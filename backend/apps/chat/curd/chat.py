import datetime
from typing import List

import orjson
import sqlparse
from sqlalchemy import and_, select, update

from apps.chat.models.chat_model import Chat, ChatRecord, CreateChat, ChatInfo, RenameChat, ChatQuestion
from apps.datasource.models.datasource import CoreDatasource
from apps.system.crud.assistant import AssistantOutDsFactory
from common.core.deps import CurrentAssistant, SessionDep, CurrentUser
from common.utils.utils import extract_nested_json


def get_chat_record_by_id(session: SessionDep, record_id: int):
    record: ChatRecord | None = None

    stmt = select(ChatRecord.id, ChatRecord.question, ChatRecord.chat_id, ChatRecord.datasource, ChatRecord.engine_type,
                  ChatRecord.ai_modal_id, ChatRecord.create_by).where(
        and_(ChatRecord.id == record_id))
    result = session.execute(stmt)
    for r in result:
        record = ChatRecord(id=r.id, question=r.question, chat_id=r.chat_id, datasource=r.datasource,
                            engine_type=r.engine_type, ai_modal_id=r.ai_modal_id, create_by=r.create_by)
    return record


def list_chats(session: SessionDep, current_user: CurrentUser) -> List[Chat]:
    oid = current_user.oid if current_user.oid is not None else 1
    chart_list = session.query(Chat).filter(and_(Chat.create_by == current_user.id, Chat.oid == oid)).order_by(
        Chat.create_time.desc()).all()
    return chart_list


def rename_chat(session: SessionDep, rename_object: RenameChat) -> str:
    chat = session.get(Chat, rename_object.id)
    if not chat:
        raise Exception(f"Chat with id {rename_object.id} not found")

    chat.brief = rename_object.brief.strip()[:20]
    session.add(chat)
    session.flush()
    session.refresh(chat)

    brief = chat.brief
    session.commit()
    return brief


def delete_chat(session, chart_id) -> str:
    chat = session.query(Chat).filter(Chat.id == chart_id).first()
    if not chat:
        return f'Chat with id {chart_id} has been deleted'

    session.delete(chat)
    session.commit()

    return f'Chat with id {chart_id} has been deleted'


def get_chart_config(session: SessionDep, chart_record_id: int):
    stmt = select(ChatRecord.chart).where(and_(ChatRecord.id == chart_record_id))
    res = session.execute(stmt)
    for row in res:
        try:
            return orjson.loads(row.chart)
        except Exception:
            pass
    return {}


def get_chat_chart_data(session: SessionDep, chart_record_id: int):
    stmt = select(ChatRecord.data).where(and_(ChatRecord.id == chart_record_id))
    res = session.execute(stmt)
    for row in res:
        try:
            return orjson.loads(row.data)
        except Exception:
            pass
    return []


def get_chat_predict_data(session: SessionDep, chart_record_id: int):
    stmt = select(ChatRecord.predict_data).where(and_(ChatRecord.id == chart_record_id))
    res = session.execute(stmt)
    for row in res:
        try:
            return orjson.loads(row.predict_data)
        except Exception:
            pass
    return []


def get_chat_with_records_with_data(session: SessionDep, chart_id: int, current_user: CurrentUser,
                                    current_assistant: CurrentAssistant) -> ChatInfo:
    return get_chat_with_records(session, chart_id, current_user, current_assistant, True)


def get_chat_with_records(session: SessionDep, chart_id: int, current_user: CurrentUser,
                          current_assistant: CurrentAssistant, with_data: bool = False) -> ChatInfo:
    chat = session.get(Chat, chart_id)
    if not chat:
        raise Exception(f"Chat with id {chart_id} not found")

    chat_info = ChatInfo(**chat.model_dump())

    if current_assistant and current_assistant.type == 1:
        out_ds_instance = AssistantOutDsFactory.get_instance(current_assistant)
        ds = out_ds_instance.get_ds(chat.datasource)
    else:
        ds = session.get(CoreDatasource, chat.datasource) if chat.datasource else None

    if not ds:
        chat_info.datasource_exists = False
        chat_info.datasource_name = 'Datasource not exist'
    else:
        chat_info.datasource_exists = True
        chat_info.datasource_name = ds.name
        chat_info.ds_type = ds.type

    stmt = select(ChatRecord.id, ChatRecord.chat_id, ChatRecord.create_time, ChatRecord.finish_time,
                  ChatRecord.question, ChatRecord.sql_answer, ChatRecord.sql,
                  ChatRecord.chart_answer, ChatRecord.chart, ChatRecord.analysis, ChatRecord.predict,
                  ChatRecord.datasource_select_answer, ChatRecord.analysis_record_id, ChatRecord.predict_record_id,
                  ChatRecord.recommended_question, ChatRecord.first_chat,
                  ChatRecord.finish, ChatRecord.error).where(
        and_(ChatRecord.create_by == current_user.id, ChatRecord.chat_id == chart_id)).order_by(ChatRecord.create_time)
    if with_data:
        stmt = select(ChatRecord.id, ChatRecord.chat_id, ChatRecord.create_time, ChatRecord.finish_time,
                      ChatRecord.question, ChatRecord.sql_answer, ChatRecord.sql,
                      ChatRecord.chart_answer, ChatRecord.chart, ChatRecord.analysis, ChatRecord.predict,
                      ChatRecord.datasource_select_answer, ChatRecord.analysis_record_id, ChatRecord.predict_record_id,
                      ChatRecord.recommended_question, ChatRecord.first_chat,
                      ChatRecord.finish, ChatRecord.error, ChatRecord.data, ChatRecord.predict_data).where(
            and_(ChatRecord.create_by == current_user.id, ChatRecord.chat_id == chart_id)).order_by(
            ChatRecord.create_time)

    result = session.execute(stmt).all()
    record_list: list[ChatRecord] = []
    for row in result:
        if not with_data:
            record_list.append(
                ChatRecord(id=row.id, chat_id=row.chat_id, create_time=row.create_time, finish_time=row.finish_time,
                           question=row.question, sql_answer=row.sql_answer, sql=row.sql,
                           chart_answer=row.chart_answer, chart=row.chart,
                           analysis=row.analysis, predict=row.predict,
                           datasource_select_answer=row.datasource_select_answer,
                           analysis_record_id=row.analysis_record_id, predict_record_id=row.predict_record_id,
                           recommended_question=row.recommended_question, first_chat=row.first_chat,
                           finish=row.finish, error=row.error))
        else:
            record_list.append(
                ChatRecord(id=row.id, chat_id=row.chat_id, create_time=row.create_time, finish_time=row.finish_time,
                           question=row.question, sql_answer=row.sql_answer, sql=row.sql,
                           chart_answer=row.chart_answer, chart=row.chart,
                           analysis=row.analysis, predict=row.predict,
                           datasource_select_answer=row.datasource_select_answer,
                           analysis_record_id=row.analysis_record_id, predict_record_id=row.predict_record_id,
                           recommended_question=row.recommended_question, first_chat=row.first_chat,
                           finish=row.finish, error=row.error, data=row.data, predict_data=row.predict_data))

    result = list(map(format_record, record_list))

    chat_info.records = result

    return chat_info


def format_record(record: ChatRecord):
    _dict = record.model_dump()

    if record.sql_answer and record.sql_answer.strip() != '' and record.sql_answer.strip()[0] == '{' and \
            record.sql_answer.strip()[-1] == '}':
        _obj = orjson.loads(record.sql_answer)
        _dict['sql_answer'] = _obj.get('reasoning_content')
    if record.chart_answer and record.chart_answer.strip() != '' and record.chart_answer.strip()[0] == '{' and \
            record.chart_answer.strip()[-1] == '}':
        _obj = orjson.loads(record.chart_answer)
        _dict['chart_answer'] = _obj.get('reasoning_content')
    if record.analysis and record.analysis.strip() != '' and record.analysis.strip()[0] == '{' and \
            record.analysis.strip()[-1] == '}':
        _obj = orjson.loads(record.analysis)
        _dict['analysis_thinking'] = _obj.get('reasoning_content')
        _dict['analysis'] = _obj.get('content')
    if record.predict and record.predict.strip() != '' and record.predict.strip()[0] == '{' and record.predict.strip()[
        -1] == '}':
        _obj = orjson.loads(record.predict)
        _dict['predict'] = _obj.get('reasoning_content')
        _dict['predict_content'] = _obj.get('content')
    if record.data and record.data.strip() != '':
        try:
            _obj = orjson.loads(record.data)
            _dict['data'] = _obj
        except Exception:
            pass
    if record.predict_data and record.predict_data.strip() != '':
        try:
            _obj = orjson.loads(record.predict_data)
            _dict['predict_data'] = _obj
        except Exception:
            pass
    if record.sql and record.sql.strip() != '':
        try:
            _dict['sql'] = sqlparse.format(record.sql, reindent=True)
        except Exception:
            pass

    return _dict


def list_base_records(session: SessionDep, chart_id: int, current_user: CurrentUser) -> List[ChatRecord]:
    stmt = select(ChatRecord.id, ChatRecord.chat_id, ChatRecord.full_sql_message, ChatRecord.full_chart_message,
                  ChatRecord.first_chat, ChatRecord.create_time).where(
        and_(ChatRecord.create_by == current_user.id, ChatRecord.chat_id == chart_id,
             ChatRecord.analysis_record_id.is_(None), ChatRecord.predict_record_id.is_(None))).order_by(
        ChatRecord.create_time)
    result = session.execute(stmt).all()
    record_list: List[ChatRecord] = []
    for r in result:
        record_list.append(
            ChatRecord(id=r.id, chat_id=r.chat_id, create_time=r.create_time, full_sql_message=r.full_sql_message,
                       full_chart_message=r.full_chart_message, first_chat=r.first_chat))
    return record_list


def create_chat(session: SessionDep, current_user: CurrentUser, create_chat_obj: CreateChat,
                require_datasource: bool = True) -> ChatInfo:
    if not create_chat_obj.datasource and require_datasource:
        raise Exception("Datasource cannot be None")

    if not create_chat_obj.question or create_chat_obj.question.strip() == '':
        create_chat_obj.question = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    chat = Chat(create_time=datetime.datetime.now(),
                create_by=current_user.id,
                oid=current_user.oid if current_user.oid is not None else 1,
                brief=create_chat_obj.question.strip()[:20],
                origin=create_chat_obj.origin if create_chat_obj.origin is not None else 0)
    ds: CoreDatasource | None = None
    if create_chat_obj.datasource:
        chat.datasource = create_chat_obj.datasource
        ds = session.get(CoreDatasource, create_chat_obj.datasource)

        if not ds:
            raise Exception(f"Datasource with id {create_chat_obj.datasource} not found")

        chat.engine_type = ds.type_name
    else:
        chat.engine_type = ''

    chat_info = ChatInfo(**chat.model_dump())

    session.add(chat)
    session.flush()
    session.refresh(chat)
    chat_info.id = chat.id
    session.commit()

    if ds:
        chat_info.datasource_exists = True
        chat_info.datasource_name = ds.name
        chat_info.ds_type = ds.type

    if require_datasource and ds:
        # generate first empty record
        record = ChatRecord()
        record.chat_id = chat.id
        record.datasource = ds.id
        record.engine_type = ds.type_name
        record.first_chat = True
        record.finish = True
        record.create_time = datetime.datetime.now()
        record.create_by = current_user.id

        _record = ChatRecord(**record.model_dump())

        session.add(record)
        session.flush()
        session.refresh(record)
        _record.id = record.id
        session.commit()

        chat_info.records.append(_record)

    return chat_info


def save_question(session: SessionDep, current_user: CurrentUser, question: ChatQuestion) -> ChatRecord:
    if not question.chat_id:
        raise Exception("ChatId cannot be None")
    if not question.question or question.question.strip() == '':
        raise Exception("Question cannot be Empty")

    # chat = session.query(Chat).filter(Chat.id == question.chat_id).first()
    chat: Chat = session.get(Chat, question.chat_id)
    if not chat:
        raise Exception(f"Chat with id {question.chat_id} not found")

    record = ChatRecord()
    record.question = question.question
    record.chat_id = chat.id
    record.create_time = datetime.datetime.now()
    record.create_by = current_user.id
    record.datasource = chat.datasource
    record.engine_type = chat.engine_type
    record.ai_modal_id = question.ai_modal_id

    result = ChatRecord(**record.model_dump())

    session.add(record)
    session.flush()
    session.refresh(record)
    result.id = record.id
    session.commit()

    return result


def save_analysis_predict_record(session: SessionDep, base_record: ChatRecord, action_type: str) -> ChatRecord:
    record = ChatRecord()
    record.question = base_record.question
    record.chat_id = base_record.chat_id
    record.datasource = base_record.datasource
    record.engine_type = base_record.engine_type
    record.ai_modal_id = base_record.ai_modal_id
    record.create_time = datetime.datetime.now()
    record.create_by = base_record.create_by
    record.chart = base_record.chart
    record.data = base_record.data

    if action_type == 'analysis':
        record.analysis_record_id = base_record.id
    elif action_type == 'predict':
        record.predict_record_id = base_record.id

    result = ChatRecord(**record.model_dump())

    session.add(record)
    session.flush()
    session.refresh(record)
    result.id = record.id
    session.commit()

    return result


def save_full_sql_message(session: SessionDep, record_id: int, full_message: str) -> ChatRecord:
    return save_full_sql_message_and_answer(session=session, record_id=record_id, full_message=full_message, answer='')


def save_full_sql_message_and_answer(session: SessionDep, record_id: int, answer: str, full_message: str,
                                     token_usage: dict = None) -> ChatRecord:
    if not record_id:
        raise Exception("Record id cannot be None")
    record = get_chat_record_by_id(session, record_id)

    record.full_sql_message = full_message
    record.sql_answer = answer

    if token_usage:
        record.token_sql = orjson.dumps(token_usage).decode()

    result = ChatRecord(**record.model_dump())

    stmt = update(ChatRecord).where(and_(ChatRecord.id == record.id)).values(
        full_sql_message=record.full_sql_message,
        sql_answer=record.sql_answer,
        token_sql=record.token_sql,
    )

    session.execute(stmt)

    session.commit()

    return result


def save_full_analysis_message_and_answer(session: SessionDep, record_id: int, answer: str,
                                          full_message: str, token_usage: dict = None) -> ChatRecord:
    if not record_id:
        raise Exception("Record id cannot be None")
    record = get_chat_record_by_id(session, record_id)

    record.full_analysis_message = full_message
    record.analysis = answer

    if token_usage:
        record.token_analysis = orjson.dumps(token_usage).decode()

    result = ChatRecord(**record.model_dump())

    stmt = update(ChatRecord).where(and_(ChatRecord.id == record.id)).values(
        full_analysis_message=record.full_analysis_message,
        analysis=record.analysis,
        token_analysis=record.token_analysis,
    )

    session.execute(stmt)

    session.commit()

    return result


def save_full_predict_message_and_answer(session: SessionDep, record_id: int, answer: str,
                                         full_message: str, data: str, token_usage: dict = None) -> ChatRecord:
    if not record_id:
        raise Exception("Record id cannot be None")
    record = get_chat_record_by_id(session, record_id)

    record.full_predict_message = full_message
    record.predict = answer
    record.predict_data = data

    if token_usage:
        record.token_predict = orjson.dumps(token_usage).decode()

    result = ChatRecord(**record.model_dump())

    stmt = update(ChatRecord).where(and_(ChatRecord.id == record.id)).values(
        full_predict_message=record.full_predict_message,
        predict=record.predict,
        predict_data=record.predict_data,
        token_predict=record.token_predict
    )

    session.execute(stmt)

    session.commit()

    return result


def save_full_select_datasource_message_and_answer(session: SessionDep, record_id: int, answer: str,
                                                   full_message: str, datasource: int = None,
                                                   engine_type: str = None, token_usage: dict = None) -> ChatRecord:
    if not record_id:
        raise Exception("Record id cannot be None")
    record = get_chat_record_by_id(session, record_id)

    record.full_select_datasource_message = full_message
    record.datasource_select_answer = answer

    if datasource:
        record.datasource = datasource
        record.engine_type = engine_type

    if token_usage:
        record.token_select_datasource_question = orjson.dumps(token_usage).decode()

    result = ChatRecord(**record.model_dump())

    if datasource:
        stmt = update(ChatRecord).where(and_(ChatRecord.id == record.id)).values(
            full_select_datasource_message=record.full_select_datasource_message,
            datasource_select_answer=record.datasource_select_answer,
            token_select_datasource_question=record.token_select_datasource_question,
            datasource=record.datasource,
            engine_type=record.engine_type,
        )
    else:
        stmt = update(ChatRecord).where(and_(ChatRecord.id == record.id)).values(
            full_select_datasource_message=record.full_select_datasource_message,
            datasource_select_answer=record.datasource_select_answer,
            token_select_datasource_question=record.token_select_datasource_question,
        )

    session.execute(stmt)

    session.commit()

    return result


def save_full_recommend_question_message_and_answer(session: SessionDep, record_id: int, answer: dict = None,
                                                    full_message: str = '[]', token_usage: dict = None) -> ChatRecord:
    if not record_id:
        raise Exception("Record id cannot be None")
    record = get_chat_record_by_id(session, record_id)

    record.full_recommended_question_message = full_message

    if answer:
        record.recommended_question_answer = orjson.dumps(answer).decode()

    json_str = '[]'
    if answer and answer.get('content') and answer.get('content') != '':
        try:
            json_str = extract_nested_json(answer.get('content'))

            if not json_str:
                json_str = '[]'
        except Exception as e:
            pass
    record.recommended_question = json_str

    if token_usage:
        record.token_recommended_question = orjson.dumps(token_usage).decode()

    result = ChatRecord(**record.model_dump())

    stmt = update(ChatRecord).where(and_(ChatRecord.id == record.id)).values(
        full_recommended_question_message=record.full_recommended_question_message,
        recommended_question_answer=record.recommended_question_answer,
        recommended_question=record.recommended_question,
        token_recommended_question=record.token_recommended_question
    )

    session.execute(stmt)

    session.commit()

    return result


def save_sql(session: SessionDep, record_id: int, sql: str) -> ChatRecord:
    if not record_id:
        raise Exception("Record id cannot be None")

    record = get_chat_record_by_id(session, record_id)

    record.sql = sql

    result = ChatRecord(**record.model_dump())

    stmt = update(ChatRecord).where(and_(ChatRecord.id == record.id)).values(
        sql=record.sql
    )

    session.execute(stmt)

    session.commit()

    return result


def save_full_chart_message(session: SessionDep, record_id: int, full_message: str) -> ChatRecord:
    return save_full_chart_message_and_answer(session=session, record_id=record_id, full_message=full_message,
                                              answer='')


def save_full_chart_message_and_answer(session: SessionDep, record_id: int, answer: str,
                                       full_message: str, token_usage: dict = None) -> ChatRecord:
    if not record_id:
        raise Exception("Record id cannot be None")
    record = get_chat_record_by_id(session, record_id)

    record.full_chart_message = full_message
    record.chart_answer = answer

    if token_usage:
        record.token_chart = orjson.dumps(token_usage).decode()

    result = ChatRecord(**record.model_dump())

    stmt = update(ChatRecord).where(and_(ChatRecord.id == record.id)).values(
        full_chart_message=record.full_chart_message,
        chart_answer=record.chart_answer,
        token_chart=record.token_chart
    )

    session.execute(stmt)

    session.commit()

    return result


def save_chart(session: SessionDep, record_id: int, chart: str) -> ChatRecord:
    if not record_id:
        raise Exception("Record id cannot be None")
    record = get_chat_record_by_id(session, record_id)

    record.chart = chart

    result = ChatRecord(**record.model_dump())

    stmt = update(ChatRecord).where(and_(ChatRecord.id == record.id)).values(
        chart=record.chart
    )

    session.execute(stmt)

    session.commit()

    return result


def save_predict_data(session: SessionDep, record_id: int, data: str = '') -> ChatRecord:
    if not record_id:
        raise Exception("Record id cannot be None")
    record = get_chat_record_by_id(session, record_id)

    record.predict_data = data

    result = ChatRecord(**record.model_dump())

    stmt = update(ChatRecord).where(and_(ChatRecord.id == record.id)).values(
        predict_data=record.predict_data
    )

    session.execute(stmt)

    session.commit()

    return result


def save_error_message(session: SessionDep, record_id: int, message: str) -> ChatRecord:
    if not record_id:
        raise Exception("Record id cannot be None")
    record = get_chat_record_by_id(session, record_id)

    record.error = message
    record.finish = True
    record.finish_time = datetime.datetime.now()

    result = ChatRecord(**record.model_dump())

    stmt = update(ChatRecord).where(and_(ChatRecord.id == record.id)).values(
        error=record.error,
        finish=record.finish,
        finish_time=record.finish_time
    )

    session.execute(stmt)

    session.commit()

    return result


def save_sql_exec_data(session: SessionDep, record_id: int, data: str) -> ChatRecord:
    if not record_id:
        raise Exception("Record id cannot be None")
    record = get_chat_record_by_id(session, record_id)

    record.data = data

    result = ChatRecord(**record.model_dump())

    stmt = update(ChatRecord).where(and_(ChatRecord.id == record.id)).values(
        data=record.data,
    )

    session.execute(stmt)

    session.commit()

    return result


def finish_record(session: SessionDep, record_id: int) -> ChatRecord:
    if not record_id:
        raise Exception("Record id cannot be None")
    record = get_chat_record_by_id(session, record_id)

    record.finish = True
    record.finish_time = datetime.datetime.now()

    result = ChatRecord(**record.model_dump())

    stmt = update(ChatRecord).where(and_(ChatRecord.id == record.id)).values(
        finish=record.finish,
        finish_time=record.finish_time
    )

    session.execute(stmt)

    session.commit()

    return result


def get_old_questions(session: SessionDep, datasource: int):
    records = []
    if not datasource:
        return records
    stmt = select(ChatRecord.question).where(
        and_(ChatRecord.datasource == datasource, ChatRecord.question.isnot(None))).order_by(
        ChatRecord.create_time.desc()).limit(20)
    result = session.execute(stmt)
    for r in result:
        records.append(r.question)
    return records
