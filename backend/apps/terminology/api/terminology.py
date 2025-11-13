import asyncio
import io
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from apps.chat.models.chat_model import AxisObj
from apps.chat.task.llm import LLMService
from apps.terminology.curd.terminology import page_terminology, create_terminology, update_terminology, \
    delete_terminology, enable_terminology, get_all_terminology
from apps.terminology.models.terminology_model import TerminologyInfo
from common.core.deps import SessionDep, CurrentUser, Trans

router = APIRouter(tags=["Terminology"], prefix="/system/terminology")


@router.get("/page/{current_page}/{page_size}")
async def pager(session: SessionDep, current_user: CurrentUser, current_page: int, page_size: int,
                word: Optional[str] = Query(None, description="搜索术语(可选)")):
    current_page, page_size, total_count, total_pages, _list = page_terminology(session, current_page, page_size, word,
                                                                                current_user.oid)

    return {
        "current_page": current_page,
        "page_size": page_size,
        "total_count": total_count,
        "total_pages": total_pages,
        "data": _list
    }


@router.put("")
async def create_or_update(session: SessionDep, current_user: CurrentUser, trans: Trans, info: TerminologyInfo):
    oid = current_user.oid
    if info.id:
        return update_terminology(session, info, oid, trans)
    else:
        return create_terminology(session, info, oid, trans)


@router.delete("")
async def delete(session: SessionDep, id_list: list[int]):
    delete_terminology(session, id_list)


@router.get("/{id}/enable/{enabled}")
async def enable(session: SessionDep, id: int, enabled: bool, trans: Trans):
    enable_terminology(session, id, enabled, trans)


@router.get("/export")
async def export_excel(session: SessionDep, trans: Trans, current_user: CurrentUser,
                       word: Optional[str] = Query(None, description="搜索术语(可选)")):
    def inner():
        _list = get_all_terminology(session, word, oid=current_user.oid)

        data_list = []
        for obj in _list:
            _data = {
                "word": obj.word,
                "other_words": ', '.join(obj.other_words) if obj.other_words else '',
                "description": obj.description,
                "all_data_sources": 'Y' if obj.specific_ds else 'N',
                "datasource": ', '.join(obj.datasource_names) if obj.datasource_names else '',
            }
            data_list.append(_data)

        fields = []
        fields.append(AxisObj(name=trans('i18n_terminology.term_name'), value='word'))
        fields.append(AxisObj(name=trans('i18n_terminology.synonyms'), value='other_words'))
        fields.append(AxisObj(name=trans('i18n_terminology.term_description'), value='description'))
        fields.append(AxisObj(name=trans('i18n_terminology.effective_data_sources'), value='datasource'))
        fields.append(AxisObj(name=trans('i18n_terminology.all_data_sources'), value='all_data_sources'))

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
