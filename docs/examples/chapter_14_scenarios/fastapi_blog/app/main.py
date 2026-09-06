# docs/examples/chapter_14_scenarios/fastapi_blog/app/main.py
"""FastAPI 应用入口。

启动流程 (lifespan)：
1. 配置日志
2. 创建 AsyncBackendPool（连接池）
3. 在池连接上下文中推导 DDL 建表（无需手写 SQL）
4. 初始化 Prometheus 指标

请求处理：每个请求经 ``get_db_context`` 依赖借出独立连接（contextvar 隔离）。
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from .database import configure_models, create_pool, create_schema, make_connection_config
from .logging_conf import setup_logging
from .models import Post, User
from .routes import router

logger = logging.getLogger("blog")

ALL_MODELS = [User, Post]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. 日志
    setup_logging()
    logger.info("日志已初始化")

    # 2. 连接池
    config = make_connection_config(database="blog.db")
    configure_models(ALL_MODELS, config)
    pool = await create_pool(config)
    app.state.pool = pool
    logger.info("连接池已创建")

    # 3. 推导 DDL 建表 + 种子数据
    async with pool.connection():
        await create_schema(ALL_MODELS)
        if await User.query().count() == 0:
            alice = User(username="alice", email="alice@example.com", bio="Python developer")
            await alice.save()
            await Post(user_id=alice.id, title="Hello FastAPI", content="First post").save()
            await Post(user_id=alice.id, title="Async Is Easy", content="Second post").save()

    logger.info("数据库就绪")
    yield

    # 优雅关闭：等待在途请求，再关闭连接池
    await pool.close()
    logger.info("连接池已关闭")


app = FastAPI(
    title="博客系统 API",
    description="rhosocial-activerecord + FastAPI 博客示例",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


_instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    excluded_handlers=["/metrics", "/health"],
)
_instrumentator.instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


@app.get("/health")
async def health():
    """存活探针。"""
    return {"status": "healthy", "version": "1.0.0"}