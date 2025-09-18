import concurrent
import json
import traceback
import warnings
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime
from typing import Any, List, Optional, Union, Dict

import numpy as np
import orjson
import pandas as pd
import requests
import sqlparse
from langchain.chat_models.base import BaseChatModel
from langchain_community.utilities import SQLDatabase
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, BaseMessageChunk
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from sqlmodel import create_engine, Session

from apps.ai_model.model_factory import LLMConfig, LLMFactory, get_default_config
from apps.chat.curd.chat import save_question, save_sql_answer, save_sql, \
    save_error_message, save_sql_exec_data, save_chart_answer, save_chart, \
    finish_record, save_analysis_answer, save_predict_answer, save_predict_data, \
    save_select_datasource_answer, save_recommend_question_answer, \
    get_old_questions, save_analysis_predict_record, rename_chat, get_chart_config, \
    get_chat_chart_data, list_generate_sql_logs, list_generate_chart_logs, start_log, end_log, \
    get_last_execute_sql_error
from apps.chat.models.chat_model import ChatQuestion, ChatRecord, Chat, RenameChat, ChatLog, OperationEnum
from apps.datasource.crud.datasource import get_table_schema
from apps.datasource.crud.permission import get_row_permission_filters, is_normal_user
from apps.datasource.models.datasource import CoreDatasource
from apps.db.db import exec_sql, get_version, check_connection
from apps.system.crud.assistant import AssistantOutDs, AssistantOutDsFactory, get_assistant_ds
from apps.system.schemas.system_schema import AssistantOutDsSchema
from apps.terminology.curd.terminology import get_terminology_template
from common.core.config import settings
from common.core.deps import CurrentAssistant, CurrentUser
from common.error import SingleMessageError, SQLBotDBError, ParseSQLResultError, SQLBotDBConnectionError
from common.utils.utils import SQLBotLogUtil, extract_nested_json, prepare_for_orjson

warnings.filterwarnings("ignore")

base_message_count_limit = 6

executor = ThreadPoolExecutor(max_workers=200)

dynamic_ds_types = [1, 3]


class LLMService:
    ds: CoreDatasource
    chat_question: ChatQuestion
    record: ChatRecord
    config: LLMConfig
    llm: BaseChatModel
    sql_message: List[Union[BaseMessage, dict[str, Any]]] = []
    chart_message: List[Union[BaseMessage, dict[str, Any]]] = []

    session: Session
    current_user: CurrentUser
    current_assistant: Optional[CurrentAssistant] = None
    out_ds_instance: Optional[AssistantOutDs] = None
    change_title: bool = False

    generate_sql_logs: List[ChatLog] = []
    generate_chart_logs: List[ChatLog] = []

    current_logs: dict[OperationEnum, ChatLog] = {}

    chunk_list: List[str] = []
    future: Future

    last_execute_sql_error: str = None

    def __init__(self, current_user: CurrentUser, chat_question: ChatQuestion,
                 current_assistant: Optional[CurrentAssistant] = None, no_reasoning: bool = False,
                 config: LLMConfig = None):
        self.chunk_list = []
        self._retry_thinking_updates = []  # 存储重试时的thinking更新
        engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
        session_maker = sessionmaker(bind=engine)
        self.session = session_maker()
        self.session.exec = self.session.exec if hasattr(self.session, "exec") else self.session.execute
        self.current_user = current_user
        self.current_assistant = current_assistant
        # chat = self.session.query(Chat).filter(Chat.id == chat_question.chat_id).first()
        chat_id = chat_question.chat_id
        chat: Chat | None = self.session.get(Chat, chat_id)
        if not chat:
            raise SingleMessageError(f"Chat with id {chat_id} not found")
        ds: CoreDatasource | AssistantOutDsSchema | None = None
        if chat.datasource:
            # Get available datasource
            # ds = self.session.query(CoreDatasource).filter(CoreDatasource.id == chat.datasource).first()
            if current_assistant and current_assistant.type in dynamic_ds_types:
                self.out_ds_instance = AssistantOutDsFactory.get_instance(current_assistant)
                ds = self.out_ds_instance.get_ds(chat.datasource)
                if not ds:
                    raise SingleMessageError("No available datasource configuration found")
                chat_question.engine = ds.type + get_version(ds)
                chat_question.db_schema = self.out_ds_instance.get_db_schema(ds.id)
            else:
                ds = self.session.get(CoreDatasource, chat.datasource)
                if not ds:
                    raise SingleMessageError("No available datasource configuration found")
                chat_question.engine = (ds.type_name if ds.type != 'excel' else 'PostgreSQL') + get_version(ds)
                chat_question.db_schema = get_table_schema(session=self.session, current_user=current_user, ds=ds)

        self.generate_sql_logs = list_generate_sql_logs(session=self.session, chart_id=chat_id)
        self.generate_chart_logs = list_generate_chart_logs(session=self.session, chart_id=chat_id)

        self.change_title = len(self.generate_sql_logs) == 0

        chat_question.lang = get_lang_name(current_user.language)

        self.ds = (ds if isinstance(ds, AssistantOutDsSchema) else CoreDatasource(**ds.model_dump())) if ds else None
        self.chat_question = chat_question
        self.config = config
        if no_reasoning:
            # only work while using qwen
            if self.config.additional_params:
                if self.config.additional_params.get('extra_body'):
                    if self.config.additional_params.get('extra_body').get('enable_thinking'):
                        del self.config.additional_params['extra_body']['enable_thinking']

        self.chat_question.ai_modal_id = self.config.model_id
        self.chat_question.ai_modal_name = self.config.model_name

        # Create LLM instance through factory
        llm_instance = LLMFactory.create_llm(self.config)
        self.llm = llm_instance.llm

        # get last_execute_sql_error
        last_execute_sql_error = get_last_execute_sql_error(self.session, self.chat_question.chat_id)
        if last_execute_sql_error:
            self.chat_question.error_msg = f'''<error-msg>
{last_execute_sql_error}
</error-msg>'''
        else:
            self.chat_question.error_msg = ''

        self.init_messages()

    @classmethod
    async def create(cls, *args, **kwargs):
        config: LLMConfig = await get_default_config()
        instance = cls(*args, **kwargs, config=config)
        return instance

    def is_running(self, timeout=0.5):
        try:
            r = concurrent.futures.wait([self.future], timeout)
            if len(r.not_done) > 0:
                return True
            else:
                return False
        except Exception as e:
            return True

    def init_messages(self):
        last_sql_messages: List[dict[str, Any]] = self.generate_sql_logs[-1].messages if len(
            self.generate_sql_logs) > 0 else []

        # todo maybe can configure
        count_limit = 0 - base_message_count_limit

        self.sql_message = []
        # add sys prompt
        self.sql_message.append(SystemMessage(content=self.chat_question.sql_sys_question()))
        if last_sql_messages is not None and len(last_sql_messages) > 0:
            # limit count
            for last_sql_message in last_sql_messages[count_limit:]:
                _msg: BaseMessage
                if last_sql_message['type'] == 'human':
                    _msg = HumanMessage(content=last_sql_message['content'])
                    self.sql_message.append(_msg)
                elif last_sql_message['type'] == 'ai':
                    _msg = AIMessage(content=last_sql_message['content'])
                    self.sql_message.append(_msg)

        last_chart_messages: List[dict[str, Any]] = self.generate_chart_logs[-1].messages if len(
            self.generate_chart_logs) > 0 else []

        self.chart_message = []
        # add sys prompt
        self.chart_message.append(SystemMessage(content=self.chat_question.chart_sys_question()))

        if last_chart_messages is not None and len(last_chart_messages) > 0:
            # limit count
            for last_chart_message in last_chart_messages:
                _msg: BaseMessage
                if last_chart_message.get('type') == 'human':
                    _msg = HumanMessage(content=last_chart_message.get('content'))
                    self.chart_message.append(_msg)
                elif last_chart_message.get('type') == 'ai':
                    _msg = AIMessage(content=last_chart_message.get('content'))
                    self.chart_message.append(_msg)

    def init_record(self) -> ChatRecord:
        self.record = save_question(session=self.session, current_user=self.current_user, question=self.chat_question)
        return self.record

    def get_record(self):
        return self.record

    def set_record(self, record: ChatRecord):
        self.record = record

    def get_fields_from_chart(self):
        chart_info = get_chart_config(self.session, self.record.id)
        fields = []
        if chart_info.get('columns') and len(chart_info.get('columns')) > 0:
            for column in chart_info.get('columns'):
                column_str = column.get('value')
                if column.get('value') != column.get('name'):
                    column_str = column_str + '(' + column.get('name') + ')'
                fields.append(column_str)
        if chart_info.get('axis'):
            for _type in ['x', 'y', 'series']:
                if chart_info.get('axis').get(_type):
                    column = chart_info.get('axis').get(_type)
                    column_str = column.get('value')
                    if column.get('value') != column.get('name'):
                        column_str = column_str + '(' + column.get('name') + ')'
                    fields.append(column_str)
        return fields

    def generate_analysis(self):
        fields = self.get_fields_from_chart()
        self.chat_question.fields = orjson.dumps(fields).decode()
        data = get_chat_chart_data(self.session, self.record.id)
        self.chat_question.data = orjson.dumps(data.get('data')).decode()
        analysis_msg: List[Union[BaseMessage, dict[str, Any]]] = []

        self.chat_question.terminologies = get_terminology_template(self.session, self.chat_question.question,
                                                                    self.current_user.oid)

        analysis_msg.append(SystemMessage(content=self.chat_question.analysis_sys_question()))
        analysis_msg.append(HumanMessage(content=self.chat_question.analysis_user_question()))

        self.current_logs[OperationEnum.ANALYSIS] = start_log(session=self.session,
                                                              ai_modal_id=self.chat_question.ai_modal_id,
                                                              ai_modal_name=self.chat_question.ai_modal_name,
                                                              operate=OperationEnum.ANALYSIS,
                                                              record_id=self.record.id,
                                                              full_message=[
                                                                  {'type': msg.type,
                                                                   'content': msg.content} for
                                                                  msg
                                                                  in analysis_msg])
        full_thinking_text = ''
        full_analysis_text = ''
        res = self.llm.stream(analysis_msg)
        token_usage = {}
        for chunk in res:
            SQLBotLogUtil.info(chunk)
            reasoning_content_chunk = ''
            if 'reasoning_content' in chunk.additional_kwargs:
                reasoning_content_chunk = chunk.additional_kwargs.get('reasoning_content', '')
            # else:
            #     reasoning_content_chunk = chunk.get('reasoning_content')
            if reasoning_content_chunk is None:
                reasoning_content_chunk = ''
            full_thinking_text += reasoning_content_chunk

            full_analysis_text += chunk.content
            yield {'content': chunk.content, 'reasoning_content': reasoning_content_chunk}
            get_token_usage(chunk, token_usage)

        analysis_msg.append(AIMessage(full_analysis_text))

        self.current_logs[OperationEnum.ANALYSIS] = end_log(session=self.session,
                                                            log=self.current_logs[
                                                                OperationEnum.ANALYSIS],
                                                            full_message=[
                                                                {'type': msg.type,
                                                                 'content': msg.content}
                                                                for msg in analysis_msg],
                                                            reasoning_content=full_thinking_text,
                                                            token_usage=token_usage)
        self.record = save_analysis_answer(session=self.session, record_id=self.record.id,
                                           answer=orjson.dumps({'content': full_analysis_text}).decode())

    def generate_predict(self):
        fields = self.get_fields_from_chart()
        self.chat_question.fields = orjson.dumps(fields).decode()
        data = get_chat_chart_data(self.session, self.record.id)
        self.chat_question.data = orjson.dumps(data.get('data')).decode()
        predict_msg: List[Union[BaseMessage, dict[str, Any]]] = []
        predict_msg.append(SystemMessage(content=self.chat_question.predict_sys_question()))
        predict_msg.append(HumanMessage(content=self.chat_question.predict_user_question()))

        self.current_logs[OperationEnum.PREDICT_DATA] = start_log(session=self.session,
                                                                  ai_modal_id=self.chat_question.ai_modal_id,
                                                                  ai_modal_name=self.chat_question.ai_modal_name,
                                                                  operate=OperationEnum.PREDICT_DATA,
                                                                  record_id=self.record.id,
                                                                  full_message=[
                                                                      {'type': msg.type,
                                                                       'content': msg.content} for
                                                                      msg
                                                                      in predict_msg])
        full_thinking_text = ''
        full_predict_text = ''
        res = self.llm.stream(predict_msg)
        token_usage = {}
        for chunk in res:
            SQLBotLogUtil.info(chunk)
            reasoning_content_chunk = ''
            if 'reasoning_content' in chunk.additional_kwargs:
                reasoning_content_chunk = chunk.additional_kwargs.get('reasoning_content', '')
            # else:
            #     reasoning_content_chunk = chunk.get('reasoning_content')
            if reasoning_content_chunk is None:
                reasoning_content_chunk = ''
            full_thinking_text += reasoning_content_chunk

            full_predict_text += chunk.content
            yield {'content': chunk.content, 'reasoning_content': reasoning_content_chunk}
            get_token_usage(chunk, token_usage)

        predict_msg.append(AIMessage(full_predict_text))
        self.record = save_predict_answer(session=self.session, record_id=self.record.id,
                                          answer=orjson.dumps({'content': full_predict_text}).decode())
        self.current_logs[OperationEnum.PREDICT_DATA] = end_log(session=self.session,
                                                                log=self.current_logs[
                                                                    OperationEnum.PREDICT_DATA],
                                                                full_message=[
                                                                    {'type': msg.type,
                                                                     'content': msg.content}
                                                                    for msg in predict_msg],
                                                                reasoning_content=full_thinking_text,
                                                                token_usage=token_usage)

    def generate_recommend_questions_task(self):

        # get schema
        if self.ds and not self.chat_question.db_schema:
            self.chat_question.db_schema = self.out_ds_instance.get_db_schema(
                self.ds.id) if self.out_ds_instance else get_table_schema(session=self.session,
                                                                          current_user=self.current_user, ds=self.ds)

        guess_msg: List[Union[BaseMessage, dict[str, Any]]] = []
        guess_msg.append(SystemMessage(content=self.chat_question.guess_sys_question()))

        old_questions = list(map(lambda q: q.strip(), get_old_questions(self.session, self.record.datasource)))
        guess_msg.append(
            HumanMessage(content=self.chat_question.guess_user_question(orjson.dumps(old_questions).decode())))

        self.current_logs[OperationEnum.GENERATE_RECOMMENDED_QUESTIONS] = start_log(session=self.session,
                                                                                    ai_modal_id=self.chat_question.ai_modal_id,
                                                                                    ai_modal_name=self.chat_question.ai_modal_name,
                                                                                    operate=OperationEnum.GENERATE_RECOMMENDED_QUESTIONS,
                                                                                    record_id=self.record.id,
                                                                                    full_message=[
                                                                                        {'type': msg.type,
                                                                                         'content': msg.content} for
                                                                                        msg
                                                                                        in guess_msg])
        full_thinking_text = ''
        full_guess_text = ''
        token_usage = {}
        res = self.llm.stream(guess_msg)
        for chunk in res:
            SQLBotLogUtil.info(chunk)
            reasoning_content_chunk = ''
            if 'reasoning_content' in chunk.additional_kwargs:
                reasoning_content_chunk = chunk.additional_kwargs.get('reasoning_content', '')
            # else:
            #     reasoning_content_chunk = chunk.get('reasoning_content')
            if reasoning_content_chunk is None:
                reasoning_content_chunk = ''
            full_thinking_text += reasoning_content_chunk

            full_guess_text += chunk.content
            yield {'content': chunk.content, 'reasoning_content': reasoning_content_chunk}
            get_token_usage(chunk, token_usage)

        guess_msg.append(AIMessage(full_guess_text))

        self.current_logs[OperationEnum.GENERATE_RECOMMENDED_QUESTIONS] = end_log(session=self.session,
                                                                                  log=self.current_logs[
                                                                                      OperationEnum.GENERATE_RECOMMENDED_QUESTIONS],
                                                                                  full_message=[
                                                                                      {'type': msg.type,
                                                                                       'content': msg.content}
                                                                                      for msg in guess_msg],
                                                                                  reasoning_content=full_thinking_text,
                                                                                  token_usage=token_usage)
        self.record = save_recommend_question_answer(session=self.session, record_id=self.record.id,
                                                     answer={'content': full_guess_text})

        yield {'recommended_question': self.record.recommended_question}

    def select_datasource(self):
        datasource_msg: List[Union[BaseMessage, dict[str, Any]]] = []
        datasource_msg.append(SystemMessage(self.chat_question.datasource_sys_question()))
        if self.current_assistant and self.current_assistant.type != 4:
            _ds_list = get_assistant_ds(session=self.session, llm_service=self)
        else:
            oid: str = self.current_user.oid
            stmt = select(CoreDatasource.id, CoreDatasource.name, CoreDatasource.description).where(
                CoreDatasource.oid == oid)
            _ds_list = [
                {
                    "id": ds.id,
                    "name": ds.name,
                    "description": ds.description
                }
                for ds in self.session.exec(stmt)
            ]
            """ _ds_list = self.session.exec(select(CoreDatasource).options(
                load_only(CoreDatasource.id, CoreDatasource.name, CoreDatasource.description))).all() """
        if not _ds_list:
            raise SingleMessageError('No available datasource configuration found')
        ignore_auto_select = _ds_list and len(_ds_list) == 1
        # ignore auto select ds

        full_thinking_text = ''
        full_text = ''

        if not ignore_auto_select:
            _ds_list_dict = []
            for _ds in _ds_list:
                _ds_list_dict.append(_ds)
            datasource_msg.append(
                HumanMessage(self.chat_question.datasource_user_question(orjson.dumps(_ds_list_dict).decode())))

            self.current_logs[OperationEnum.CHOOSE_DATASOURCE] = start_log(session=self.session,
                                                                           ai_modal_id=self.chat_question.ai_modal_id,
                                                                           ai_modal_name=self.chat_question.ai_modal_name,
                                                                           operate=OperationEnum.CHOOSE_DATASOURCE,
                                                                           record_id=self.record.id,
                                                                           full_message=[{'type': msg.type,
                                                                                          'content': msg.content} for
                                                                                         msg in datasource_msg])

            token_usage = {}
            res = self.llm.stream(datasource_msg)
            for chunk in res:
                SQLBotLogUtil.info(chunk)
                reasoning_content_chunk = ''
                if 'reasoning_content' in chunk.additional_kwargs:
                    reasoning_content_chunk = chunk.additional_kwargs.get('reasoning_content', '')
                # else:
                #     reasoning_content_chunk = chunk.get('reasoning_content')
                if reasoning_content_chunk is None:
                    reasoning_content_chunk = ''
                full_thinking_text += reasoning_content_chunk

                full_text += chunk.content
                yield {'content': chunk.content, 'reasoning_content': reasoning_content_chunk}
                get_token_usage(chunk, token_usage)
            datasource_msg.append(AIMessage(full_text))

            self.current_logs[OperationEnum.CHOOSE_DATASOURCE] = end_log(session=self.session,
                                                                         log=self.current_logs[
                                                                             OperationEnum.CHOOSE_DATASOURCE],
                                                                         full_message=[
                                                                             {'type': msg.type, 'content': msg.content}
                                                                             for msg in datasource_msg],
                                                                         reasoning_content=full_thinking_text,
                                                                         token_usage=token_usage)

            json_str = extract_nested_json(full_text)

        _error: Exception | None = None
        _datasource: int | None = None
        _engine_type: str | None = None
        try:
            data: dict = _ds_list[0] if ignore_auto_select else orjson.loads(json_str)

            if data.get('id') and data.get('id') != 0:
                _datasource = data['id']
                _chat = self.session.get(Chat, self.record.chat_id)
                _chat.datasource = _datasource
                if self.current_assistant and self.current_assistant.type in dynamic_ds_types:
                    _ds = self.out_ds_instance.get_ds(data['id'])
                    self.ds = _ds
                    self.chat_question.engine = _ds.type + get_version(self.ds)
                    self.chat_question.db_schema = self.out_ds_instance.get_db_schema(self.ds.id)
                    _engine_type = self.chat_question.engine
                    _chat.engine_type = _ds.type
                else:
                    _ds = self.session.get(CoreDatasource, _datasource)
                    if not _ds:
                        _datasource = None
                        raise SingleMessageError(f"Datasource configuration with id {_datasource} not found")
                    self.ds = CoreDatasource(**_ds.model_dump())
                    self.chat_question.engine = (_ds.type_name if _ds.type != 'excel' else 'PostgreSQL') + get_version(
                        self.ds)
                    self.chat_question.db_schema = get_table_schema(session=self.session,
                                                                    current_user=self.current_user, ds=self.ds)
                    _engine_type = self.chat_question.engine
                    _chat.engine_type = _ds.type_name
                # save chat
                self.session.add(_chat)
                self.session.flush()
                self.session.refresh(_chat)
                self.session.commit()

            elif data['fail']:
                raise SingleMessageError(data['fail'])
            else:
                raise SingleMessageError('No available datasource configuration found')

        except Exception as e:
            _error = e

        if not ignore_auto_select:
            self.record = save_select_datasource_answer(session=self.session, record_id=self.record.id,
                                                        answer=orjson.dumps({'content': full_text}).decode(),
                                                        datasource=_datasource,
                                                        engine_type=_engine_type)

        self.chat_question.terminologies = get_terminology_template(self.session, self.chat_question.question,
                                                                    self.ds.oid if isinstance(self.ds,
                                                                                              CoreDatasource) else 1)
        self.init_messages()

        if _error:
            raise _error

    def generate_sql(self):
        # append current question
        self.sql_message.append(HumanMessage(
            self.chat_question.sql_user_question(current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))))

        self.current_logs[OperationEnum.GENERATE_SQL] = start_log(session=self.session,
                                                                  ai_modal_id=self.chat_question.ai_modal_id,
                                                                  ai_modal_name=self.chat_question.ai_modal_name,
                                                                  operate=OperationEnum.GENERATE_SQL,
                                                                  record_id=self.record.id,
                                                                  full_message=[
                                                                      {'type': msg.type, 'content': msg.content} for msg
                                                                      in self.sql_message])
        full_thinking_text = ''
        full_sql_text = ''
        token_usage = {}
        res = self.llm.stream(self.sql_message)
        for chunk in res:
            SQLBotLogUtil.info(chunk)
            reasoning_content_chunk = ''
            if 'reasoning_content' in chunk.additional_kwargs:
                reasoning_content_chunk = chunk.additional_kwargs.get('reasoning_content', '')
            # else:
            #     reasoning_content_chunk = chunk.get('reasoning_content')
            # 如果没有 reasoning_content，就用普通内容作为思考过程
            if not reasoning_content_chunk and chunk.content:
                reasoning_content_chunk = chunk.content
            if reasoning_content_chunk is None:
                reasoning_content_chunk = ''
            full_thinking_text += reasoning_content_chunk

            full_sql_text += chunk.content
            yield {'content': chunk.content, 'reasoning_content': reasoning_content_chunk}
            get_token_usage(chunk, token_usage)

        self.sql_message.append(AIMessage(full_sql_text))

        self.current_logs[OperationEnum.GENERATE_SQL] = end_log(session=self.session,
                                                                log=self.current_logs[OperationEnum.GENERATE_SQL],
                                                                full_message=[{'type': msg.type, 'content': msg.content}
                                                                              for msg in self.sql_message],
                                                                reasoning_content=full_thinking_text,
                                                                token_usage=token_usage)
    # 如果没有思考内容，用完整输出作为思考过程
        if not full_thinking_text.strip():
            full_thinking_text = f"""SQL 生成过程：
    
            用户问题：
            {self.chat_question.question}
            
            AI 完整输出：
            {full_sql_text}
            """
    
        # 保存思考过程到 sql_answer 字段
        if full_thinking_text.strip():
            save_sql_answer(session=self.session, record_id=self.record.id,
                        answer=full_thinking_text)
        else:
            # 原有逻辑
            thinking_json = {
                "reasoning_content": full_thinking_text,
                "content": "SQL生成思考过程"
            }
            save_sql_answer(session=self.session, record_id=self.record.id,
                        answer=orjson.dumps(thinking_json).decode())

    def generate_with_sub_sql(self, sql, sub_mappings: list):
        sub_query = json.dumps(sub_mappings, ensure_ascii=False)
        self.chat_question.sql = sql
        self.chat_question.sub_query = sub_query
        dynamic_sql_msg: List[Union[BaseMessage, dict[str, Any]]] = []
        dynamic_sql_msg.append(SystemMessage(content=self.chat_question.dynamic_sys_question()))
        dynamic_sql_msg.append(HumanMessage(content=self.chat_question.dynamic_user_question()))

        self.current_logs[OperationEnum.GENERATE_DYNAMIC_SQL] = start_log(session=self.session,
                                                                          ai_modal_id=self.chat_question.ai_modal_id,
                                                                          ai_modal_name=self.chat_question.ai_modal_name,
                                                                          operate=OperationEnum.GENERATE_DYNAMIC_SQL,
                                                                          record_id=self.record.id,
                                                                          full_message=[{'type': msg.type,
                                                                                         'content': msg.content}
                                                                                        for
                                                                                        msg in dynamic_sql_msg])

        full_thinking_text = ''
        full_dynamic_text = ''
        res = self.llm.stream(dynamic_sql_msg)
        token_usage = {}
        for chunk in res:
            SQLBotLogUtil.info(chunk)
            reasoning_content_chunk = ''
            if 'reasoning_content' in chunk.additional_kwargs:
                reasoning_content_chunk = chunk.additional_kwargs.get('reasoning_content', '')
            if reasoning_content_chunk is None:
                reasoning_content_chunk = ''
            full_thinking_text += reasoning_content_chunk
            full_dynamic_text += chunk.content
            get_token_usage(chunk, token_usage)

        dynamic_sql_msg.append(AIMessage(full_dynamic_text))

        self.current_logs[OperationEnum.GENERATE_DYNAMIC_SQL] = end_log(session=self.session,
                                                                        log=self.current_logs[
                                                                            OperationEnum.GENERATE_DYNAMIC_SQL],
                                                                        full_message=[
                                                                            {'type': msg.type,
                                                                             'content': msg.content}
                                                                            for msg in dynamic_sql_msg],
                                                                        reasoning_content=full_thinking_text,
                                                                        token_usage=token_usage)

        SQLBotLogUtil.info(full_dynamic_text)
        return full_dynamic_text

    def generate_assistant_dynamic_sql(self, sql, tables: List):
        ds: AssistantOutDsSchema = self.ds
        sub_query = []
        for table in ds.tables:
            if table.name in tables and table.sql:
                sub_query.append({"table": table.name, "query": table.sql})
        if not sub_query:
            return None
        return self.generate_with_sub_sql(sql=sql, sub_mappings=sub_query)

    def build_table_filter(self, sql: str, filters: list):
        filter = json.dumps(filters, ensure_ascii=False)
        self.chat_question.sql = sql
        self.chat_question.filter = filter
        permission_sql_msg: List[Union[BaseMessage, dict[str, Any]]] = []
        permission_sql_msg.append(SystemMessage(content=self.chat_question.filter_sys_question()))
        permission_sql_msg.append(HumanMessage(content=self.chat_question.filter_user_question()))

        self.current_logs[OperationEnum.GENERATE_SQL_WITH_PERMISSIONS] = start_log(session=self.session,
                                                                                   ai_modal_id=self.chat_question.ai_modal_id,
                                                                                   ai_modal_name=self.chat_question.ai_modal_name,
                                                                                   operate=OperationEnum.GENERATE_SQL_WITH_PERMISSIONS,
                                                                                   record_id=self.record.id,
                                                                                   full_message=[
                                                                                       {'type': msg.type,
                                                                                        'content': msg.content} for
                                                                                       msg
                                                                                       in permission_sql_msg])
        full_thinking_text = ''
        full_filter_text = ''
        res = self.llm.stream(permission_sql_msg)
        token_usage = {}
        for chunk in res:
            SQLBotLogUtil.info(chunk)
            reasoning_content_chunk = ''
            if 'reasoning_content' in chunk.additional_kwargs:
                reasoning_content_chunk = chunk.additional_kwargs.get('reasoning_content', '')
            # else:
            #     reasoning_content_chunk = chunk.get('reasoning_content')
            if reasoning_content_chunk is None:
                reasoning_content_chunk = ''
            full_thinking_text += reasoning_content_chunk

            full_filter_text += chunk.content
            # yield {'content': chunk.content, 'reasoning_content': reasoning_content_chunk}
            get_token_usage(chunk, token_usage)

        permission_sql_msg.append(AIMessage(full_filter_text))

        self.current_logs[OperationEnum.GENERATE_SQL_WITH_PERMISSIONS] = end_log(session=self.session,
                                                                                 log=self.current_logs[
                                                                                     OperationEnum.GENERATE_SQL_WITH_PERMISSIONS],
                                                                                 full_message=[
                                                                                     {'type': msg.type,
                                                                                      'content': msg.content}
                                                                                     for msg in permission_sql_msg],
                                                                                 reasoning_content=full_thinking_text,
                                                                                 token_usage=token_usage)

        SQLBotLogUtil.info(full_filter_text)
        return full_filter_text

    def generate_filter(self, sql: str, tables: List):
        filters = get_row_permission_filters(session=self.session, current_user=self.current_user, ds=self.ds,
                                             tables=tables)
        if not filters:
            return None
        return self.build_table_filter(sql=sql, filters=filters)

    def generate_assistant_filter(self, sql, tables: List):
        ds: AssistantOutDsSchema = self.ds
        filters = []
        for table in ds.tables:
            if table.name in tables and table.rule:
                filters.append({"table": table.name, "filter": table.rule})
        if not filters:
            return None
        return self.build_table_filter(sql=sql, filters=filters)

    def generate_chart(self, chart_type: Optional[str] = ''):
        # append current question
        self.chart_message.append(HumanMessage(self.chat_question.chart_user_question(chart_type)))

        self.current_logs[OperationEnum.GENERATE_CHART] = start_log(session=self.session,
                                                                    ai_modal_id=self.chat_question.ai_modal_id,
                                                                    ai_modal_name=self.chat_question.ai_modal_name,
                                                                    operate=OperationEnum.GENERATE_CHART,
                                                                    record_id=self.record.id,
                                                                    full_message=[
                                                                        {'type': msg.type, 'content': msg.content} for
                                                                        msg
                                                                        in self.chart_message])
        full_thinking_text = ''
        full_chart_text = ''
        token_usage = {}
        res = self.llm.stream(self.chart_message)
        for chunk in res:
            SQLBotLogUtil.info(chunk)
            reasoning_content_chunk = ''
            if 'reasoning_content' in chunk.additional_kwargs:
                reasoning_content_chunk = chunk.additional_kwargs.get('reasoning_content', '')
            # else:
            #     reasoning_content_chunk = chunk.get('reasoning_content')
            if reasoning_content_chunk is None:
                reasoning_content_chunk = ''
            full_thinking_text += reasoning_content_chunk

            full_chart_text += chunk.content
            yield {'content': chunk.content, 'reasoning_content': reasoning_content_chunk}
            get_token_usage(chunk, token_usage)

        self.chart_message.append(AIMessage(full_chart_text))

        self.record = save_chart_answer(session=self.session, record_id=self.record.id,
                                        answer=orjson.dumps({'content': full_chart_text}).decode())
        self.current_logs[OperationEnum.GENERATE_CHART] = end_log(session=self.session,
                                                                  log=self.current_logs[OperationEnum.GENERATE_CHART],
                                                                  full_message=[
                                                                      {'type': msg.type, 'content': msg.content}
                                                                      for msg in self.chart_message],
                                                                  reasoning_content=full_thinking_text,
                                                                  token_usage=token_usage)

    @staticmethod
    def check_sql(res: str) -> tuple[str, Optional[list]]:
        json_str = extract_nested_json(res)
        if json_str is None:
            raise SingleMessageError(orjson.dumps({'message': 'Cannot parse sql from answer',
                                                   'traceback': "Cannot parse sql from answer:\n" + res}).decode())
        sql: str
        data: dict
        try:
            data = orjson.loads(json_str)

            if data['success']:
                sql = data['sql']
            else:
                message = data['message']
                raise SingleMessageError(message)
        except SingleMessageError as e:
            raise e
        except Exception:
            raise SingleMessageError(orjson.dumps({'message': 'Cannot parse sql from answer',
                                                   'traceback': "Cannot parse sql from answer:\n" + res}).decode())

        if sql.strip() == '':
            raise SingleMessageError("SQL query is empty")
        return sql, data.get('tables')

    @staticmethod
    def get_chart_type_from_sql_answer(res: str) -> Optional[str]:
        json_str = extract_nested_json(res)
        if json_str is None:
            return None

        chart_type: Optional[str]
        data: dict
        try:
            data = orjson.loads(json_str)

            if data['success']:
                chart_type = data['chart-type']
            else:
                return None
        except Exception:
            return None

        return chart_type
    def validate_and_retry_sql(self, initial_sql: str, max_retries: int = 3) -> str:
        """验证 SQL 并在失败时重试生成新的 SQL"""
        current_sql = initial_sql
        retry_count = 0
        retry_errors = [] # 用于记录每次重试的错误信息
        while retry_count < max_retries:
            try:
                # 尝试执行 SQL
                test_result = self.execute_sql(sql=current_sql)
                # 如果执行成功，返回当前 SQL
                return current_sql
                
            except Exception as sql_error:
                retry_count += 1
                error_msg = str(sql_error)
                retry_errors.append(f"第{retry_count}次尝试: {error_msg}")
                
                # 只记录到日志，不保存到数据库
                SQLBotLogUtil.warning(f"SQL 执行失败 (第{retry_count}次): {error_msg}")
                
                if retry_count >= max_retries:
                    # 只有在最终失败时才保存错误信息
                    final_error_msg = f"SQL验证失败，共重试{retry_count}次:\n" + "\n".join(retry_errors)
                    save_error_message(
                        session=self.session, 
                        record_id=self.record.id,
                        message=final_error_msg
                    )
                    raise sql_error
                
                
                current_sql = self.regenerate_sql_with_error(current_sql, error_msg)

        
        return current_sql
    
    def regenerate_sql_with_error(self, failed_sql: str, error_message: str) -> str:
        """基于错误信息重新生成 SQL"""
        fix_sql_msg = []
        fix_sql_msg.append(SystemMessage(content=self.chat_question.sql_sys_question()))
        
        fix_prompt = f"""
        之前生成的 SQL 语句执行失败：
        
        SQL: {failed_sql}
        错误信息: {error_message}
        
        请分析错误原因并生成修正后的 SQL 语句。常见错误类型：
        1. 字段名错误 - 检查表结构中的实际字段名
        2. 表名错误 - 确认表是否存在
        3. 语法错误 - 检查 SQL 语法
        4. 数据类型不匹配 - 检查字段类型
        
        原始问题: {self.chat_question.question}
        数据库结构: {self.chat_question.db_schema}
        """
        
        fix_sql_msg.append(HumanMessage(content=fix_prompt))
        SQLBotLogUtil.info(f"正在重新生成 SQL，原错误: {error_message}")
        
        full_text = ''  # 这是 LLM 的完整输出，当作思考过程
        res = self.llm.stream(fix_sql_msg)
        for chunk in res:
            full_text += chunk.content
        
        SQLBotLogUtil.info(f"LLM 完整输出: {full_text}")
        
        try:
            # 获取当前记录的思考过程
            from apps.chat.models.chat_model import ChatRecord
            current_record = self.session.query(ChatRecord).filter(ChatRecord.id == self.record.id).first()
            existing_thinking = ""
            if current_record and current_record.sql_answer:
                existing_thinking = current_record.sql_answer
                SQLBotLogUtil.info(f"找到已有思考过程，长度: {len(existing_thinking)}")
        except Exception as e:
            SQLBotLogUtil.warning(f"获取已有思考过程失败: {e}")
            existing_thinking = ""
        
        # 构建重试思考过程（追加到原有内容后面）
        retry_thinking = f"""
    
            === SQL 重试修复过程 ===
            
            原始错误：
            {error_message}
            
            AI 分析和修复过程：
            {full_text}
            
            修复提示：
            {fix_prompt}
            """
        
        # 合并思考过程
        combined_thinking = existing_thinking + retry_thinking
        
            # 保存为JSON格式
        thinking_json = {
            "reasoning_content": combined_thinking,
            "content": "SQL思考过程"
        }
        save_sql_answer(session=self.session, record_id=self.record.id, 
                    answer=orjson.dumps(thinking_json).decode())
        SQLBotLogUtil.info(f"已保存合并思考过程，总长度: {len(combined_thinking)}")
        # 在保存thinking后，存储更新信息而不是直接yield
        self._retry_thinking_updates.append({
            'content': combined_thinking, 
            'reasoning_content': combined_thinking,
            'type': 'sql-retry-thinking'
        })
        try:
            # 解析新的 SQL
            fixed_sql, _ = self.check_sql(full_text)
            SQLBotLogUtil.info(f"修复后的SQL: {fixed_sql}")
            return fixed_sql
        except Exception as parse_error:
            SQLBotLogUtil.error(f"重新生成的 SQL 仍无法解析: {str(parse_error)}")
            SQLBotLogUtil.error(f"LLM 返回内容: {full_text}")
            raise Exception(f"SQL 修复失败: {str(parse_error)}")


    def check_save_sql_with_validation(self, res: str) -> str:
        """带验证的 SQL 检查和保存"""
        sql, *_ = self.check_sql(res=res)
        validated_sql = self.validate_and_retry_sql(sql)
        save_sql(session=self.session, sql=validated_sql, record_id=self.record.id)
        self.chat_question.sql = validated_sql
        return validated_sql
    def check_save_sql(self, res: str) -> str:
        sql, *_ = self.check_sql(res=res)
        save_sql(session=self.session, sql=sql, record_id=self.record.id)

        self.chat_question.sql = sql

        return sql

    def check_save_chart(self, res: str) -> Dict[str, Any]:

        json_str = extract_nested_json(res)
        if json_str is None:
            raise SingleMessageError(orjson.dumps({'message': 'Cannot parse chart config from answer',
                                                   'traceback': "Cannot parse chart config from answer:\n" + res}).decode())
        data: dict

        chart: Dict[str, Any] = {}
        message = ''
        error = False

        try:
            data = orjson.loads(json_str)
            if data['type'] and data['type'] != 'error':
                # todo type check
                chart = data
                if chart.get('columns'):
                    for v in chart.get('columns'):
                        v['value'] = v.get('value').lower()
                if chart.get('axis'):
                    if chart.get('axis').get('x'):
                        chart.get('axis').get('x')['value'] = chart.get('axis').get('x').get('value').lower()
                    if chart.get('axis').get('y'):
                        chart.get('axis').get('y')['value'] = chart.get('axis').get('y').get('value').lower()
                    if chart.get('axis').get('series'):
                        chart.get('axis').get('series')['value'] = chart.get('axis').get('series').get('value').lower()
            elif data['type'] == 'error':
                message = data['reason']
                error = True
            else:
                raise Exception('Chart is empty')
        except Exception:
            error = True
            message = orjson.dumps({'message': 'Cannot parse chart config from answer',
                                    'traceback': "Cannot parse chart config from answer:\n" + res}).decode()

        if error:
            raise SingleMessageError(message)

        save_chart(session=self.session, chart=orjson.dumps(chart).decode(), record_id=self.record.id)

        return chart

    def check_save_predict_data(self, res: str) -> bool:

        json_str = extract_nested_json(res)

        if not json_str:
            json_str = ''

        save_predict_data(session=self.session, record_id=self.record.id, data=json_str)

        if json_str == '':
            return False

        return True

    def save_error(self, message: str):
        return save_error_message(session=self.session, record_id=self.record.id, message=message)

    def save_sql_data(self, data_obj: Dict[str, Any]):
        try:
            data_result = data_obj.get('data')
            limit = 1000
            if data_result:
                data_result = prepare_for_orjson(data_result)
                if data_result and len(data_result) > limit:
                    data_obj['data'] = data_result[:limit]
                    data_obj['limit'] = limit
                else:
                    data_obj['data'] = data_result
            return save_sql_exec_data(session=self.session, record_id=self.record.id,
                                      data=orjson.dumps(data_obj).decode())
        except Exception as e:
            raise e

    def finish(self):
        return finish_record(session=self.session, record_id=self.record.id)

    def execute_sql(self, sql: str):
        """Execute SQL query

        Args:
            ds: Data source instance
            sql: SQL query statement

        Returns:
            Query results
        """
        SQLBotLogUtil.info(f"Executing SQL on ds_id {self.ds.id}: {sql}")
        try:
            return exec_sql(self.ds, sql)
        except Exception as e:
            if isinstance(e, ParseSQLResultError):
                raise e
            else:
                err = traceback.format_exc(limit=1, chain=True)
                raise SQLBotDBError(err)

    def pop_chunk(self):
        try:
            chunk = self.chunk_list.pop(0)
            return chunk
        except IndexError as e:
            return None

    def await_result(self):
        while self.is_running():
            while True:
                chunk = self.pop_chunk()
                if chunk is not None:
                    yield chunk
                else:
                    break
        while True:
            chunk = self.pop_chunk()
            if chunk is None:
                break
            yield chunk

    def run_task_async(self, in_chat: bool = True):
        self.future = executor.submit(self.run_task_cache, in_chat)

    def run_task_cache(self, in_chat: bool = True):
        for chunk in self.run_task(in_chat):
            self.chunk_list.append(chunk)

    def run_task(self, in_chat: bool = True):
        try:
            if self.ds:
                self.chat_question.terminologies = get_terminology_template(self.session, self.chat_question.question,
                                                                            self.ds.oid if isinstance(self.ds,
                                                                                                      CoreDatasource) else 1)
            self.init_messages()

            # return id
            if in_chat:
                yield 'data:' + orjson.dumps({'type': 'id', 'id': self.get_record().id}).decode() + '\n\n'

            # return title
            if self.change_title:
                if self.chat_question.question or self.chat_question.question.strip() != '':
                    brief = rename_chat(session=self.session,
                                        rename_object=RenameChat(id=self.get_record().chat_id,
                                                                 brief=self.chat_question.question.strip()[:20]))
                    if in_chat:
                        yield 'data:' + orjson.dumps({'type': 'brief', 'brief': brief}).decode() + '\n\n'

            # select datasource if datasource is none
            if not self.ds:
                ds_res = self.select_datasource()

                for chunk in ds_res:
                    SQLBotLogUtil.info(chunk)
                    if in_chat:
                        yield 'data:' + orjson.dumps(
                            {'content': chunk.get('content'), 'reasoning_content': chunk.get('reasoning_content'),
                             'type': 'datasource-result'}).decode() + '\n\n'
                if in_chat:
                    yield 'data:' + orjson.dumps({'id': self.ds.id, 'datasource_name': self.ds.name,
                                                  'engine_type': self.ds.type_name or self.ds.type,
                                                  'type': 'datasource'}).decode() + '\n\n'

                self.chat_question.db_schema = self.out_ds_instance.get_db_schema(
                    self.ds.id) if self.out_ds_instance else get_table_schema(session=self.session,
                                                                              current_user=self.current_user,
                                                                              ds=self.ds)
            else:
                self.validate_history_ds()

            # check connection
            connected = check_connection(ds=self.ds, trans=None)
            if not connected:
                raise SQLBotDBConnectionError('Connect DB failed')

            # generate sql
            sql_res = self.generate_sql()
            full_sql_text = ''
            for chunk in sql_res:
                full_sql_text += chunk.get('content')
                if in_chat:
                    yield 'data:' + orjson.dumps(
                        {'content': chunk.get('content'), 'reasoning_content': chunk.get('reasoning_content'),
                         'type': 'sql-result'}).decode() + '\n\n'
            if in_chat:
                yield 'data:' + orjson.dumps({'type': 'info', 'msg': 'sql generated'}).decode() + '\n\n'

            # filter sql
            SQLBotLogUtil.info(full_sql_text)

            chart_type = self.get_chart_type_from_sql_answer(full_sql_text)

            use_dynamic_ds: bool = self.current_assistant and self.current_assistant.type in dynamic_ds_types

            # todo row permission
            if (not self.current_assistant and is_normal_user(self.current_user)) or use_dynamic_ds:
                sql, tables = self.check_sql(res=full_sql_text)
                sql_result = None
                dynamic_sql_result = None
                if self.current_assistant:
                    dynamic_sql_result = self.generate_assistant_dynamic_sql(sql, tables)
                    if dynamic_sql_result:
                        SQLBotLogUtil.info(dynamic_sql_result)
                        sql, *_ = self.check_sql(res=dynamic_sql_result)

                    sql_result = self.generate_assistant_filter(sql, tables)
                else:
                    sql_result = self.generate_filter(sql, tables)  # maybe no sql and tables

                if sql_result:
                    SQLBotLogUtil.info(sql_result)
                    sql = self.check_save_sql_with_validation(res=sql_result)
                elif dynamic_sql_result:
                    sql = self.check_save_sql_with_validation(res=dynamic_sql_result)
                else:
                    sql = self.check_save_sql_with_validation(res=full_sql_text)
            else:
                sql = self.check_save_sql_with_validation(res=full_sql_text)
            # 在这里统一发送重试thinking更新
            for update in self._retry_thinking_updates:
                if in_chat:
                    yield 'data:' + orjson.dumps(update).decode() + '\n\n'
            
            # 清空更新列表
            self._retry_thinking_updates.clear()
            SQLBotLogUtil.info(sql)
            format_sql = sqlparse.format(sql, reindent=True)
            if in_chat:
                yield 'data:' + orjson.dumps({'content': format_sql, 'type': 'sql'}).decode() + '\n\n'
            else:
                yield f'```sql\n{format_sql}\n```\n\n'

            # execute sql
            result = self.execute_sql(sql=sql)
            self.save_sql_data(data_obj=result)
            if in_chat:
                yield 'data:' + orjson.dumps({'content': 'execute-success', 'type': 'sql-data'}).decode() + '\n\n'

            # generate chart
            chart_res = self.generate_chart(chart_type)
            full_chart_text = ''
            for chunk in chart_res:
                full_chart_text += chunk.get('content')
                if in_chat:
                    yield 'data:' + orjson.dumps(
                        {'content': chunk.get('content'), 'reasoning_content': chunk.get('reasoning_content'),
                         'type': 'chart-result'}).decode() + '\n\n'
            if in_chat:
                yield 'data:' + orjson.dumps({'type': 'info', 'msg': 'chart generated'}).decode() + '\n\n'

            # filter chart
            SQLBotLogUtil.info(full_chart_text)
            chart = self.check_save_chart(res=full_chart_text)
            SQLBotLogUtil.info(chart)
            if in_chat:
                yield 'data:' + orjson.dumps(
                    {'content': orjson.dumps(chart).decode(), 'type': 'chart'}).decode() + '\n\n'
            else:
                data = []
                _fields = {}
                if chart.get('columns'):
                    for _column in chart.get('columns'):
                        if _column:
                            _fields[_column.get('value')] = _column.get('name')
                if chart.get('axis'):
                    if chart.get('axis').get('x'):
                        _fields[chart.get('axis').get('x').get('value')] = chart.get('axis').get('x').get('name')
                    if chart.get('axis').get('y'):
                        _fields[chart.get('axis').get('y').get('value')] = chart.get('axis').get('y').get('name')
                    if chart.get('axis').get('series'):
                        _fields[chart.get('axis').get('series').get('value')] = chart.get('axis').get('series').get(
                            'name')
                _fields_list = []
                _fields_skip = False
                for _data in result.get('data'):
                    _row = []
                    for field in result.get('fields'):
                        _row.append(_data.get(field))
                        if not _fields_skip:
                            _fields_list.append(field if not _fields.get(field) else _fields.get(field))
                    data.append(_row)
                    _fields_skip = True
                df = pd.DataFrame(np.array(data), columns=_fields_list)
                markdown_table = df.to_markdown(index=False)
                yield markdown_table + '\n\n'

            record = self.finish()
            if in_chat:
                yield 'data:' + orjson.dumps({'type': 'finish'}).decode() + '\n\n'
            else:
                # todo generate picture
                if chart['type'] != 'table':
                    yield '### generated chart picture\n\n'
                    image_url = request_picture(self.record.chat_id, self.record.id, chart, result)
                    SQLBotLogUtil.info(image_url)
                    yield f'![{chart["type"]}]({image_url})'
        except Exception as e:
            error_msg: str
            if isinstance(e, SingleMessageError):
                error_msg = str(e)
            elif isinstance(e, SQLBotDBConnectionError):
                error_msg = orjson.dumps(
                    {'message': str(e), 'type': 'db-connection-err'}).decode()
            elif isinstance(e, SQLBotDBError):
                error_msg = orjson.dumps(
                    {'message': 'Execute SQL Failed', 'traceback': str(e), 'type': 'exec-sql-err'}).decode()
            else:
                error_msg = orjson.dumps({'message': str(e), 'traceback': traceback.format_exc(limit=1)}).decode()
            self.save_error(message=error_msg)
            if in_chat:
                yield 'data:' + orjson.dumps({'content': error_msg, 'type': 'error'}).decode() + '\n\n'
            else:
                yield f'> &#x274c; **ERROR**\n\n> \n\n> {error_msg}。'

    def run_recommend_questions_task_async(self):
        self.future = executor.submit(self.run_recommend_questions_task_cache)

    def run_recommend_questions_task_cache(self):
        for chunk in self.run_recommend_questions_task():
            self.chunk_list.append(chunk)

    def run_recommend_questions_task(self):
        res = self.generate_recommend_questions_task()

        for chunk in res:
            if chunk.get('recommended_question'):
                yield 'data:' + orjson.dumps(
                    {'content': chunk.get('recommended_question'), 'type': 'recommended_question'}).decode() + '\n\n'
            else:
                yield 'data:' + orjson.dumps(
                    {'content': chunk.get('content'), 'reasoning_content': chunk.get('reasoning_content'),
                     'type': 'recommended_question_result'}).decode() + '\n\n'

    def run_analysis_or_predict_task_async(self, action_type: str, base_record: ChatRecord):
        self.set_record(save_analysis_predict_record(self.session, base_record, action_type))
        self.future = executor.submit(self.run_analysis_or_predict_task_cache, action_type)

    def run_analysis_or_predict_task_cache(self, action_type: str):
        for chunk in self.run_analysis_or_predict_task(action_type):
            self.chunk_list.append(chunk)

    def run_analysis_or_predict_task(self, action_type: str):
        try:

            yield 'data:' + orjson.dumps({'type': 'id', 'id': self.get_record().id}).decode() + '\n\n'

            if action_type == 'analysis':
                # generate analysis
                analysis_res = self.generate_analysis()
                for chunk in analysis_res:
                    yield 'data:' + orjson.dumps(
                        {'content': chunk.get('content'), 'reasoning_content': chunk.get('reasoning_content'),
                         'type': 'analysis-result'}).decode() + '\n\n'
                yield 'data:' + orjson.dumps({'type': 'info', 'msg': 'analysis generated'}).decode() + '\n\n'

                yield 'data:' + orjson.dumps({'type': 'analysis_finish'}).decode() + '\n\n'

            elif action_type == 'predict':
                # generate predict
                analysis_res = self.generate_predict()
                full_text = ''
                for chunk in analysis_res:
                    yield 'data:' + orjson.dumps(
                        {'content': chunk.get('content'), 'reasoning_content': chunk.get('reasoning_content'),
                         'type': 'predict-result'}).decode() + '\n\n'
                    full_text += chunk.get('content')
                yield 'data:' + orjson.dumps({'type': 'info', 'msg': 'predict generated'}).decode() + '\n\n'

                _data = self.check_save_predict_data(res=full_text)
                if _data:
                    yield 'data:' + orjson.dumps({'type': 'predict-success'}).decode() + '\n\n'
                else:
                    yield 'data:' + orjson.dumps({'type': 'predict-failed'}).decode() + '\n\n'

                yield 'data:' + orjson.dumps({'type': 'predict_finish'}).decode() + '\n\n'

            self.finish()
        except Exception as e:
            error_msg: str
            if isinstance(e, SingleMessageError):
                error_msg = str(e)
            else:
                error_msg = orjson.dumps({'message': str(e), 'traceback': traceback.format_exc(limit=1)}).decode()
            self.save_error(message=error_msg)
            yield 'data:' + orjson.dumps({'content': error_msg, 'type': 'error'}).decode() + '\n\n'
        finally:
            # end
            pass

    def validate_history_ds(self):
        _ds = self.ds
        if not self.current_assistant or self.current_assistant.type == 4:
            try:
                current_ds = self.session.get(CoreDatasource, _ds.id)
                if not current_ds:
                    raise SingleMessageError('chat.ds_is_invalid')
            except Exception as e:
                raise SingleMessageError("chat.ds_is_invalid")
        else:
            try:
                _ds_list: list[dict] = get_assistant_ds(session=self.session, llm_service=self)
                match_ds = any(item.get("id") == _ds.id for item in _ds_list)
                if not match_ds:
                    type = self.current_assistant.type
                    msg = f"[please check ds list and public ds list]" if type == 0 else f"[please check ds api]"
                    raise SingleMessageError(msg)
            except Exception as e:
                raise SingleMessageError(f"ds is invalid [{str(e)}]")


def execute_sql_with_db(db: SQLDatabase, sql: str) -> str:
    """Execute SQL query using SQLDatabase

    Args:
        db: SQLDatabase instance
        sql: SQL query statement

    Returns:
        str: Query results formatted as string
    """
    try:
        # Execute query
        result = db.run(sql)

        if not result:
            return "Query executed successfully but returned no results."

        # Format results
        return str(result)

    except Exception as e:
        error_msg = f"SQL execution failed: {str(e)}"
        SQLBotLogUtil.exception(error_msg)
        raise RuntimeError(error_msg)


def request_picture(chat_id: int, record_id: int, chart: dict, data: dict):
    file_name = f'c_{chat_id}_r_{record_id}'

    columns = chart.get('columns') if chart.get('columns') else []
    x = None
    y = None
    series = None
    if chart.get('axis'):
        x = chart.get('axis').get('x')
        y = chart.get('axis').get('y')
        series = chart.get('axis').get('series')

    axis = []
    for v in columns:
        axis.append({'name': v.get('name'), 'value': v.get('value')})
    if x:
        axis.append({'name': x.get('name'), 'value': x.get('value'), 'type': 'x'})
    if y:
        axis.append({'name': y.get('name'), 'value': y.get('value'), 'type': 'y'})
    if series:
        axis.append({'name': series.get('name'), 'value': series.get('value'), 'type': 'series'})

    request_obj = {
        "path": (settings.MCP_IMAGE_PATH if settings.MCP_IMAGE_PATH[-1] == '/' else (
                settings.MCP_IMAGE_PATH + '/')) + file_name,
        "type": chart['type'],
        "data": orjson.dumps(data.get('data') if data.get('data') else []).decode(),
        "axis": orjson.dumps(axis).decode(),
    }

    requests.post(url=settings.MCP_IMAGE_HOST, json=request_obj)

    return f'{(settings.SERVER_IMAGE_HOST if settings.SERVER_IMAGE_HOST[-1] == "/" else (settings.SERVER_IMAGE_HOST + "/"))}{file_name}.png'


def get_token_usage(chunk: BaseMessageChunk, token_usage: dict = {}):
    try:
        if chunk.usage_metadata:
            token_usage['input_tokens'] = chunk.usage_metadata.get('input_tokens')
            token_usage['output_tokens'] = chunk.usage_metadata.get('output_tokens')
            token_usage['total_tokens'] = chunk.usage_metadata.get('total_tokens')
    except Exception:
        pass


def get_lang_name(lang: str):
    if lang and lang == 'en':
        return '英文'
    return '简体中文'
