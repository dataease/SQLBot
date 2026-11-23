import errno
import os
import stat
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO
from uuid import UUID, uuid4

from pandas import DataFrame
from pydantic import UUID4, BaseModel, ConfigDict


class ErrorReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: UUID4


@contextmanager
def _report_directory(root: str, *, create: bool = False):
    directory = Path(root) / "import-error-reports"
    if create:
        directory.mkdir(mode=0o700, exist_ok=True)
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        yield fd
    finally:
        os.close(fd)


def _storage_name(report_id: UUID, user_id: int, workspace_id: int) -> str:
    return f"{workspace_id:d}_{user_id:d}_{report_id.hex}.xlsx"


def save_error_report(
    root: str, data: DataFrame, user_id: int, workspace_id: int
) -> UUID:
    report_id = uuid4()
    name = _storage_name(report_id, user_id, workspace_id)
    with _report_directory(root, create=True) as directory:
        fd = os.open(
            name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=directory
        )
        try:
            with os.fdopen(fd, "wb") as output:
                data.to_excel(output, engine="xlsxwriter", index=False)
        except BaseException:
            os.unlink(name, dir_fd=directory)
            raise
    return report_id


def open_error_report(
    root: str, report_id: UUID, user_id: int, workspace_id: int
) -> BinaryIO:
    name = _storage_name(report_id, user_id, workspace_id)
    try:
        with _report_directory(root) as directory:
            fd = os.open(
                name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory
            )
    except OSError as exc:
        if exc.errno in (errno.ENOENT, errno.ENOTDIR, errno.ELOOP):
            raise FileNotFoundError from exc
        raise
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise FileNotFoundError
        return os.fdopen(fd, "rb")
    except BaseException:
        os.close(fd)
        raise
