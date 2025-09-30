import concurrent
import json
import os
import traceback
import urllib.parse
import warnings
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime
from typing import Any, List, Optional, Union, Dict, Iterator

import numpy as np
import orjson
import pandas as pd
import requests
import sqlparse
from langchain.chat_models.base import BaseChatModel
from langchain_community.utilities import SQLDatabase
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, BaseMessageChunk
from sqlalchemy import and_, select
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session

from apps.ai_model.model_factory import LLMConfig, LLMFactory, get_default_config
from apps.chat.curd.chat import save_question, save_sql_answer, save_sql, \
    save_error_message, save_sql_exec_data, save_chart_answer, save_chart, \
    finish_record, save_analysis_answer, save_predict_answer, save_predict_data, \
    save_select_datasource_answer, save_recommend_question_answer, \
    get_old_questions, save_analysis_predict_record, rename_chat, get_chart_config, \
    get_chat_chart_data, list_generate_sql_logs, list_generate_chart_logs, start_log, end_log, \
    get_last_execute_sql_error
from apps.chat.models.chat_model import ChatQuestion, ChatRecord, Chat, RenameChat, ChatLog, OperationEnum, \
    ChatFinishStep
from sqlbot_xpack.license.license_manage import SQLBotLicenseUtil
from sqlbot_xpack.custom_prompt.curd.custom_prompt import find_custom_prompts
from sqlbot_xpack.custom_prompt.models.custom_prompt_model import CustomPromptTypeEnum
from apps.data_training.curd.data_training import get_training_template
from apps.datasource.crud.datasource import get_table_schema
from apps.datasource.crud.permission import get_row_permission_filters, is_normal_user
from apps.datasource.embedding.ds_embedding import get_ds_embedding
from apps.datasource.models.datasource import CoreDatasource
from apps.db.db import exec_sql, get_version, check_connection
from apps.system.crud.assistant import AssistantOutDs, AssistantOutDsFactory, get_assistant_ds
from apps.system.schemas.system_schema import AssistantOutDsSchema
from apps.terminology.curd.terminology import get_terminology_template
from common.core.config import settings
from common.core.db import engine
from common.core.deps import CurrentAssistant, CurrentUser
from common.error import SingleMessageError, SQLBotDBError, ParseSQLResultError, SQLBotDBConnectionError
from common.utils.utils import SQLBotLogUtil, extract_nested_json, prepare_for_orjson

warnings.filterwarnings("ignore")

base_message_count_limit = 6

executor = ThreadPoolExecutor(max_workers=200)

dynamic_ds_types = [1, 3]
dynamic_subsql_prefix = 'select * from sqlbot_dynamic_temp_table_'

session_maker = sessionmaker(bind=engine)
db_session = session_maker()


class LLMService:
    ds: CoreDatasource
    chat_question: ChatQuestion
    record: ChatRecord
    config: LLMConfig
    llm: BaseChatModel
    sql_message: List[Union[BaseMessage, dict[str, Any]]] = []
    chart_message: List[Union[BaseMessage, dict[str, Any]]] = []

    session: Session = db_session
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
                 embedding: bool = False, config: LLMConfig = None):
        self.chunk_list = []
        # engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
        # session_maker = sessionmaker(bind=engine)
        # self.session = session_maker()
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
                chat_question.db_schema = get_table_schema(session=self.session, current_user=current_user, ds=ds,
                                                           question=chat_question.question, embedding=embedding)

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

        ds_id = self.ds.id if isinstance(self.ds, CoreDatasource) else None
        self.chat_question.terminologies = get_terminology_template(self.session, self.chat_question.question,
                                                                    self.current_user.oid, ds_id)
        if SQLBotLicenseUtil.valid():
            self.chat_question.custom_prompt = find_custom_prompts(self.session, CustomPromptTypeEnum.ANALYSIS,
                                                               self.current_user.oid, ds_id)

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
        token_usage = {}
        res = process_stream(self.llm.stream(analysis_msg), token_usage)
        for chunk in res:
            if chunk.get('content'):
                full_analysis_text += chunk.get('content')
            if chunk.get('reasoning_content'):
                full_thinking_text += chunk.get('reasoning_content')
            yield chunk

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

        if SQLBotLicenseUtil.valid():
            ds_id = self.ds.id if isinstance(self.ds, CoreDatasource) else None
            self.chat_question.custom_prompt = find_custom_prompts(self.session, CustomPromptTypeEnum.PREDICT_DATA,
                                                               self.current_user.oid, ds_id)

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
        token_usage = {}
        res = process_stream(self.llm.stream(predict_msg), token_usage)
        for chunk in res:
            if chunk.get('content'):
                full_predict_text += chunk.get('content')
            if chunk.get('reasoning_content'):
                full_thinking_text += chunk.get('reasoning_content')
            yield chunk

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
                                                                          current_user=self.current_user, ds=self.ds,
                                                                          question=self.chat_question.question,
                                                                          embedding=False)

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
        res = process_stream(self.llm.stream(guess_msg), token_usage)
        for chunk in res:
            if chunk.get('content'):
                full_guess_text += chunk.get('content')
            if chunk.get('reasoning_content'):
                full_thinking_text += chunk.get('reasoning_content')
            yield chunk

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
            stmt = select(CoreDatasource.id, CoreDatasource.name, CoreDatasource.description).where(
                and_(CoreDatasource.oid == self.current_user.oid))
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
            if settings.TABLE_EMBEDDING_ENABLED:
                ds = get_ds_embedding(self.session, self.current_user, _ds_list, self.out_ds_instance,
                                      self.chat_question.question, self.current_assistant)
                yield {'content': '{"id":' + str(ds.get('id')) + '}'}
            else:
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
                                                                                              'content': msg.content}
                                                                                             for
                                                                                             msg in datasource_msg])

                token_usage = {}
                res = process_stream(self.llm.stream(datasource_msg), token_usage)
                for chunk in res:
                    if chunk.get('content'):
                        full_text += chunk.get('content')
                    if chunk.get('reasoning_content'):
                        full_thinking_text += chunk.get('reasoning_content')
                    yield chunk
                datasource_msg.append(AIMessage(full_text))

                self.current_logs[OperationEnum.CHOOSE_DATASOURCE] = end_log(session=self.session,
                                                                             log=self.current_logs[
                                                                                 OperationEnum.CHOOSE_DATASOURCE],
                                                                             full_message=[
                                                                                 {'type': msg.type,
                                                                                  'content': msg.content}
                                                                                 for msg in datasource_msg],
                                                                             reasoning_content=full_thinking_text,
                                                                             token_usage=token_usage)

                json_str = extract_nested_json(full_text)
                if json_str is None:
                    raise SingleMessageError(f'Cannot parse datasource from answer: {full_text}')
                ds = orjson.loads(json_str)

        _error: Exception | None = None
        _datasource: int | None = None
        _engine_type: str | None = None
        try:
            data: dict = _ds_list[0] if ignore_auto_select else ds

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
                                                                    current_user=self.current_user, ds=self.ds,
                                                                    question=self.chat_question.question)
                    _engine_type = self.chat_question.engine
                    _chat.engine_type = _ds.type_name
                # save chat
                with self.session.begin_nested():
                    # 为了能继续记日志，先单独处理下事务
                    try:
                        self.session.add(_chat)
                        self.session.flush()
                        self.session.refresh(_chat)
                        self.session.commit()
                    except Exception as e:
                        self.session.rollback()
                        raise e

            elif data['fail']:
                raise SingleMessageError(data['fail'])
            else:
                raise SingleMessageError('No available datasource configuration found')

        except Exception as e:
            _error = e

        if not ignore_auto_select and not settings.TABLE_EMBEDDING_ENABLED:
            self.record = save_select_datasource_answer(session=self.session, record_id=self.record.id,
                                                        answer=orjson.dumps({'content': full_text}).decode(),
                                                        datasource=_datasource,
                                                        engine_type=_engine_type)
        if self.ds:
            oid = self.ds.oid if isinstance(self.ds, CoreDatasource) else 1
            ds_id = self.ds.id if isinstance(self.ds, CoreDatasource) else None

            self.chat_question.terminologies = get_terminology_template(self.session, self.chat_question.question, oid,
                                                                        ds_id)
            self.chat_question.data_training = get_training_template(self.session, self.chat_question.question, ds_id,
                                                                     oid)
            if SQLBotLicenseUtil.valid():
                self.chat_question.custom_prompt = find_custom_prompts(self.session, CustomPromptTypeEnum.GENERATE_SQL,
                                                                   oid, ds_id)

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
        res = process_stream(self.llm.stream(self.sql_message), token_usage)
        for chunk in res:
            if chunk.get('content'):
                full_sql_text += chunk.get('content')
            if chunk.get('reasoning_content'):
                full_thinking_text += chunk.get('reasoning_content')
            yield chunk

        self.sql_message.append(AIMessage(full_sql_text))

        self.current_logs[OperationEnum.GENERATE_SQL] = end_log(session=self.session,
                                                                log=self.current_logs[OperationEnum.GENERATE_SQL],
                                                                full_message=[{'type': msg.type, 'content': msg.content}
                                                                              for msg in self.sql_message],
                                                                reasoning_content=full_thinking_text,
                                                                token_usage=token_usage)
        self.record = save_sql_answer(session=self.session, record_id=self.record.id,
                                      answer=orjson.dumps({'content': full_sql_text}).decode())

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
        token_usage = {}
        res = process_stream(self.llm.stream(dynamic_sql_msg), token_usage)
        for chunk in res:
            if chunk.get('content'):
                full_dynamic_text += chunk.get('content')
            if chunk.get('reasoning_content'):
                full_thinking_text += chunk.get('reasoning_content')
            yield chunk

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
        result_dict = {}
        for table in ds.tables:
            if table.name in tables and table.sql:
                # sub_query.append({"table": table.name, "query": table.sql})
                result_dict[table.name] = table.sql
                sub_query.append({"table": table.name, "query": f'{dynamic_subsql_prefix}{table.name}'})
        if not sub_query:
            return None
        temp_sql_text = self.generate_with_sub_sql(sql=sql, sub_mappings=sub_query)
        result_dict['sqlbot_temp_sql_text'] = temp_sql_text
        return result_dict

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
        token_usage = {}
        res = process_stream(self.llm.stream(permission_sql_msg), token_usage)
        for chunk in res:
            if chunk.get('content'):
                full_filter_text += chunk.get('content')
            if chunk.get('reasoning_content'):
                full_thinking_text += chunk.get('reasoning_content')

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
        res = process_stream(self.llm.stream(self.chart_message), token_usage)
        for chunk in res:
            if chunk.get('content'):
                full_chart_text += chunk.get('content')
            if chunk.get('reasoning_content'):
                full_thinking_text += chunk.get('reasoning_content')
            yield chunk

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
            return exec_sql(ds=self.ds, sql=sql, origin_column=False)
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

    def run_task_async(self, in_chat: bool = True, stream: bool = True,
                       finish_step: ChatFinishStep = ChatFinishStep.GENERATE_CHART):
        if in_chat:
            stream = True
        self.future = executor.submit(self.run_task_cache, in_chat, stream, finish_step)

    def run_task_cache(self, in_chat: bool = True, stream: bool = True,
                       finish_step: ChatFinishStep = ChatFinishStep.GENERATE_CHART):
        for chunk in self.run_task(in_chat, stream, finish_step):
            self.chunk_list.append(chunk)

    def run_task(self, in_chat: bool = True, stream: bool = True,
                 finish_step: ChatFinishStep = ChatFinishStep.GENERATE_CHART):
        json_result: Dict[str, Any] = {'success': True}
        try:
            if self.ds:
                oid = self.ds.oid if isinstance(self.ds, CoreDatasource) else 1
                ds_id = self.ds.id if isinstance(self.ds, CoreDatasource) else None
                self.chat_question.terminologies = get_terminology_template(self.session, self.chat_question.question,
                                                                            oid, ds_id)
                self.chat_question.data_training = get_training_template(self.session, self.chat_question.question,
                                                                         ds_id, oid)
                if SQLBotLicenseUtil.valid():
                    self.chat_question.custom_prompt = find_custom_prompts(self.session, CustomPromptTypeEnum.GENERATE_SQL,
                                                                       oid, ds_id)

            self.init_messages()

            # return id
            if in_chat:
                yield 'data:' + orjson.dumps({'type': 'id', 'id': self.get_record().id}).decode() + '\n\n'
            if not stream:
                json_result['record_id'] = self.get_record().id

            # return title
            if self.change_title:
                if self.chat_question.question or self.chat_question.question.strip() != '':
                    brief = rename_chat(session=self.session,
                                        rename_object=RenameChat(id=self.get_record().chat_id,
                                                                 brief=self.chat_question.question.strip()[:20]))
                    if in_chat:
                        yield 'data:' + orjson.dumps({'type': 'brief', 'brief': brief}).decode() + '\n\n'
                    if not stream:
                        json_result['title'] = brief

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
                                                                              ds=self.ds,
                                                                              question=self.chat_question.question)
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
            is_page_embedded: bool = self.current_assistant and self.current_assistant.type == 4
            dynamic_sql_result = None
            sqlbot_temp_sql_text = None
            assistant_dynamic_sql = None
            # todo row permission
            if ((not self.current_assistant or is_page_embedded) and is_normal_user(
                    self.current_user)) or use_dynamic_ds:
                sql, tables = self.check_sql(res=full_sql_text)
                sql_result = None

                if use_dynamic_ds:
                    dynamic_sql_result = self.generate_assistant_dynamic_sql(sql, tables)
                    sqlbot_temp_sql_text = dynamic_sql_result.get(
                        'sqlbot_temp_sql_text') if dynamic_sql_result else None
                    # sql_result = self.generate_assistant_filter(sql, tables)
                else:
                    sql_result = self.generate_filter(sql, tables)  # maybe no sql and tables

                if sql_result:
                    SQLBotLogUtil.info(sql_result)
                    sql = self.check_save_sql(res=sql_result)
                elif dynamic_sql_result and sqlbot_temp_sql_text:
                    assistant_dynamic_sql = self.check_save_sql(res=sqlbot_temp_sql_text)
                else:
                    sql = self.check_save_sql(res=full_sql_text)
            else:
                sql = self.check_save_sql(res=full_sql_text)

            SQLBotLogUtil.info('sql: ' + sql)

            if not stream:
                json_result['sql'] = sql

            format_sql = sqlparse.format(sql, reindent=True)
            if in_chat:
                yield 'data:' + orjson.dumps({'content': format_sql, 'type': 'sql'}).decode() + '\n\n'
            else:
                if stream:
                    yield f'```sql\n{format_sql}\n```\n\n'

            # execute sql
            real_execute_sql = sql
            if sqlbot_temp_sql_text and assistant_dynamic_sql:
                dynamic_sql_result.pop('sqlbot_temp_sql_text')
                for origin_table, subsql in dynamic_sql_result.items():
                    assistant_dynamic_sql = assistant_dynamic_sql.replace(f'{dynamic_subsql_prefix}{origin_table}',
                                                                          subsql)
                real_execute_sql = assistant_dynamic_sql

            if finish_step.value <= ChatFinishStep.GENERATE_SQL.value:
                if in_chat:
                    yield 'data:' + orjson.dumps({'type': 'finish'}).decode() + '\n\n'
                if not stream:
                    yield json_result
                return

            result = self.execute_sql(sql=real_execute_sql)
            self.save_sql_data(data_obj=result)
            if in_chat:
                yield 'data:' + orjson.dumps({'content': 'execute-success', 'type': 'sql-data'}).decode() + '\n\n'
            if not stream:
                json_result['data'] = result.get('data')

            if finish_step.value <= ChatFinishStep.QUERY_DATA.value:
                if stream:
                    if in_chat:
                        yield 'data:' + orjson.dumps({'type': 'finish'}).decode() + '\n\n'
                    else:
                        data = []
                        _fields_list = []
                        _fields_skip = False
                        for _data in result.get('data'):
                            _row = []
                            for field in result.get('fields'):
                                _row.append(_data.get(field))
                                if not _fields_skip:
                                    _fields_list.append(field)
                            data.append(_row)
                            _fields_skip = True

                        if not data or not _fields_list:
                            yield 'The SQL execution result is empty.\n\n'
                        else:
                            df = pd.DataFrame(np.array(data), columns=_fields_list)
                            markdown_table = df.to_markdown(index=False)
                            yield markdown_table + '\n\n'
                else:
                    yield json_result
                return

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

            if not stream:
                json_result['chart'] = chart

            if in_chat:
                yield 'data:' + orjson.dumps(
                    {'content': orjson.dumps(chart).decode(), 'type': 'chart'}).decode() + '\n\n'
            else:
                if stream:
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

                    if not data or not _fields_list:
                        yield 'The SQL execution result is empty.\n\n'
                    else:
                        df = pd.DataFrame(np.array(data), columns=_fields_list)
                        markdown_table = df.to_markdown(index=False)
                        yield markdown_table + '\n\n'

            if in_chat:
                yield 'data:' + orjson.dumps({'type': 'finish'}).decode() + '\n\n'
            else:
                # todo generate picture
                if chart['type'] != 'table':
                    yield '### generated chart picture\n\n'
                    image_url = request_picture(self.record.chat_id, self.record.id, chart, result)
                    SQLBotLogUtil.info(image_url)
                    if stream:
                        yield f'![{chart["type"]}]({image_url})'
                    else:
                        json_result['image_url'] = image_url

            if not stream:
                yield json_result

        except Exception as e:
            traceback.print_exc()
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
                if stream:
                    yield f'> &#x274c; **ERROR**\n\n> \n\n> {error_msg}。'
                else:
                    json_result['success'] = False
                    json_result['message'] = error_msg
                    yield json_result
        finally:
            self.finish()

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
        "path": os.path.join(settings.MCP_IMAGE_PATH, file_name),
        "type": chart['type'],
        "data": orjson.dumps(data.get('data') if data.get('data') else []).decode(),
        "axis": orjson.dumps(axis).decode(),
    }

    requests.post(url=settings.MCP_IMAGE_HOST, json=request_obj)

    request_path = urllib.parse.urljoin(settings.SERVER_IMAGE_HOST, f"{file_name}.png")

    return request_path


def get_token_usage(chunk: BaseMessageChunk, token_usage: dict = None):
    try:
        if chunk.usage_metadata:
            if token_usage is None:
                token_usage = {}
            token_usage['input_tokens'] = chunk.usage_metadata.get('input_tokens')
            token_usage['output_tokens'] = chunk.usage_metadata.get('output_tokens')
            token_usage['total_tokens'] = chunk.usage_metadata.get('total_tokens')
    except Exception:
        pass


def process_stream(res: Iterator[BaseMessageChunk],
                   token_usage: Dict[str, Any] = None,
                   enable_tag_parsing: bool = settings.PARSE_REASONING_BLOCK_ENABLED,
                   start_tag: str = settings.DEFAULT_REASONING_CONTENT_START,
                   end_tag: str = settings.DEFAULT_REASONING_CONTENT_END
                   ):
    if token_usage is None:
        token_usage = {}
    in_thinking_block = False  # 标记是否在思考过程块中
    current_thinking = ''  # 当前收集的思考过程内容
    pending_start_tag = ''  # 用于缓存可能被截断的开始标签部分

    for chunk in res:
        SQLBotLogUtil.info(chunk)
        reasoning_content_chunk = ''
        content = chunk.content
        output_content = ''  # 实际要输出的内容

        # 检查additional_kwargs中的reasoning_content
        if 'reasoning_content' in chunk.additional_kwargs:
            reasoning_content = chunk.additional_kwargs.get('reasoning_content', '')
            if reasoning_content is None:
                reasoning_content = ''

            # 累积additional_kwargs中的思考内容到current_thinking
            current_thinking += reasoning_content
            reasoning_content_chunk = reasoning_content

        # 只有当current_thinking不是空字符串时才跳过标签解析
        if not in_thinking_block and current_thinking.strip() != '':
            output_content = content  # 正常输出content
            yield {
                'content': output_content,
                'reasoning_content': reasoning_content_chunk
            }
            get_token_usage(chunk, token_usage)
            continue  # 跳过后续的标签解析逻辑

        # 如果没有有效的思考内容，并且启用了标签解析，才执行标签解析逻辑
        # 如果有缓存的开始标签部分，先拼接当前内容
        if pending_start_tag:
            content = pending_start_tag + content
            pending_start_tag = ''

        # 检查是否开始思考过程块（处理可能被截断的开始标签）
        if enable_tag_parsing and not in_thinking_block and start_tag:
            if start_tag in content:
                start_idx = content.index(start_tag)
                # 只有当开始标签前面没有其他文本时才认为是真正的思考块开始
                if start_idx == 0 or content[:start_idx].strip() == '':
                    # 完整标签存在且前面没有其他文本
                    output_content += content[:start_idx]  # 输出开始标签之前的内容
                    content = content[start_idx + len(start_tag):]  # 移除开始标签
                    in_thinking_block = True
                else:
                    # 开始标签前面有其他文本，不认为是思考块开始
                    output_content += content
                    content = ''
            else:
                # 检查是否可能有部分开始标签
                for i in range(1, len(start_tag)):
                    if content.endswith(start_tag[:i]):
                        # 只有当当前内容全是空白时才缓存部分标签
                        if content[:-i].strip() == '':
                            pending_start_tag = start_tag[:i]
                            content = content[:-i]  # 移除可能的部分标签
                            output_content += content
                            content = ''
                        break

        # 处理思考块内容
        if enable_tag_parsing and in_thinking_block and end_tag:
            if end_tag in content:
                # 找到结束标签
                end_idx = content.index(end_tag)
                current_thinking += content[:end_idx]  # 收集思考内容
                reasoning_content_chunk += current_thinking  # 添加到当前块的思考内容
                content = content[end_idx + len(end_tag):]  # 移除结束标签后的内容
                current_thinking = ''  # 重置当前思考内容
                in_thinking_block = False
                output_content += content  # 输出结束标签之后的内容
            else:
                # 在遇到结束标签前，持续收集思考内容
                current_thinking += content
                reasoning_content_chunk += content
                content = ''

        else:
            # 不在思考块中或标签解析未启用，正常输出
            output_content += content

        yield {
            'content': output_content,
            'reasoning_content': reasoning_content_chunk
        }
        get_token_usage(chunk, token_usage)


def get_lang_name(lang: str):
    if not lang:
        return '简体中文'
    normalized = lang.lower()
    if normalized.startswith('en'):
        return '英文'
    if normalized.startswith('ko'):
        return '韩语'
    return '简体中文'
