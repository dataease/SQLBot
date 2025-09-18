import json
import urllib
from typing import Optional

import requests
from fastapi import FastAPI
from sqlalchemy import Engine, create_engine
from sqlmodel import Session, select
from starlette.middleware.cors import CORSMiddleware

from apps.datasource.models.datasource import CoreDatasource, DatasourceConf
from apps.system.models.system_model import AssistantModel
from apps.system.schemas.auth import CacheName, CacheNamespace
from apps.system.schemas.system_schema import AssistantHeader, AssistantOutDsSchema, UserInfoDTO
from common.core.config import settings
from common.core.db import engine
from common.core.sqlbot_cache import cache
from common.utils.aes_crypto import simple_aes_decrypt
from common.utils.utils import string_to_numeric_hash

@cache(namespace=CacheNamespace.EMBEDDED_INFO, cacheName=CacheName.ASSISTANT_INFO, keyExpression="assistant_id")
async def get_assistant_info(*, session: Session, assistant_id: int) -> AssistantModel | None:
    db_model = session.get(AssistantModel, assistant_id)
    return db_model


def get_assistant_user(*, id: int):
    return UserInfoDTO(id=id, account="sqlbot-inner-assistant", oid=1, name="sqlbot-inner-assistant",
                       email="sqlbot-inner-assistant@sqlbot.com")


def get_assistant_ds(session: Session, llm_service) -> list[dict]:
    assistant: AssistantHeader = llm_service.current_assistant
    type = assistant.type
    if type == 0 or type == 2:
        configuration = assistant.configuration
        if configuration:
            config: dict[any] = json.loads(configuration)
            oid: int = int(config['oid'])
            stmt = select(CoreDatasource.id, CoreDatasource.name, CoreDatasource.description).where(
                CoreDatasource.oid == oid)
            if not assistant.online:
                public_list: list[int] = config.get('public_list') or None
                if public_list:
                    stmt = stmt.where(CoreDatasource.id.in_(public_list))
                else:
                    return []
                """ private_list: list[int] = config.get('private_list') or None
                if private_list:
                    stmt = stmt.where(~CoreDatasource.id.in_(private_list)) """
        db_ds_list = session.exec(stmt)

        result_list = [
            {
                "id": ds.id,
                "name": ds.name,
                "description": ds.description
            }
            for ds in db_ds_list
        ]

        # filter private ds if offline
        return result_list
    out_ds_instance: AssistantOutDs = AssistantOutDsFactory.get_instance(assistant)
    llm_service.out_ds_instance = out_ds_instance
    dslist = out_ds_instance.get_simple_ds_list()
    # format?
    return dslist


def init_dynamic_cors(app: FastAPI):
    try:
        with Session(engine) as session:
            list_result = session.exec(select(AssistantModel).order_by(AssistantModel.create_time)).all()
            seen = set()
            unique_domains = []
            for item in list_result:
                if item.domain:
                    for domain in item.domain.split(','):
                        domain = domain.strip()
                        if domain and domain not in seen:
                            seen.add(domain)
                            unique_domains.append(domain)
            cors_middleware = None
            for middleware in app.user_middleware:
                if middleware.cls == CORSMiddleware:
                    cors_middleware = middleware
                    break
            if cors_middleware:
                updated_origins = list(set(settings.all_cors_origins + unique_domains))
                cors_middleware.kwargs['allow_origins'] = updated_origins
    except Exception as e:
        return False, e


class AssistantOutDs:
    assistant: AssistantHeader
    ds_list: Optional[list[AssistantOutDsSchema]] = None
    certificate: Optional[str] = None

    def __init__(self, assistant: AssistantHeader):
        self.assistant = assistant
        self.ds_list = None
        self.certificate = assistant.certificate
        self.get_ds_from_api()

    # @cache(namespace=CacheNamespace.EMBEDDED_INFO, cacheName=CacheName.ASSISTANT_DS, keyExpression="current_user.id")
    def get_ds_from_api(self):
        config: dict[any] = json.loads(self.assistant.configuration)
        endpoint: str = config['endpoint']
        certificateList: list[any] = json.loads(self.certificate)
        header = {}
        cookies = {}
        param = {}
        for item in certificateList:
            if item['target'] == 'header':
                header[item['key']] = item['value']
            if item['target'] == 'cookie':
                cookies[item['key']] = item['value']
            if item['target'] == 'param':
                param[item['key']] = item['value']
        res = requests.get(url=endpoint, params=param, headers=header, cookies=cookies, timeout=10)
        if res.status_code == 200:
            result_json: dict[any] = json.loads(res.text)
            if result_json.get('code') == 0 or result_json.get('code') == 200:
                temp_list = result_json.get('data', [])
                temp_ds_list = [
                    self.convert2schema(item, config)
                    for item in temp_list
                ]
                self.ds_list = temp_ds_list
                return self.ds_list
            else:
                raise Exception(f"Failed to get datasource list from {endpoint}, error: {result_json.get('message')}")
        else:
            raise Exception(f"Failed to get datasource list from {endpoint}, status code: {res.status_code}")

    def get_simple_ds_list(self):
        if self.ds_list:
            return [{'id': ds.id, 'name': ds.name, 'description': ds.comment} for ds in self.ds_list]
        else:
            raise Exception("Datasource list is not found.")

    def get_db_schema(self, ds_id: int) -> str:
        ds = self.get_ds(ds_id)
        schema_str = ""
        db_name = ds.db_schema if ds.db_schema is not None and ds.db_schema != "" else ds.dataBase
        schema_str += f"【DB_ID】 {db_name}\n【Schema】\n"
        for table in ds.tables:
            schema_str += f"# Table: {db_name}.{table.name}" if ds.type != "mysql" else f"# Table: {table.name}"
            table_comment = table.comment
            if table_comment == '':
                schema_str += '\n[\n'
            else:
                schema_str += f", {table_comment}\n[\n"

            field_list = []
            for field in table.fields:
                field_comment = field.comment
                if field_comment == '':
                    field_list.append(f"({field.name}:{field.type})")
                else:
                    field_list.append(f"({field.name}:{field.type}, {field_comment})")
            schema_str += ",\n".join(field_list)
            schema_str += '\n]\n'
        return schema_str

    def get_ds(self, ds_id: int):
        if self.ds_list:
            for ds in self.ds_list:
                if ds.id == ds_id:
                    return ds
        else:
            raise Exception("Datasource list is not found.")
        raise Exception(f"Datasource with id {ds_id} not found.")

    def convert2schema(self, ds_dict: dict, config: dict[any]) -> AssistantOutDsSchema:
        id_marker: str = ''
        attr_list = ['name', 'type', 'host', 'port', 'user', 'dataBase', 'schema']
        if config.get('encrypt', False):
            key = config.get('aes_key', None)
            iv = config.get('aes_iv', None)
            aes_attrs = ['host', 'user', 'password', 'dataBase', 'db_schema', 'schema']
            for attr in aes_attrs:
                if attr in ds_dict and ds_dict[attr]:
                    try:
                        ds_dict[attr] = simple_aes_decrypt(ds_dict[attr], key, iv)
                    except Exception as e:
                        raise Exception(f"Failed to encrypt {attr} for datasource {ds_dict.get('name')}, error: {str(e)}")
        for attr in attr_list:
            if attr in ds_dict:
                id_marker += str(ds_dict.get(attr, '')) + '--sqlbot--'
        id = string_to_numeric_hash(id_marker)
        db_schema = ds_dict.get('schema', ds_dict.get('db_schema', ''))
        ds_dict.pop("schema", None)
        return AssistantOutDsSchema(**{**ds_dict, "id": id, "db_schema": db_schema})

class AssistantOutDsFactory:
    @staticmethod
    def get_instance(assistant: AssistantHeader) -> AssistantOutDs:
        return AssistantOutDs(assistant)


def get_ds_engine(ds: AssistantOutDsSchema) -> Engine:
    timeout: int = 30
    connect_args = {"connect_timeout": timeout}
    conf = DatasourceConf(
        host=ds.host,
        port=ds.port,
        username=ds.user,
        password=ds.password,
        database=ds.dataBase,
        driver='',
        extraJdbc=ds.extraParams or '',
        dbSchema=ds.db_schema or ''
    )
    conf.extraJdbc = ''
    from apps.db.db import get_uri_from_config
    uri = get_uri_from_config(ds.type, conf)
    # if ds.type == "pg" and ds.db_schema:
    #     connect_args.update({"options": f"-c search_path={ds.db_schema}"})
    # engine = create_engine(uri, connect_args=connect_args, pool_timeout=timeout, pool_size=20, max_overflow=10)

    if ds.type == "pg" and ds.db_schema:
        engine = create_engine(uri,
                               connect_args={"options": f"-c search_path={urllib.parse.quote(ds.db_schema)}",
                                             "connect_timeout": timeout},
                               pool_timeout=timeout)
    elif ds.type == 'sqlServer':
        engine = create_engine(uri, pool_timeout=timeout)
    elif ds.type == 'oracle':
        engine = create_engine(uri,
                               pool_timeout=timeout)
    else:
        engine = create_engine(uri, connect_args={"connect_timeout": timeout}, pool_timeout=timeout)
    return engine
