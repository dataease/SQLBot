import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from apps.swagger.i18n import PLACEHOLDER_PREFIX
from common.core.config import settings
from common.core.file import FileRequest
from common.utils.utils import safe_upload_name

router = APIRouter(tags=["System"], prefix="/system")

path = settings.EXCEL_PATH


@router.post("/download-fail-info", summary=f"{PLACEHOLDER_PREFIX}download-fail-info")
async def download_excel(req: FileRequest):
    """
    根据文件路径下载 Excel 文件
    """
    # 该文件名由导出接口生成，是单个文件名：带目录分量、盘符或控制字符的取值
    # 一律拒绝，不做静默改写；校验先于文件系统访问，避免用拒绝结果反推任意路径
    # 是否存在。
    raw_name = (req.file or "").strip()
    file_name = safe_upload_name(req.file)
    if not file_name or file_name != raw_name or not file_name.endswith("_error.xlsx"):
        raise HTTPException(400, "Only support _error.xlsx")

    base_dir = os.path.realpath(path)
    try:
        file_path = os.path.realpath(os.path.join(base_dir, file_name))
        inside = os.path.commonpath([file_path, base_dir]) == base_dir
    except ValueError:  # 含 NUL、跨盘符或非法路径
        inside = False
        file_path = ""

    # 检查文件是否位于上传目录内且确实是文件（符号链接由 realpath 一并解析）
    if not inside or file_path == base_dir or not os.path.isfile(file_path):
        raise HTTPException(404, "File Not Exists")

    # 获取文件名
    file_name = os.path.basename(file_path)

    # 返回文件
    return FileResponse(
        path=file_path,
        filename=file_name,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
