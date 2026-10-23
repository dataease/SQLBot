import asyncio
import json

from fastapi import Request
from sqlalchemy import text
from sqlbot_xpack.config.arg_manage import get_group_args, save_group_args
from sqlbot_xpack.config.model import SysArgModel
from sqlbot_xpack.file_utils import SQLBotFileUtils

from common.core.deps import SessionDep
from common.core.embedding_config import (
    EDITABLE_FIELDS,
    effective_parameter_args,
    load_embedding_config,
    parse_parameter,
)
from common.error import SingleMessageError
from common.utils.locale import I18n

# Fixed bigint advisory-lock key for all parameter writers. Resource generation
# keys instead hash the sqlbot:embedding:<resource>:<id> namespace.
PARAMETER_SAVE_LOCK_KEY = 14030001


async def get_parameter_args(session: SessionDep) -> list[SysArgModel]:
    group_args = await get_group_args(session=session)
    return [
        x for x in group_args if not x.pkey.startswith(("appearance.", "embedding."))
    ] + effective_parameter_args(session)


async def get_groups(session: SessionDep, flag: str) -> list[SysArgModel]:
    group_args = await get_group_args(session=session, flag=flag)
    return group_args


async def save_parameter_args(session: SessionDep, request: Request):
    allow_file_mapping = {
        """ "test_logo": { "types": [".jpg", ".jpeg", ".png"], "size": 5 * 1024 * 1024 } """
    }
    form_data = await request.form()
    files = form_data.getlist("files")
    json_text = form_data.get("data")
    # xpack commits internally: validate the complete batch before passing any values.
    try:
        items = json.loads(json_text)
    except (TypeError, json.JSONDecodeError):
        raise SingleMessageError(
            I18n()(request)("i18n_parameter.invalid_embedding_parameter", key="data")
        )
    if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
        raise SingleMessageError(
            I18n()(request)("i18n_parameter.invalid_embedding_parameter", key="data")
        )
    sys_args = []
    seen = set()
    for item in items:
        key = item.get("pkey")
        if not isinstance(key, str) or not key:
            raise SingleMessageError(
                I18n()(request)(
                    "i18n_parameter.invalid_embedding_parameter", key="pkey"
                )
            )
        if key.startswith("embedding."):
            field = key.removeprefix("embedding.")
            try:
                if field not in EDITABLE_FIELDS or key in seen:
                    raise ValueError(key)
                value = parse_parameter(field, item.get("pval"))
            except (ValueError, TypeError, OverflowError):
                raise SingleMessageError(
                    I18n()(request)(
                        "i18n_parameter.invalid_embedding_parameter", key=key
                    )
                )
            item = {**item, "pval": str(value).lower()}
        else:
            item = {
                **item,
                "pval": str(item.get("pval", "")).lower()
                if isinstance(item.get("pval"), bool)
                else str(item.get("pval", "")),
            }
        seen.add(key)
        sys_args.append(SysArgModel(**item))
    if not sys_args:
        return
    file_mapping = None
    if files:
        file_mapping = {}
        for file in files:
            origin_file_name = file.filename
            file_name, flag_name = SQLBotFileUtils.split_filename_and_flag(
                origin_file_name
            )
            file.filename = file_name
            allow_limit_obj = allow_file_mapping.get(flag_name)
            if allow_limit_obj:
                SQLBotFileUtils.check_file(
                    file=file,
                    file_types=allow_limit_obj.get("types"),
                    limit_file_size=allow_limit_obj.get("size"),
                )
            else:
                raise Exception(
                    f"The file [{file_name}] is not allowed to be uploaded!"
                )
            file_id = await SQLBotFileUtils.upload(file)
            file_mapping[f"{flag_name}"] = file_id

    # Legacy migrations do not enforce unique pkey. Serialize first-time writes
    # across workers before the adapter reads existing keys and commits. A try
    # lock lets other requests run while waiting. Keep the async adapter on its
    # original loop so configured cache clients retain their loop affinity.
    if session.get_bind().dialect.name == "postgresql":
        while not session.execute(
            text("SELECT pg_try_advisory_xact_lock(:key)"),
            {"key": PARAMETER_SAVE_LOCK_KEY},
        ).scalar_one():
            await asyncio.sleep(0.05)
    previous = load_embedding_config(session)
    result = await save_group_args(
        session=session, sys_args=sys_args, file_mapping=file_mapping
    )
    current = load_embedding_config(session)
    if not previous.enabled and current.enabled:
        from common.utils.embedding_threads import (
            fill_empty_data_training_embeddings,
            fill_empty_terminology_embeddings,
        )

        fill_empty_terminology_embeddings()
        fill_empty_data_training_embeddings()
    if not previous.table_enabled and current.table_enabled:
        from common.utils.embedding_threads import fill_empty_table_and_ds_embeddings

        fill_empty_table_and_ds_embeddings()
    return result
