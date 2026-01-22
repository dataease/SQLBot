import os
from typing import Dict, Any

import sqlbot_xpack
from alembic.config import Config
from fastapi import FastAPI, Request
from fastapi.concurrency import asynccontextmanager
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from fastapi_mcp import FastApiMCP
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware

from alembic import command
from apps.api import api_router
from apps.swagger.i18n import PLACEHOLDER_PREFIX, tags_metadata, i18n_list
from apps.swagger.i18n import get_translation, DEFAULT_LANG
from apps.system.crud.aimodel_manage import async_model_info
from apps.system.crud.assistant import init_dynamic_cors
from apps.system.middleware.auth import TokenMiddleware
from apps.system.schemas.permission import RequestContextMiddleware
from common.audit.schemas.request_context import RequestContextMiddlewareCommon
from common.core.config import settings
from common.core.response_middleware import ResponseMiddleware, exception_handler
from common.core.sqlbot_cache import init_sqlbot_cache
from common.utils.embedding_threads import fill_empty_terminology_embeddings, fill_empty_data_training_embeddings, \
    fill_empty_table_and_ds_embeddings
from common.utils.utils import SQLBotLogUtil


def run_migrations():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


def init_terminology_embedding_data():
    fill_empty_terminology_embeddings()


def init_data_training_embedding_data():
    fill_empty_data_training_embeddings()


def init_table_and_ds_embedding():
    fill_empty_table_and_ds_embeddings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    init_sqlbot_cache()
    init_dynamic_cors(app)
    init_terminology_embedding_data()
    init_data_training_embedding_data()
    init_table_and_ds_embedding()
    SQLBotLogUtil.info("✅ SQLBot 初始化完成")
    await sqlbot_xpack.core.clean_xpack_cache()
    await async_model_info()  # 异步加密已有模型的密钥和地址
    await sqlbot_xpack.core.monitor_app(app)
    yield
    SQLBotLogUtil.info("SQLBot 应用关闭")


def custom_generate_unique_id(route: APIRoute) -> str:
    tag = route.tags[0] if route.tags and len(route.tags) > 0 else ""
    return f"{tag}-{route.name}"


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None
)

# cache docs for different text
_openapi_cache: Dict[str, Dict[str, Any]] = {}

# replace placeholder
def replace_placeholders_in_schema(schema: Dict[str, Any], trans: Dict[str, str]) -> None:
    """
    search OpenAPI schema，replace PLACEHOLDER_xxx to text。
    """
    if isinstance(schema, dict):
        for key, value in schema.items():
            if isinstance(value, str) and value.startswith(PLACEHOLDER_PREFIX):
                placeholder_key = value[len(PLACEHOLDER_PREFIX):]
                schema[key] = trans.get(placeholder_key, value)
            else:
                replace_placeholders_in_schema(value, trans)
    elif isinstance(schema, list):
        for item in schema:
            replace_placeholders_in_schema(item, trans)



# OpenAPI build
def get_language_from_request(request: Request) -> str:
    # get param from query ?lang=zh
    lang = request.query_params.get("lang")
    if lang in i18n_list:
        return lang
    # get lang from Accept-Language Header
    accept_lang = request.headers.get("accept-language", "")
    if "zh" in accept_lang.lower():
        return "zh"
    return DEFAULT_LANG


def generate_openapi_for_lang(lang: str) -> Dict[str, Any]:
    if lang in _openapi_cache:
        return _openapi_cache[lang]

    # tags metadata
    trans = get_translation(lang)
    localized_tags = []
    for tag in tags_metadata:
        desc = tag["description"]
        if desc.startswith(PLACEHOLDER_PREFIX):
            key = desc[len(PLACEHOLDER_PREFIX):]
            desc = trans.get(key, desc)
        localized_tags.append({
            "name": tag["name"],
            "description": desc
        })

    # 1. create OpenAPI
    openapi_schema = get_openapi(
        title="SQLBot API Document" if lang == "en" else "SQLBot API 文档",
        version="1.0.0",
        routes=app.routes,
        tags=localized_tags
    )

    # openapi version
    openapi_schema.setdefault("openapi", "3.1.0")

    # 2. get trans for lang
    trans = get_translation(lang)

    # 3. replace placeholder
    replace_placeholders_in_schema(openapi_schema, trans)

    # 4. cache
    _openapi_cache[lang] = openapi_schema
    return openapi_schema



# custom /openapi.json and /docs
@app.get("/openapi.json", include_in_schema=False)
async def custom_openapi(request: Request):
    lang = get_language_from_request(request)
    schema = generate_openapi_for_lang(lang)
    return JSONResponse(schema)


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui(request: Request):
    lang = get_language_from_request(request)
    from fastapi.openapi.docs import get_swagger_ui_html
    return get_swagger_ui_html(
        openapi_url=f"/openapi.json?lang={lang}",
        title="SQLBot API Docs",
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
        swagger_js_url="/swagger-ui-bundle.js",
        swagger_css_url="/swagger-ui.css",
    )


mcp_app = FastAPI()
# mcp server, images path
images_path = settings.MCP_IMAGE_PATH
os.makedirs(images_path, exist_ok=True)
mcp_app.mount("/images", StaticFiles(directory=images_path), name="images")

mcp = FastApiMCP(
    app,
    name="SQLBot MCP Server",
    description="SQLBot MCP Server",
    describe_all_responses=True,
    describe_full_response_schema=True,
    include_operations=["mcp_datasource_list", "get_model_list", "mcp_question", "mcp_start", "mcp_assistant"]
)

mcp.mount(mcp_app)

# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.add_middleware(TokenMiddleware)
app.add_middleware(ResponseMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(RequestContextMiddlewareCommon)
app.include_router(api_router, prefix=settings.API_V1_STR)

# Register exception handlers
app.add_exception_handler(StarletteHTTPException, exception_handler.http_exception_handler)
app.add_exception_handler(Exception, exception_handler.global_exception_handler)

mcp.setup_server()

sqlbot_xpack.init_fastapi_app(app)
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    # uvicorn.run("main:mcp_app", host="0.0.0.0", port=8001) # mcp server
