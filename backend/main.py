import os

import sqlbot_xpack
from alembic.config import Config
from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from fastapi_mcp import FastApiMCP
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware

from alembic import command
from apps.api import api_router
from apps.system.crud.aimodel_manage import async_model_info
from apps.system.crud.assistant import init_dynamic_cors
from apps.system.middleware.auth import TokenMiddleware
from common.core.config import settings
from common.core.response_middleware import ResponseMiddleware, exception_handler
from common.core.sqlbot_cache import init_sqlbot_cache
from common.utils.embedding_threads import fill_empty_terminology_embeddings, fill_empty_data_training_embeddings
from common.utils.utils import SQLBotLogUtil


def run_migrations():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


def init_terminology_embedding_data():
    fill_empty_terminology_embeddings()


def init_data_training_embedding_data():
    fill_empty_data_training_embeddings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    init_sqlbot_cache()
    init_dynamic_cors(app)
    init_terminology_embedding_data()
    init_data_training_embedding_data()
    SQLBotLogUtil.info("✅ SQLBot 初始化完成")
    await sqlbot_xpack.core.clean_xpack_cache()
    await async_model_info()  # 异步加密已有模型的密钥和地址
    yield
    SQLBotLogUtil.info("SQLBot 应用关闭")


def custom_generate_unique_id(route: APIRoute) -> str:
    tag = route.tags[0] if route.tags and len(route.tags) > 0 else ""
    return f"{tag}-{route.name}"


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan
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
    include_operations=["get_datasource_list", "get_model_list", "mcp_question", "mcp_start", "mcp_assistant"]
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
