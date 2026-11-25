"""The user import must accept its own template in every supported language."""

import asyncio
import io
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest

from apps.system.crud import user_excel
from common.utils.locale import I18n

I18N = I18n(Path(__file__).resolve().parents[1] / "locales")


def template(trans) -> pd.DataFrame:
    async def download():
        response = await user_excel.downTemplate(trans)
        return b"".join([chunk async for chunk in response.body_iterator])

    return pd.read_excel(io.BytesIO(asyncio.run(download())))


def upload(trans, frame: pd.DataFrame):
    buffer = io.BytesIO()
    frame.to_excel(buffer, index=False)
    buffer.seek(0)
    buffer.filename = "users.xlsx"
    session = Mock()
    result = asyncio.run(user_excel.batchUpload(session, trans, buffer))
    return result, session


@pytest.mark.parametrize("lang", sorted(I18N.translations))
def test_downloaded_template_can_be_imported(lang):
    trans = I18N(lang=lang)

    result, session = upload(trans, template(trans))

    assert (result.successCount, result.errorCount) == (2, 0)
    users = session.add_all.call_args.args[0]
    assert [(u.account, u.status, u.origin) for u in users] == [
        ("sqlbot1", 1, 0),
        ("sqlbot2", 0, 0),
    ]


def test_unknown_status_is_reported_per_row():
    trans = I18N(lang="en")
    frame = template(trans)
    frame[trans("i18n_user.status")] = ["Unknown", trans("i18n_user.status_enabled")]

    result, _ = upload(trans, frame)

    assert (result.successCount, result.errorCount) == (1, 1)
    user_excel.download_error_file(result.dataKey)
