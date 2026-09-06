# docs/examples/chapter_14_scenarios/fastapi_blog/tests/manual_mysql_pool_compare.py
"""手动对照实验：共享单连接 vs AsyncBackendPool（MySQL 后端）。

运行前提：有一个可达的 MySQL 服务器。可通过环境变量指定连接：
    MYSQL_HOST / MYSQL_PORT / MYSQL_DB / MYSQL_USER / MYSQL_PASSWORD

演示结果（本机 MySQL 8.0.46 实测，30 路并发写入）：
    共享单连接：1 成功 / 29 失败
        错误：DatabaseError: read() called while another coroutine is
              already waiting for incoming data
        原因：mysql-connector 的异步连接不允许同一时刻多个协程并发读写；
              多个请求共享同一后端实例（同一连接）时必然冲突。
    AsyncBackendPool：30/30 全部成功，数据完整。
        每个请求从池中借出**独立连接**，通过 contextvar 隔离，互不干扰。

用法：
    python manual_mysql_pool_compare.py
"""
import asyncio
import os
from typing import ClassVar, Optional

from rhosocial.activerecord.model import AsyncActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.backend.impl.mysql import AsyncMySQLBackend
from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig
from rhosocial.activerecord.connection.pool import AsyncBackendPool, PoolConfig

HOST = os.getenv("MYSQL_HOST", "localhost")
PORT = int(os.getenv("MYSQL_PORT", "3306"))
DB = os.getenv("MYSQL_DB", "test_db")
USER = os.getenv("MYSQL_USER", "root")
PWD = os.getenv("MYSQL_PASSWORD", "password")

USER_TABLE = "blog_user"
POST_TABLE = "blog_post"
N_CONCURRENT = 30


def make_config() -> MySQLConnectionConfig:
    return MySQLConnectionConfig(host=HOST, port=PORT, database=DB, username=USER, password=PWD)


class User(IntegerPKMixin, AsyncActiveRecord):
    """用户：自增主键。"""
    __table_name__ = USER_TABLE
    id: Optional[int] = None
    username: str
    c: ClassVar[FieldProxy] = FieldProxy()


class Post(IntegerPKMixin, AsyncActiveRecord):
    """文章：外键指向 User。"""
    __table_name__ = POST_TABLE
    id: Optional[int] = None
    user_id: int
    title: str
    c: ClassVar[FieldProxy] = FieldProxy()


async def _drop(backend) -> None:
    for t in (POST_TABLE, USER_TABLE):
        try:
            await backend.execute(f"DROP TABLE IF EXISTS {t}")
        except Exception:
            pass


async def _create_tables() -> None:
    for m in (User, Post):
        expr = m.generate_create_table(if_not_exists=True)
        sql, _ = expr.to_sql()
        await m.backend().execute(sql)


async def run_shared_single() -> None:
    """反例：User / Post 共享同一 backend 实例（同一连接）。"""
    print("=" * 70)
    print("反例：多个模型共享同一个后端实例（不隔离连接）")
    config = make_config()
    await User.configure(config, AsyncMySQLBackend)
    shared = User.__backend__
    Post.__backend__ = shared  # ← 反例：Post 直接复用 User 的连接

    await _drop(shared)
    await _create_tables()

    async def create(i: int):
        user = User(username=f"u_{i}")
        await user.save()
        await asyncio.sleep(0.01)  # 制造真实的并发交错窗口
        post = Post(user_id=user.id, title=f"p_{i}")
        await post.save()

    results = await asyncio.gather(*[create(i) for i in range(N_CONCURRENT)], return_exceptions=True)
    ok = sum(1 for r in results if not isinstance(r, Exception))
    errs = [r for r in results if isinstance(r, Exception)]
    print(f"  30 路并发写入: 成功 {ok} / 失败 {len(errs)}")
    if errs:
        from collections import Counter
        print(f"  错误类型: {dict(Counter(type(e).__name__ for e in errs))}")
        for e in errs[:3]:
            print(f"    示例: {type(e).__name__}: {str(e)[:120]}")

    await shared.disconnect()


async def run_pool() -> None:
    """正确：AsyncBackendPool，每次操作从池中借出独立连接。"""
    print("=" * 70)
    print("正确：AsyncBackendPool + 每请求独立连接")
    config = make_config()
    pool = await AsyncBackendPool.create(
        PoolConfig(
            min_size=2,
            max_size=10,
            connection_mode="auto",
            backend_factory=lambda: AsyncMySQLBackend(connection_config=config),
        )
    )

    async with pool.connection():
        await _drop(User.backend())
        for m in (User, Post):
            m.__backend_class__ = AsyncMySQLBackend
            m.__connection_config__ = config
        await _create_tables()

    async def create(i: int):
        async with pool.connection():  # 每个并发借独立连接
            user = User(username=f"u_{i}")
            await user.save()
            await asyncio.sleep(0.01)
            post = Post(user_id=user.id, title=f"p_{i}")
            await post.save()

    results = await asyncio.gather(*[create(i) for i in range(N_CONCURRENT)], return_exceptions=True)
    ok = sum(1 for r in results if not isinstance(r, Exception))
    errs = [r for r in results if isinstance(r, Exception)]
    print(f"  30 路并发写入: 成功 {ok} / 失败 {len(errs)}")
    if errs:
        from collections import Counter
        print(f"  错误类型: {dict(Counter(type(e).__name__ for e in errs))}")

    async with pool.connection():
        count = await User.query().count()
        print(f"  最终 User 记录数: {count}")
    await pool.close()


async def main() -> None:
    await run_shared_single()
    await run_pool()


if __name__ == "__main__":
    asyncio.run(main())