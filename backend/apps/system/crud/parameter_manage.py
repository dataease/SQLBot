from fastapi import Request
from sqlbot_xpack.config.arg_manage import get_group_args, save_group_args
from sqlbot_xpack.config.model import SysArgModel
import json
from common.core.deps import SessionDep
from sqlbot_xpack.file_utils import SQLBotFileUtils

async def get_parameter_args(session: SessionDep) -> list[SysArgModel]:
    group_args = await get_group_args(session=session)
    return [x for x in group_args if not x.pkey.startswith('appearance.')]

async def get_groups(session: SessionDep, flag: str) -> list[SysArgModel]:
    group_args = await get_group_args(session=session, flag=flag)
    return group_args

async def save_parameter_args(session: SessionDep, request: Request):
    allow_file_mapping = {
        """ "test_logo": { "types": [".jpg", ".jpeg", ".png", ".svg"], "size": 5 * 1024 * 1024 } """
    }
    form_data = await request.form()
    files = form_data.getlist("files")
    json_text = form_data.get("data")
    sys_args = [
        SysArgModel(**{**item, "pkey": f"{item['pkey']}"})
        for item in json.loads(json_text)
        if "pkey" in item
    ]
    if not sys_args:
        return
    file_mapping = None
    if files:
        file_mapping = {}
        for file in files:
            origin_file_name = file.filename
            file_name, flag_name = SQLBotFileUtils.split_filename_and_flag(origin_file_name)
            file.filename = file_name
            allow_limit_obj = allow_file_mapping.get(flag_name)
            if allow_limit_obj:
                SQLBotFileUtils.check_file(file=file, file_types=allow_limit_obj.get("types"), limit_file_size=allow_limit_obj.get("size"))
            else:
                raise Exception(f'The file [{file_name}] is not allowed to be uploaded!')
            file_id = await SQLBotFileUtils.upload(file)
            file_mapping[f"{flag_name}"] = file_id
    
    await save_group_args(session=session, sys_args=sys_args, file_mapping=file_mapping)