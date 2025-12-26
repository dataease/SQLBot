

import asyncio
from http.client import HTTPException
import io
import sys
import tempfile
import uuid
import atexit
import threading
from fastapi.responses import StreamingResponse, FileResponse
import os
from openai import BaseModel
import pandas as pd
from apps.system.models.user import UserModel
from common.core.deps import SessionDep


class RowValidator:
    def __init__(self, success: bool = False, row=list[str], error_info: dict = None):
        self.success = success
        self.row = row
        self.dict_data = {}
        self.error_info = error_info or {}
class CellValidator:
    def __init__(self, success: bool = False, value: str | int | list = None, message: str = ""):
        self.success = success
        self.value = value
        self.message = message
        
class UploadResultDTO(BaseModel):
    successCount: int
    errorCount: int
    dataKey: str | None = None
    

async def downTemplate(trans):
    def inner():
        data = {
            trans('i18n_user.account'): ['sqlbot1', 'sqlbot2'],
            trans('i18n_user.name'): ['sqlbot_employee1', 'sqlbot_employee2'],
            trans('i18n_user.email'): ['employee1@sqlbot.com', 'employee2@sqlbot.com'],
            trans('i18n_user.workspace'): [trans('i18n_default_workspace'), trans('i18n_default_workspace')],
            trans('i18n_user.role'): [trans('i18n_user.administrator'), trans('i18n_user.ordinary_member')],
            trans('i18n_user.status'): [trans('i18n_user.status_enabled'), trans('i18n_user.status_disabled')],
            trans('i18n_user.origin'): [trans('i18n_user.local_creation'), trans('i18n_user.local_creation')],
            trans('i18n_user.platform_user_id'): [None, None],
        }
        df = pd.DataFrame(data)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter', engine_kwargs={'options': {'strings_to_numbers': False}}) as writer:
            df.to_excel(writer, sheet_name='Sheet1', index=False)
            
            workbook = writer.book
            worksheet = writer.sheets['Sheet1']

            header_format = workbook.add_format({
                'bold': True,
                'font_size': 12,
                'font_name': '微软雅黑',
                'align': 'center',
                'valign': 'vcenter',
                'border': 0,
                'text_wrap': False,
            })
            
            for i, col in enumerate(df.columns):
                max_length = max(
                    len(str(col).encode('utf-8')) * 1.1,
                    (df[col].astype(str)).apply(len).max()
                )
                worksheet.set_column(i, i, max_length + 12)
                
                worksheet.write(0, i, col, header_format)
            
            
            worksheet.set_row(0, 30)
            for row in range(1, len(df) + 1):
                worksheet.set_row(row, 25)

        buffer.seek(0)
        return io.BytesIO(buffer.getvalue())

    result = await asyncio.to_thread(inner)
    return StreamingResponse(result, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

async def batchUpload(session: SessionDep, trans, file) -> UploadResultDTO:
    ALLOWED_EXTENSIONS = {"xlsx", "xls"}
    if not file.filename.lower().endswith(tuple(ALLOWED_EXTENSIONS)):
        raise HTTPException(400, "Only support .xlsx/.xls")
    
    # Support FastAPI UploadFile (async read) and file-like objects.
    NA_VALUES = ['', 'NA', 'N/A', 'NULL']
    df = None
    # If file provides an async read (UploadFile), read bytes first
    if hasattr(file, 'read') and asyncio.iscoroutinefunction(getattr(file, 'read')):
        content = await file.read()
        df = pd.read_excel(io.BytesIO(content), sheet_name=0, na_values=NA_VALUES)
    else:
        # If it's a Starlette UploadFile-like with a .file attribute, use that
        if hasattr(file, 'file'):
            fobj = file.file
            try:
                fobj.seek(0)
            except Exception:
                pass
            df = pd.read_excel(fobj, sheet_name=0, na_values=NA_VALUES)
        else:
            # fallback: assume a path or file-like object
            try:
                file.seek(0)
            except Exception:
                pass
            df = pd.read_excel(file, sheet_name=0, na_values=NA_VALUES)
    head_list = list(df.columns)
    i18n_head_list = get_i18n_head_list()
    if not validate_head(trans=trans, head_i18n_list=i18n_head_list, head_list=head_list):
        raise HTTPException(400, "Excel header validation failed")
    success_list = []
    error_list = []
    for row in df.itertuples():
        row_validator = validate_row(trans=trans, head_i18n_list=i18n_head_list, row=row)
        if row_validator.success:
            success_list.append(row_validator.dict_data)
        else:
            error_list.append(row_validator)
    error_file_id = None
    if error_list:
        error_file_id = generate_error_file(error_list, head_list)
    result = UploadResultDTO(successCount=len(success_list), errorCount=len(error_list), dataKey=error_file_id)
    if success_list:
        user_po_list = [UserModel.model_validate(row) for row in success_list]
        session.add_all(user_po_list)
        session.commit()
    return result    

def get_i18n_head_list():
    return [
        'i18n_user.account',
        'i18n_user.name',
        'i18n_user.email',
        'i18n_user.workspace',
        'i18n_user.role',
        'i18n_user.status',
        'i18n_user.origin',
        'i18n_user.platform_user_id',
    ]

def validate_head(trans, head_i18n_list: list[str], head_list: list):
    if len(head_list) != len(head_i18n_list):
        return False
    for i in range(len(head_i18n_list)):
        if head_list[i] != trans(head_i18n_list[i]):
            return False
    return True



def validate_row(trans, head_i18n_list: list[str], row):
    validator = RowValidator(success=True, row=[], error_info={})
    for i in range(len(head_i18n_list)):
        col_name = trans(head_i18n_list[i])
        row_value = getattr(row, col_name)
        validator.row.append(row_value)
        _attr_name = f"{head_i18n_list[i].split('.')[-1]}"
        _method_name = f"validate_{_attr_name}"
        cellValidator = dynamic_call(_method_name, row_value)
        if not cellValidator.success:
            validator.success = False
            validator.error_info[i] = cellValidator.message
        else:
            validator.dict_data[_attr_name] = cellValidator.value
    return validator

def generate_error_file(error_list: list[RowValidator], head_list: list[str]) -> str:
    # If no errors, return empty string
    if not error_list:
        return ""

    # Build DataFrame from error rows (only include rows that had errors)
    df_rows = [err.row for err in error_list]
    df = pd.DataFrame(df_rows, columns=head_list)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    tmp_name = tmp.name
    tmp.close()

    with pd.ExcelWriter(tmp_name, engine='xlsxwriter', engine_kwargs={'options': {'strings_to_numbers': False}}) as writer:
        df.to_excel(writer, sheet_name='Errors', index=False)

        workbook = writer.book
        worksheet = writer.sheets['Errors']

        # header format similar to downTemplate
        header_format = workbook.add_format({
            'bold': True,
            'font_size': 12,
            'font_name': '微软雅黑',
            'align': 'center',
            'valign': 'vcenter',
            'border': 0,
            'text_wrap': False,
        })

        # apply header format and column widths
        for i, col in enumerate(df.columns):
            max_length = max(
                len(str(col).encode('utf-8')) * 1.1,
                (df[col].astype(str)).apply(len).max() if len(df) > 0 else 0
            )
            worksheet.set_column(i, i, max_length + 12)
            worksheet.write(0, i, col, header_format)

        worksheet.set_row(0, 30)
        for row_idx in range(1, len(df) + 1):
            worksheet.set_row(row_idx, 25)

        red_format = workbook.add_format({'font_color': 'red'})

        # Add comments and set red font for each erroneous cell.
        # Note: pandas wrote header at row 0, data starts from row 1 in the sheet.
        for sheet_row_idx, err in enumerate(error_list, start=1):
            for col_idx, message in err.error_info.items():
                if message:
                    comment_text = str(message)
                    worksheet.write_comment(sheet_row_idx, col_idx, comment_text)
                    try:
                        cell_value = df.iat[sheet_row_idx - 1, col_idx]
                    except Exception:
                        cell_value = None
                    worksheet.write(sheet_row_idx, col_idx, cell_value, red_format)

    # register temp file in map and return an opaque file id
    file_id = uuid.uuid4().hex
    with _TEMP_FILE_LOCK:
        _TEMP_FILE_MAP[file_id] = tmp_name

    return file_id


def download_error_file(file_id: str) -> FileResponse:
    """Return a FileResponse for the given generated file id.

    Look up the actual temp path from the internal map. Only files
    created by `generate_error_file` are allowed.
    """
    if not file_id:
        raise HTTPException(400, "file_id required")

    with _TEMP_FILE_LOCK:
        file_path = _TEMP_FILE_MAP.get(file_id)

    if not file_path:
        raise HTTPException(404, "File not found")

    # ensure file is inside tempdir
    tempdir = tempfile.gettempdir()
    try:
        common = os.path.commonpath([tempdir, os.path.abspath(file_path)])
    except Exception:
        raise HTTPException(403, "Unauthorized file access")

    if os.path.abspath(common) != os.path.abspath(tempdir):
        raise HTTPException(403, "Unauthorized file access")

    if not os.path.exists(file_path):
        raise HTTPException(404, "File not found")

    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=os.path.basename(file_path),
    )

def validate_account(value: str) -> CellValidator:
    return CellValidator(True, value, None)
def validate_name(value: str) -> CellValidator:
    return CellValidator(True, value, None)  
def validate_email(value: str) -> CellValidator:
    return CellValidator(True, value, None)
def validate_workspace(value: str) -> CellValidator:
    return CellValidator(True, value, None)
def validate_role(value: str) -> CellValidator:
    return CellValidator(True, value, None)
def validate_status(value: str) -> CellValidator:
    if value == '已启用': return CellValidator(True, 1, None)
    if value == '已禁用': return CellValidator(True, 0, None)
    return CellValidator(False, None, "状态只能是已启用或已禁用")
def validate_origin(value: str) -> CellValidator:
    if value == '本地创建': return CellValidator(True, 0, None)
    return CellValidator(False, None, "不支持当前来源")
def validate_platform_id(value: str) -> CellValidator:
    return CellValidator(True, value, None)

_method_cache = {
    'validate_account': validate_account,
    'validate_name': validate_name,
    'validate_email': validate_email,
    'validate_workspace': validate_workspace,
    'validate_role': validate_role,
    'validate_status': validate_status,
    'validate_origin': validate_origin,
    'validate_platform_user_id': validate_platform_id,   
}
_module = sys.modules[__name__]
def dynamic_call(method_name: str, *args, **kwargs):
    if method_name in _method_cache:
        return _method_cache[method_name](*args, **kwargs)
    
    if hasattr(_module, method_name):
        func = getattr(_module, method_name)
        _method_cache[method_name] = func
        return func(*args, **kwargs)
    
    raise AttributeError(f"Function '{method_name}' not found")


# Map of file_id -> temp path for generated error files
_TEMP_FILE_MAP: dict[str, str] = {}
_TEMP_FILE_LOCK = threading.Lock()


def _cleanup_temp_files():
    with _TEMP_FILE_LOCK:
        for fid, path in list(_TEMP_FILE_MAP.items()):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass
        _TEMP_FILE_MAP.clear()


atexit.register(_cleanup_temp_files)
    



    
   