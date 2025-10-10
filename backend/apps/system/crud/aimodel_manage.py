
from apps.system.models.system_model import AiModelDetail
from common.core.db import engine
from sqlmodel import Session, select
from common.utils.crypto import sqlbot_encrypt
from common.utils.utils import SQLBotLogUtil

async def async_model_info():
    with Session(engine) as session:
        model_list = session.exec(select(AiModelDetail)).all()
        any_model_change = False
        if model_list:
            for model in model_list:
                current_model_change = False
                if model.api_domain.startswith("http"):
                    if model.api_key:
                        model.api_key = await sqlbot_encrypt(model.api_key)
                    if model.api_domain:
                        model.api_domain = await sqlbot_encrypt(model.api_domain)
                    any_model_change = True
                    current_model_change = True
                if model.supplier and model.supplier == 12:
                    model.supplier = 15
                    any_model_change = True
                    current_model_change = True
                if current_model_change:
                    session.add(model)
        if any_model_change:
            session.commit()
            SQLBotLogUtil.info("✅ 异步加密已有模型的密钥和地址完成")           
            
            
        