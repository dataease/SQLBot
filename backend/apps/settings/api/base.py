import os
from http.client import HTTPException

from fastapi import APIRouter
from fastapi.responses import FileResponse

from apps.swagger.i18n import PLACEHOLDER_PREFIX
from common.core.config import settings
from common.core.file import FileRequest

router = APIRouter(tags=["System"], prefix="/system")

path = settings.EXCEL_PATH


@router.post("/download-fail-info", summary=f"{PLACEHOLDER_PREFIX}download-fail-info")
async def download_excel(req: FileRequest):
    """
    根据文件路径下载 Excel 文件
    """
    filename = req.file
    file_path = os.path.join(path, filename)

    # 检查文件是否存在
    if not os.path.exists(file_path):
        raise HTTPException(404, "File Not Exists")

    # 检查文件是否是 Excel 文件
    if not filename.endswith('_error.xlsx'):
        raise HTTPException(400, "Only support _error.xlsx")

    # 获取文件名
    filename = os.path.basename(file_path)

    # 返回文件
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
