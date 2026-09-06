# docs/examples/chapter_14_scenarios/graphql_fastapi/app/database.py
"""数据库配置：连接池 + 推导 DDL + 请求级连接隔离。

与 ``fastapi_blog`` 场景完全相同的模式：
- 应用启动 (lifespan) 创建 ``AsyncBackendPool``
- 每个 GraphQL 请求通过 ``get_db_context`` 依赖借出独立连接（contextvar 隔离）
- ``generate_create_table()`` 由模型推导 DDL，无需手写建表 SQL
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List, Type

from fastapi import Request

from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.connection.pool import AsyncBackendPool, PoolConfig
from rhosocial.activerecord.interface.model import IAsyncActiveRecord


def make_connection_config(database: str = "graphql.db") -> SQLiteConnectionConfig:
    return SQLiteConnectionConfig(database=database)


def configure_models(models: List[Type[IAsyncActiveRecord]], config: SQLiteConnectionConfig) -> None:
    for model in models:
        model.__backend_class__ = AsyncSQLiteBackend
        model.__connection_config__ = config


async def create_schema(models: List[Type[IAsyncActiveRecord]]) -> None:
    options = ExecutionOptions(stmt_type=StatementType.DDL)
    for model in models:
        expr = model.generate_create_table(if_not_exists=True)
        sql, params = expr.to_sql()
        await model.backend().execute(sql, params, options=options)


async def create_pool(config: SQLiteConnectionConfig) -> AsyncBackendPool:
    pool_config = PoolConfig(
        min_size=2,
        max_size=10,
        connection_mode="auto",
        backend_factory=lambda: AsyncSQLiteBackend(connection_config=config),
    )
    return await AsyncBackendPool.create(pool_config)


async def get_db_context(request: Request) -> AsyncGenerator[None, None]:
    """FastAPI 依赖：为当前请求借出一个独立连接（原生 async generator 依赖）。"""
    pool: AsyncBackendPool = request.app.state.pool
    async with pool.connection():
        yield