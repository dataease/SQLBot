# Author: Junjun
# Date: 2025/9/9

import json
from base64 import b64encode

import requests
from elasticsearch import Elasticsearch

from apps.datasource.models.datasource import DatasourceConf
from common.error import SingleMessageError


def get_es_auth(conf: DatasourceConf):
    username = f"{conf.username}"
    password = f"{conf.password}"

    credentials = f"{username}:{password}"
    encoded_credentials = b64encode(credentials.encode()).decode()

    return {
        "Content-Type": "application/json",
        "Authorization": f"Basic {encoded_credentials}"
    }


def get_es_connect(conf: DatasourceConf):
    es_client = Elasticsearch(
        [conf.host],  # ES address
        basic_auth=(conf.username, conf.password),
        verify_certs=False,
        compatibility_mode=True,
        headers=get_es_auth(conf)
    )
    return es_client


# get tables
def get_es_index(conf: DatasourceConf):
    es_client = get_es_connect(conf)
    indices = es_client.cat.indices(format="json")
    res = []
    if indices is not None:
        for idx in indices:
            index_name = idx.get('index')
            desc = ''
            # get mapping
            mapping = es_client.indices.get_mapping(index=index_name)
            mappings = mapping.get(index_name).get("mappings")
            if mappings.get('_meta'):
                desc = mappings.get('_meta').get('description')
            res.append((index_name, desc))
    return res


# get fields
def get_es_fields(conf: DatasourceConf, table_name: str):
    es_client = get_es_connect(conf)
    index_name = table_name
    mapping = es_client.indices.get_mapping(index=index_name)
    properties = mapping.get(index_name).get("mappings").get("properties")
    res = []
    if properties is not None:
        for field, config in properties.items():
            field_type = config.get("type")
            desc = ''
            if config.get("_meta"):
                desc = config.get("_meta").get('description')

            if field_type:
                res.append((field, field_type, desc))
            else:
                # object、nested...
                res.append((field, ','.join(list(config.keys())), desc))
    return res


# def get_es_data(conf: DatasourceConf, sql: str, table_name: str):
#     r = requests.post(f"{conf.host}/_sql/translate", json={"query": sql})
#     if r.json().get('error'):
#         print(json.dumps(r.json()))
#
#     es_client = get_es_connect(conf)
#     response = es_client.search(
#         index=table_name,
#         body=json.dumps(r.json())
#     )
#
#     # print(response)
#     fields = get_es_fields(conf, table_name)
#     res = []
#     for hit in response.get('hits').get('hits'):
#         item = []
#         if 'fields' in hit:
#             result = hit.get('fields')  # {'title': ['Python'], 'age': [30]}
#             for field in fields:
#                 v = result.get(field[0])
#                 item.append(v[0]) if v else item.append(None)
#             res.append(tuple(item))
#             # print(hit['fields']['title'][0])
#         # elif '_source' in hit:
#         #     print(hit.get('_source'))
#     return res, fields


def get_es_data_by_http(conf: DatasourceConf, sql: str):
    url = conf.host
    while url.endswith('/'):
        url = url[:-1]

    host = f'{url}/_sql?format=json'

    # Security improvement: Enable SSL certificate verification
    # Note: In production, always set verify=True or provide path to CA bundle
    # If using self-signed certificates, provide the cert path: verify='/path/to/cert.pem'
    verify_ssl = True if not url.startswith('https://localhost') else False
    
    response = requests.post(
        host, 
        data=json.dumps({"query": sql}), 
        headers=get_es_auth(conf), 
        verify=verify_ssl,
        timeout=30  # Add timeout to prevent hanging
    )

    # print(response.json())
    res = response.json()
    if res.get('error'):
        raise SingleMessageError(json.dumps(res))
    fields = res.get('columns')
    result = res.get('rows')
    return result, fields
