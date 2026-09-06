# docs/examples/chapter_14_scenarios/fastapi_blog/app/database.py
"""数据库配置：连接池 + 推导 DDL + 请求级连接隔离。

核心机制（参考真实项目实践）：
- 应用启动 (lifespan) 时创建 ``AsyncBackendPool``，所有模型共享同一份
  后端类与连接配置（``__backend_class__`` / ``__connection_config__``）。
- 每个 HTTP 请求通过 ``get_db_context`` 依赖从池中借出**自己的**连接，
  该连接通过 ``contextvars`` 绑定到当前请求上下文 —— 因此并发的请求
  各自使用独立连接，互不干扰，也不会阻塞事件循环。
- 建表不再手写 SQL：调用 ``Model.generate_create_table()`` 由模型推导 DDL。
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


def make_connection_config(database: str = "blog.db") -> SQLiteConnectionConfig:
    """创建 SQLite 连接配置。

    SQLite 默认启用 WAL 等 PRAGMA；``:memory:`` 仅用于单连接场景，
    生产请使用文件数据库以便连接池共享同一份数据。
    """
    return SQLiteConnectionConfig(database=database)


def configure_models(models: List[Type[IAsyncActiveRecord]], config: SQLiteConnectionConfig) -> None:
    """为所有模型配置后端类与连接配置。

    模型本身不持有固定后端实例；在 ``pool.connection()`` 上下文中，
    ``Model.backend()`` 会优先解析到当前请求借出的连接。
    """
    for model in models:
        model.__backend_class__ = AsyncSQLiteBackend
        model.__connection_config__ = config


async def create_schema(models: List[Type[IAsyncActiveRecord]]) -> None:
    """推导 DDL：由模型定义自动生成并执行 CREATE TABLE。

    列类型取自 ``UseSqlType`` 注解（或按 Python 类型自动推断），
    无需手写任何建表 SQL。``if_not_exists=True`` 保证可重复执行。
    """
    options = ExecutionOptions(stmt_type=StatementType.DDL)
    for model in models:
        expr = model.generate_create_table(if_not_exists=True)
        sql, params = expr.to_sql()
        await model.backend().execute(sql, params, options=options)


async def create_pool(config: SQLiteConnectionConfig) -> AsyncBackendPool:
    """创建异步连接池。

    ``connection_mode="auto"`` 在异步后端下等效于 ``"persistent"``：
    连接在池创建时预热，并在请求间复用。每个请求通过 ``connection()``
    借出，请求结束后归还。
    """
    pool_config = PoolConfig(
        min_size=2,
        max_size=10,
        connection_mode="auto",
        backend_factory=lambda: AsyncSQLiteBackend(connection_config=config),
    )
    return await AsyncBackendPool.create(pool_config)


async def get_db_context(request: Request) -> AsyncGenerator[None, None]:
    """FastAPI 依赖：为当前请求借出一个独立连接。

    这是一个**原生 async generator 依赖**（FastAPI 的 yield 依赖约定）：
    ``yield`` 之前的代码在请求开始时执行，``yield`` 之后的在请求结束时执行。

    在 ``async with pool.connection():`` 内部，``contextvars`` 会设置
    当前异步连接后端，使 ``User.query()`` / ``Post.find_one()`` 等调用
    自动使用该请求专属的连接。请求处理完成后自动归还连接。
    """
    pool: AsyncBackendPool = request.app.state.pool
    async with pool.connection():
        yield