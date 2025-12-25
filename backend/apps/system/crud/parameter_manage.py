from fastapi import Request
from sqlbot_xpack.config.arg_manage import get_group_args, save_group_args
# from sqlbot_xpack.config.model import SysArgModel
from sqlmodel import select, delete
import json
from common.core.deps import SessionDep
# from sqlbot_xpack.file_utils import SQLBotFileUtils
from apps.system.models.parameter_model import SysParameter, SysArgModel
from common.utils.local_file import LocalFileUtils

# 定义所有属于外观设置的图片 Key，确保它们能被正确处理
# 包含用户提到的 web, login, 以及常见的 navigate (导航栏Logo), favicon
IMAGE_KEYS = ["login", "navigate", "web", "favicon", "loginBg"]

# 定义外观相关的 Key 列表，用于强制分组
APPEARANCE_KEYS = [
                      "name", "slogan", "pc_welcome", "pc_welcome_desc",
                      "foot", "footContent", "help", "showSlogan", "showDoc", "showAbout", "bg"
                  ] + IMAGE_KEYS

# 1. 获取参数列表
async def get_groups(session: SessionDep, flag: str) -> list[SysArgModel]:
    # 从数据库查
    stmt = select(SysParameter).where(SysParameter.group_name == flag)
    db_params = session.exec(stmt).all()

    # 转换为前端需要的格式 (这里可以根据需求补全默认值，防止数据库为空时报错)
    result = []
    for p in db_params:
        result.append(SysArgModel(pkey=p.pkey, pval=p.pval))
    return result


# 2. 获取通用参数列表
async def get_parameter_args(session: SessionDep) -> list[SysArgModel]:
    stmt = select(SysParameter).where(SysParameter.group_name != "appearance")
    db_params = session.exec(stmt).all()
    return [SysArgModel(pkey=p.pkey, pval=p.pval) for p in db_params]


# 3. 保存参数
async def save_parameter_args(session: SessionDep, request: Request):
    form_data = await request.form()
    files = form_data.getlist("files")
    json_text = form_data.get("data")

    if not json_text:
        return
    sys_args_data = json.loads(json_text)

    for item in sys_args_data:
        key = item.get("pkey")
        val = item.get("pval")
        ptype = item.get("ptype")

        # --- 处理文件上传 ---
        if ptype == 'file':
            try:
                # 尝试匹配上传的文件
                if files:
                    target_file = None
                    for f in files:
                        if key in f.filename:
                            target_file = f
                            break
                    if not target_file and len(files) > 0:
                        target_file = files[0]

                    if target_file:
                        file_id = await LocalFileUtils.upload(target_file)
                        val = file_id
                        files.remove(target_file)
            except Exception:
                pass

        # Upsert 逻辑 (存在则更新，不存在则插入)
        db_obj = session.get(SysParameter, key)
        if not db_obj:
            # 【关键修复：正确分组】
            group = "system"
            if key.startswith("login."):
                group = "login"
            elif key.startswith("chat."):
                group = "chat"
            # 只要是定义的 Appearance Key，统统归类到 appearance
            elif key in APPEARANCE_KEYS:
                group = "appearance"

            db_obj = SysParameter(pkey=key, pval=val, group_name=group)
            session.add(db_obj)
        else:
            # 如果之前分组错了（比如变成了 system），这里强制修正回来
            if key in APPEARANCE_KEYS and db_obj.group_name != "appearance":
                db_obj.group_name = "appearance"

            if val is not None:
                db_obj.pval = val
            session.add(db_obj)

    session.commit()
