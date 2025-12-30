import asyncio
import hashlib
import io
import os
import uuid
from http.client import HTTPException
from typing import Optional

import pandas as pd
from fastapi import APIRouter, File, UploadFile, Query
from fastapi.responses import StreamingResponse

from apps.chat.models.chat_model import AxisObj
from apps.swagger.i18n import PLACEHOLDER_PREFIX
from apps.system.schemas.permission import SqlbotPermission, require_permissions
from apps.terminology.curd.terminology import page_terminology, create_terminology, update_terminology, \
    delete_terminology, enable_terminology, get_all_terminology, batch_create_terminology
from apps.terminology.models.terminology_model import TerminologyInfo
from common.core.config import settings
from common.core.deps import SessionDep, CurrentUser, Trans
from common.utils.data_format import DataFormat
from common.utils.excel import get_excel_column_count
from common.audit.models.log_model import OperationType, OperationModules
from common.audit.schemas.logger_decorator import LogConfig, system_log
router = APIRouter(tags=["Terminology"], prefix="/system/terminology")


@router.get("/page/{current_page}/{page_size}", summary=f"{PLACEHOLDER_PREFIX}get_term_page")
async def pager(session: SessionDep, current_user: CurrentUser, current_page: int, page_size: int,
                word: Optional[str] = Query(None, description="搜索术语(可选)"),
                dslist: Optional[list[int]] = Query(None, description="数据集ID集合(可选)")):
    current_page, page_size, total_count, total_pages, _list = page_terminology(session, current_page, page_size, word,
                                                                                current_user.oid, dslist)

    return {
        "current_page": current_page,
        "page_size": page_size,
        "total_count": total_count,
        "total_pages": total_pages,
        "data": _list
    }


@router.put("", summary=f"{PLACEHOLDER_PREFIX}create_or_update_term")
@system_log(LogConfig(operation_type=OperationType.CREATE_OR_UPDATE, module=OperationModules.TERMINOLOGY,resource_id_expr='info.id', result_id_expr="result_self"))
async def create_or_update(session: SessionDep, current_user: CurrentUser, trans: Trans, info: TerminologyInfo):
    oid = current_user.oid
    if info.id:
        return update_terminology(session, info, oid, trans)
    else:
        return create_terminology(session, info, oid, trans)


@router.delete("", summary=f"{PLACEHOLDER_PREFIX}delete_term")
@system_log(LogConfig(operation_type=OperationType.DELETE, module=OperationModules.TERMINOLOGY,resource_id_expr='id_list'))
@require_permissions(permission=SqlbotPermission(role=['ws_admin']))
async def delete(session: SessionDep, id_list: list[int]):
    delete_terminology(session, id_list)


@router.get("/{id}/enable/{enabled}", summary=f"{PLACEHOLDER_PREFIX}enable_term")
@system_log(LogConfig(operation_type=OperationType.UPDATE, module=OperationModules.TERMINOLOGY,resource_id_expr='id'))
@require_permissions(permission=SqlbotPermission(role=['ws_admin']))
async def enable(session: SessionDep, id: int, enabled: bool, trans: Trans):
    enable_terminology(session, id, enabled, trans)


@router.get("/export", summary=f"{PLACEHOLDER_PREFIX}export_term")
@system_log(LogConfig(operation_type=OperationType.EXPORT, module=OperationModules.TERMINOLOGY))
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
                "all_data_sources": 'N' if obj.specific_ds else 'Y',
                "datasource": ', '.join(obj.datasource_names) if obj.datasource_names and obj.specific_ds else '',
            }
            data_list.append(_data)

        fields = []
        fields.append(AxisObj(name=trans('i18n_terminology.term_name'), value='word'))
        fields.append(AxisObj(name=trans('i18n_terminology.synonyms'), value='other_words'))
        fields.append(AxisObj(name=trans('i18n_terminology.term_description'), value='description'))
        fields.append(AxisObj(name=trans('i18n_terminology.effective_data_sources'), value='datasource'))
        fields.append(AxisObj(name=trans('i18n_terminology.all_data_sources'), value='all_data_sources'))

        md_data, _fields_list = DataFormat.convert_object_array_for_pandas(fields, data_list)

        df = pd.DataFrame(md_data, columns=_fields_list)

        buffer = io.BytesIO()

        with pd.ExcelWriter(buffer, engine='xlsxwriter',
                            engine_kwargs={'options': {'strings_to_numbers': False}}) as writer:
            df.to_excel(writer, sheet_name='Sheet1', index=False)

        buffer.seek(0)
        return io.BytesIO(buffer.getvalue())

    result = await asyncio.to_thread(inner)
    return StreamingResponse(result, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@router.get("/template", summary=f"{PLACEHOLDER_PREFIX}excel_template_term")
async def excel_template(trans: Trans):
    def inner():
        data_list = []
        _data1 = {
            "word": trans('i18n_terminology.term_name_template_example_1'),
            "other_words": trans('i18n_terminology.synonyms_template_example_1'),
            "description": trans('i18n_terminology.term_description_template_example_1'),
            "all_data_sources": 'N',
            "datasource": trans('i18n_terminology.effective_data_sources_template_example_1'),
        }
        data_list.append(_data1)
        _data2 = {
            "word": trans('i18n_terminology.term_name_template_example_2'),
            "other_words": trans('i18n_terminology.synonyms_template_example_2'),
            "description": trans('i18n_terminology.term_description_template_example_2'),
            "all_data_sources": 'Y',
            "datasource": '',
        }
        data_list.append(_data2)

        fields = []
        fields.append(AxisObj(name=trans('i18n_terminology.term_name_template'), value='word'))
        fields.append(AxisObj(name=trans('i18n_terminology.synonyms_template'), value='other_words'))
        fields.append(AxisObj(name=trans('i18n_terminology.term_description_template'), value='description'))
        fields.append(AxisObj(name=trans('i18n_terminology.effective_data_sources_template'), value='datasource'))
        fields.append(AxisObj(name=trans('i18n_terminology.all_data_sources_template'), value='all_data_sources'))

        md_data, _fields_list = DataFormat.convert_object_array_for_pandas(fields, data_list)

        df = pd.DataFrame(md_data, columns=_fields_list)

        buffer = io.BytesIO()

        with pd.ExcelWriter(buffer, engine='xlsxwriter',
                            engine_kwargs={'options': {'strings_to_numbers': False}}) as writer:
            df.to_excel(writer, sheet_name='Sheet1', index=False)

        buffer.seek(0)
        return io.BytesIO(buffer.getvalue())

    result = await asyncio.to_thread(inner)
    return StreamingResponse(result, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


path = settings.EXCEL_PATH

from sqlalchemy.orm import sessionmaker, scoped_session
from common.core.db import engine
from sqlmodel import Session

session_maker = scoped_session(sessionmaker(bind=engine, class_=Session))


@router.post("/uploadExcel", summary=f"{PLACEHOLDER_PREFIX}upload_term")
@system_log(LogConfig(operation_type=OperationType.IMPORT, module=OperationModules.TERMINOLOGY))
async def upload_excel(trans: Trans, current_user: CurrentUser, file: UploadFile = File(...)):
    ALLOWED_EXTENSIONS = {"xlsx", "xls"}
    if not file.filename.lower().endswith(tuple(ALLOWED_EXTENSIONS)):
        raise HTTPException(400, "Only support .xlsx/.xls")

    os.makedirs(path, exist_ok=True)
    base_filename = f"{file.filename.split('.')[0]}_{hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:10]}"
    filename = f"{base_filename}.{file.filename.split('.')[1]}"
    save_path = os.path.join(path, filename)
    with open(save_path, "wb") as f:
        f.write(await file.read())

    oid = current_user.oid

    use_cols = [0, 1, 2, 3, 4]

    def inner():

        session = session_maker()

        sheet_names = pd.ExcelFile(save_path).sheet_names

        import_data = []

        for sheet_name in sheet_names:

            if get_excel_column_count(save_path, sheet_name) < len(use_cols):
                raise Exception(trans("i18n_excel_import.col_num_not_match"))

            df = pd.read_excel(
                save_path,
                sheet_name=sheet_name,
                engine='calamine',
                header=0,
                usecols=use_cols,
                dtype=str
            ).fillna("")

            for index, row in df.iterrows():
                # 跳过空行
                if row.isnull().all():
                    continue

                word = row[0].strip() if pd.notna(row[0]) and row[0].strip() else ''
                other_words = [w.strip() for w in row[1].strip().split(',')] if pd.notna(row[1]) and row[
                    1].strip() else []
                description = row[2].strip() if pd.notna(row[2]) and row[2].strip() else ''
                datasource_names = [d.strip() for d in row[3].strip().split(',')] if pd.notna(row[3]) and row[
                    3].strip() else []
                all_datasource = True if pd.notna(row[4]) and row[4].lower().strip() in ['y', 'yes', 'true'] else False
                specific_ds = False if all_datasource else True

                import_data.append(TerminologyInfo(word=word, description=description, other_words=other_words,
                                                   datasource_names=datasource_names, specific_ds=specific_ds))

        res = batch_create_terminology(session, import_data, oid, trans)

        failed_records = res['failed_records']

        error_excel_filename = None

        if len(failed_records) > 0:
            data_list = []
            for obj in failed_records:
                _data = {
                    "word": obj['data'].word,
                    "other_words": ', '.join(obj['data'].other_words) if obj['data'].other_words else '',
                    "description": obj['data'].description,
                    "all_data_sources": 'N' if obj['data'].specific_ds else 'Y',
                    "datasource": ', '.join(obj['data'].datasource_names) if obj['data'].datasource_names and obj[
                        'data'].specific_ds else '',
                    "errors": obj['errors']
                }
                data_list.append(_data)

            fields = []
            fields.append(AxisObj(name=trans('i18n_terminology.term_name'), value='word'))
            fields.append(AxisObj(name=trans('i18n_terminology.synonyms'), value='other_words'))
            fields.append(AxisObj(name=trans('i18n_terminology.term_description'), value='description'))
            fields.append(AxisObj(name=trans('i18n_terminology.effective_data_sources'), value='datasource'))
            fields.append(AxisObj(name=trans('i18n_terminology.all_data_sources'), value='all_data_sources'))
            fields.append(AxisObj(name=trans('i18n_data_training.error_info'), value='errors'))

            md_data, _fields_list = DataFormat.convert_object_array_for_pandas(fields, data_list)

            df = pd.DataFrame(md_data, columns=_fields_list)
            error_excel_filename = f"{base_filename}_error.xlsx"
            save_error_path = os.path.join(path, error_excel_filename)
            # 保存 DataFrame 到 Excel
            df.to_excel(save_error_path, index=False)

        return {
            'success_count': res['success_count'],
            'failed_count': len(failed_records),
            'duplicate_count': res['duplicate_count'],
            'original_count': res['original_count'],
            'error_excel_filename': error_excel_filename,
        }

    return await asyncio.to_thread(inner)
