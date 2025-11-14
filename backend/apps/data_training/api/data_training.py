import asyncio
import io
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from apps.chat.models.chat_model import AxisObj
from apps.chat.task.llm import LLMService
from apps.data_training.curd.data_training import page_data_training, create_training, update_training, delete_training, \
    enable_training, get_all_data_training
from apps.data_training.models.data_training_model import DataTrainingInfo
from common.core.deps import SessionDep, CurrentUser, Trans

router = APIRouter(tags=["DataTraining"], prefix="/system/data-training")


@router.get("/page/{current_page}/{page_size}")
async def pager(session: SessionDep, current_user: CurrentUser, current_page: int, page_size: int,
                question: Optional[str] = Query(None, description="搜索问题(可选)")):
    current_page, page_size, total_count, total_pages, _list = page_data_training(session, current_page, page_size,
                                                                                  question,
                                                                                  current_user.oid)

    return {
        "current_page": current_page,
        "page_size": page_size,
        "total_count": total_count,
        "total_pages": total_pages,
        "data": _list
    }


@router.put("")
async def create_or_update(session: SessionDep, current_user: CurrentUser, trans: Trans, info: DataTrainingInfo):
    oid = current_user.oid
    if info.id:
        return update_training(session, info, oid, trans)
    else:
        return create_training(session, info, oid, trans)


@router.delete("")
async def delete(session: SessionDep, id_list: list[int]):
    delete_training(session, id_list)


@router.get("/{id}/enable/{enabled}")
async def enable(session: SessionDep, id: int, enabled: bool, trans: Trans):
    enable_training(session, id, enabled, trans)


@router.get("/export")
async def export_excel(session: SessionDep, trans: Trans, current_user: CurrentUser,
                       word: Optional[str] = Query(None, description="搜索术语(可选)")):
    def inner():
        _list = get_all_data_training(session, word, oid=current_user.oid)

        data_list = []
        for obj in _list:
            _data = {
                "question": obj.question,
                "description": obj.description,
                "datasource_name": obj.datasource_name,
                "advanced_application_name": obj.advanced_application_name,
            }
            data_list.append(_data)

        fields = []
        fields.append(AxisObj(name=trans('i18n_data_training.data_training'), value='question'))
        fields.append(AxisObj(name=trans('i18n_data_training.problem_description'), value='description'))
        fields.append(AxisObj(name=trans('i18n_data_training.effective_data_sources'), value='datasource_name'))
        if current_user.oid == 1:
            fields.append(
                AxisObj(name=trans('i18n_data_training.advanced_application'), value='advanced_application_name'))

        md_data, _fields_list = LLMService.convert_object_array_for_pandas(fields, data_list)

        df = pd.DataFrame(md_data, columns=_fields_list)

        buffer = io.BytesIO()

        with pd.ExcelWriter(buffer, engine='xlsxwriter',
                            engine_kwargs={'options': {'strings_to_numbers': False}}) as writer:
            df.to_excel(writer, sheet_name='Sheet1', index=False)

        buffer.seek(0)
        return io.BytesIO(buffer.getvalue())

    result = await asyncio.to_thread(inner)
    return StreamingResponse(result, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
