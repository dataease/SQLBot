

import asyncio
from http.client import HTTPException
import io
from fastapi.responses import StreamingResponse
import pandas as pd


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

async def batchUpload(trans, file):
    ALLOWED_EXTENSIONS = {"xlsx", "xls"}
    if not file.filename.lower().endswith(tuple(ALLOWED_EXTENSIONS)):
        raise HTTPException(400, "Only support .xlsx/.xls")
    pass