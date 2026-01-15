import json
import re
import urllib
from typing import Optional

import requests
from fastapi import FastAPI
from sqlalchemy import Engine, create_engine
from sqlmodel import Session, select
from starlette.middleware.cors import CORSMiddleware

# from apps.datasource.embedding.table_embedding import get_table_embedding
from apps.datasource.models.datasource import CoreDatasource, DatasourceConf
from apps.datasource.utils.utils import aes_encrypt
from apps.system.models.system_model import AssistantModel
from apps.system.schemas.auth import CacheName, CacheNamespace
from apps.system.schemas.system_schema import AssistantHeader, AssistantOutDsSchema, UserInfoDTO
from common.core.config import settings
from common.core.db import engine
from common.core.sqlbot_cache import cache
from common.utils.aes_crypto import simple_aes_decrypt
from common.utils.utils import equals_ignore_case, get_domain_list, string_to_numeric_hash
from common.core.deps import Trans


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
                    for domain in get_domain_list(item.domain):
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
    request_origin: Optional[str] = None

    def __init__(self, assistant: AssistantHeader):
        self.assistant = assistant
        self.ds_list = None
        self.certificate = assistant.certificate
        self.request_origin = assistant.request_origin
        self.get_ds_from_api()

    # @cache(namespace=CacheNamespace.EMBEDDED_INFO, cacheName=CacheName.ASSISTANT_DS, keyExpression="current_user.id")
    def get_ds_from_api(self):
        config: dict[any] = json.loads(self.assistant.configuration)
        endpoint: str = config['endpoint']
        endpoint = self.get_complete_endpoint(endpoint=endpoint)
        if not endpoint:
            raise Exception(
                f"Failed to get datasource list from {config['endpoint']}, error: [Assistant domain or endpoint miss]")
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
        timeout = int(config.get('timeout')) if config.get('timeout') else 10
        res = requests.get(url=endpoint, params=param, headers=header, cookies=cookies, timeout=timeout)
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

    def get_first_element(self, text: str):
        parts = re.split(r'[,;]', text.strip())
        first_domain = parts[0].strip()
        return first_domain

    def get_complete_endpoint(self, endpoint: str) -> str | None:
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint
        domain_text = self.assistant.domain
        if not domain_text:
            return None
        if ',' in domain_text or ';' in domain_text:
            return (
                self.request_origin.strip('/') if self.request_origin else self.get_first_element(domain_text).strip(
                    '/')) + endpoint
        else:
            return f"{domain_text}{endpoint}"

    def get_simple_ds_list(self):
        if self.ds_list:
            return [{'id': ds.id, 'name': ds.name, 'description': ds.comment} for ds in self.ds_list]
        else:
            raise Exception("Datasource list is not found.")

    def get_db_schema(self, ds_id: int, question: str, embedding: bool = True) -> str:
        ds = self.get_ds(ds_id)
        schema_str = ""
        db_name = ds.db_schema if ds.db_schema is not None and ds.db_schema != "" else ds.dataBase
        schema_str += f"【DB_ID】 {db_name}\n【Schema】\n"
        tables = []
        i = 0
        for table in ds.tables:
            i += 1
            schema_table = ''
            schema_table += f"# Table: {db_name}.{table.name}" if ds.type != "mysql" and ds.type != "es" else f"# Table: {table.name}"
            table_comment = table.comment
            if table_comment == '':
                schema_table += '\n[\n'
            else:
                schema_table += f", {table_comment}\n[\n"

            field_list = []
            for field in table.fields:
                field_comment = field.comment
                if field_comment == '':
                    field_list.append(f"({field.name}:{field.type})")
                else:
                    field_list.append(f"({field.name}:{field.type}, {field_comment})")
            schema_table += ",\n".join(field_list)
            schema_table += '\n]\n'
            t_obj = {"id": i, "schema_table": schema_table}
            tables.append(t_obj)

        # do table embedding
        # if embedding and tables and settings.TABLE_EMBEDDING_ENABLED:
        #     tables = get_table_embedding(tables, question)

        if tables:
            for s in tables:
                schema_str += s.get('schema_table')

        return schema_str

    def get_ds(self, ds_id: int, trans: Trans = None):
        if self.ds_list:
            for ds in self.ds_list:
                if ds.id == ds_id:
                    return ds
        else:
            raise Exception("Datasource list is not found.")
        raise Exception(f"Datasource id {ds_id} is not found." if trans is None else trans(
            'i18n_data_training.datasource_id_not_found', key=ds_id))

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
                        raise Exception(
                            f"Failed to encrypt {attr} for datasource {ds_dict.get('name')}, error: {str(e)}")
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


def get_out_ds_conf(ds: AssistantOutDsSchema, timeout: int = 30) -> str:
    conf = {
        "host": ds.host or '',
        "port": ds.port or 0,
        "username": ds.user or '',
        "password": ds.password or '',
        "database": ds.dataBase or '',
        "driver": '',
        "extraJdbc": ds.extraParams or '',
        "dbSchema": ds.db_schema or '',
        "timeout": timeout or 30
    }
    conf["extraJdbc"] = ''
    return aes_encrypt(json.dumps(conf))
