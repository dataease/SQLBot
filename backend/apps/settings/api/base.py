from functools import partial

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from apps.swagger.i18n import PLACEHOLDER_PREFIX
from common.core.config import settings
from common.core.deps import CurrentUser
from common.core.file import ErrorReportRequest, open_error_report

router = APIRouter(tags=["System"], prefix="/system")

path = settings.EXCEL_PATH


@router.post("/download-fail-info", summary=f"{PLACEHOLDER_PREFIX}download-fail-info")
def download_excel(req: ErrorReportRequest, current_user: CurrentUser):
    try:
        report = open_error_report(
            path, req.report_id, current_user.id, current_user.oid
        )
    except FileNotFoundError:
        raise HTTPException(404, "File Not Exists") from None

    return StreamingResponse(
        iter(partial(report.read, 64 * 1024), b""),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{req.report_id}_error.xlsx"'
        },
        background=BackgroundTask(report.close),
    )
