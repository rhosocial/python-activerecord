# exp2_sqlite_wal_mode.py - SQLite WAL 模式 vs 默认 journal 模式性能对比
# docs/examples/chapter_12_scenarios/parallel_workers/exp2_sqlite_wal_mode.py
"""
实验目标：
    对比 SQLite 默认 journal 模式和 WAL 模式下，4 进程并发写入时的性能差异。
    使用真实的 ActiveRecord ORM，演示通过 SQLiteConnectionConfig.pragmas 设置 WAL。

背景：
    - 默认 journal 模式（DELETE）：写操作对整个数据库文件加互斥锁，
      多进程并发写入时同一时刻只有一个进程可以写。
    - WAL 模式：读写可并发，写写之间仍串行但锁等待时间显著更短。

同步/异步对等：
    - sync_worker_default / async_worker_default — 默认模式
    - sync_worker_wal    / async_worker_wal     — WAL 模式
    方法名完全相同，异步版本仅需加 await。

运行方式：
    python setup_db.py   # 先初始化数据库
    python exp2_sqlite_wal_mode.py
"""

from __future__ import annotations

import asyncio
import multiprocessing
import os
import sys
import time

_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "src"))
if _src not in sys.path:
    sys.path.insert(0, _src)

from rhosocial.activerecord.backend.impl.sqlite import (  # noqa: E402
    AsyncSQLiteBackend,
    SQLiteBackend,
)
from rhosocial.activerecord.backend.impl.sqlite.config import (  # noqa: E402
    SQLiteConnectionConfig,
)

from models import AsyncPost, AsyncUser, Post, User  # noqa: E402

DB_PATH = "parallel_workers.db"
NUM_WORKERS = 4


# ─────────────────────────────────────────────────────────────────────────────
# 辅助
# ─────────────────────────────────────────────────────────────────────────────


def fetch_all_post_ids() -> list[int]:
    config = SQLiteConnectionConfig(database=DB_PATH)
    Post.configure(config, SQLiteBackend)
    ids = [p.id for p in Post.query().order_by(Post.c.id).all() if p.id is not None]
    Post.backend().disconnect()
    return ids


def split_chunks(items: list, n: int) -> list[list]:
    size = max(1, (len(items) + n - 1) // n)
    return [items[i : i + size] for i in range(0, len(items), size)]


def reset_posts(post_ids: list[int]) -> None:
    """重置实验中修改的 view_count"""
    config = SQLiteConnectionConfig(database=DB_PATH)
    Post.configure(config, SQLiteBackend)
    for pid in post_ids:
        p = Post.find_one(pid)
        if p is not None:
            p.view_count = 0
            p.save()
    Post.backend().disconnect()


# ─────────────────────────────────────────────────────────────────────────────
# 同步版 Worker
# ─────────────────────────────────────────────────────────────────────────────


def sync_worker_default(post_ids: list[int]) -> int:
    """同步 Worker — 默认 journal 模式（不设置 pragmas）"""
    config = SQLiteConnectionConfig(database=DB_PATH, timeout=30.0)
    User.configure(config, SQLiteBackend)
    Post.__backend__ = User.backend()

    count = 0
    for post_id in post_ids:
        post = Post.find_one(post_id)
        if post is None:
            continue
        post.view_count += 1
        post.save()  # 每次单独提交（最坏情况：频繁获取写锁）
        count += 1

    User.backend().disconnect()
    return count


def sync_worker_wal(post_ids: list[int]) -> int:
    """
    同步 Worker — WAL 模式。
    通过 SQLiteConnectionConfig.pragmas 在连接时自动设置，
    这是文档推荐的方式（比连接后调用 set_pragma() 更简洁）。
    """
    config = SQLiteConnectionConfig(
        database=DB_PATH,
        timeout=30.0,
        pragmas={
            "journal_mode": "WAL",
            "synchronous": "NORMAL",
            "busy_timeout": "5000",
        },
    )
    User.configure(config, SQLiteBackend)
    Post.__backend__ = User.backend()

    count = 0
    for post_id in post_ids:
        post = Post.find_one(post_id)
        if post is None:
            continue
        post.view_count += 1
        post.save()
        count += 1

    User.backend().disconnect()
    return count


# ─────────────────────────────────────────────────────────────────────────────
# 异步版 Worker（方法名与同步版相同，加 await）
# ─────────────────────────────────────────────────────────────────────────────


async def _async_increment_views(post_ids: list[int]) -> int:
    count = 0
    for post_id in post_ids:
        post = await AsyncPost.find_one(post_id)
        if post is None:
            continue
        post.view_count += 1
        await post.save()
        count += 1
    return count


async def async_worker_default_main(post_ids: list[int]) -> int:
    """异步 Worker 主函数 — 默认模式"""
    config = SQLiteConnectionConfig(database=DB_PATH, timeout=30.0)
    await AsyncUser.configure(config, AsyncSQLiteBackend)
    AsyncPost.__backend__ = AsyncUser.backend()
    count = await _async_increment_views(post_ids)
    await AsyncUser.backend().disconnect()
    return count


async def async_worker_wal_main(post_ids: list[int]) -> int:
    """异步 Worker 主函数 — WAL 模式（通过 pragmas 配置，与同步版完全对称）"""
    config = SQLiteConnectionConfig(
        database=DB_PATH,
        timeout=30.0,
        pragmas={
            "journal_mode": "WAL",
            "synchronous": "NORMAL",
            "busy_timeout": "5000",
        },
    )
    await AsyncUser.configure(config, AsyncSQLiteBackend)
    AsyncPost.__backend__ = AsyncUser.backend()
    count = await _async_increment_views(post_ids)
    await AsyncUser.backend().disconnect()
    return count


def async_worker_default(post_ids: list[int]) -> int:
    return asyncio.run(async_worker_default_main(post_ids))


def async_worker_wal(post_ids: list[int]) -> int:
    return asyncio.run(async_worker_wal_main(post_ids))


# ─────────────────────────────────────────────────────────────────────────────
# 通用实验执行函数
# ─────────────────────────────────────────────────────────────────────────────


def run_experiment(label: str, worker_fn, chunks: list[list]) -> float:
    t0 = time.perf_counter()
    with multiprocessing.Pool(processes=NUM_WORKERS) as pool:
        results = pool.map(worker_fn, chunks)
    elapsed = time.perf_counter() - t0
    total = sum(results)
    print(f"  {label}: 处理 {total} 篇文章，耗时 {elapsed:.3f}s")
    return elapsed


# ─────────────────────────────────────────────────────────────────────────────
# 主程序
# ─────────────────────────────────────────────────────────────────────────────


def main() -> None:
    all_ids = fetch_all_post_ids()
    if not all_ids:
        print("⚠️  没有文章数据，请先运行 setup_db.py")
        sys.exit(1)

    chunks = split_chunks(all_ids, NUM_WORKERS)
    print(f"实验设置：{NUM_WORKERS} 个进程，共 {len(all_ids)} 篇文章\n")

    # ─── 同步版对比 ───
    print("=== 同步版：默认模式 vs WAL 模式 ===")
    t_sync_default = run_experiment("同步-默认模式", sync_worker_default, chunks)
    reset_posts(all_ids)

    t_sync_wal = run_experiment("同步-WAL 模式", sync_worker_wal, chunks)
    reset_posts(all_ids)

    # ─── 异步版对比 ───
    print("\n=== 异步版：默认模式 vs WAL 模式 ===")
    t_async_default = run_experiment("异步-默认模式", async_worker_default, chunks)
    reset_posts(all_ids)

    t_async_wal = run_experiment("异步-WAL 模式", async_worker_wal, chunks)
    reset_posts(all_ids)

    # ─── 对比结论 ───
    print(f"\n{'=' * 55}")
    print("WAL 模式加速比：")
    if t_sync_wal > 0:
        print(f"  同步：{t_sync_default / t_sync_wal:.2f}x")
    if t_async_wal > 0:
        print(f"  异步：{t_async_default / t_async_wal:.2f}x")
    print("""
结论：
  - 通过 SQLiteConnectionConfig(pragmas={...}) 一行配置即可启用 WAL 模式
  - 同步和异步版本的配置方式完全相同（方法名相同，异步加 await）
  - WAL 模式写入之间仍然串行；真正的并发写入需要 MySQL / PostgreSQL
  - set_pragma() 是 SQLite 专属方法，MySQL/PostgreSQL 后端不提供此方法

注意：SQLite 异步版本（aiosqlite）不是真正的异步 I/O：
  - aiosqlite 将同步 SQLite 调用封装进线程池（run_in_executor）来模拟异步
  - 相比同步版本，多了线程切换 + 协程调度的额外开销
  - SQLite 写入仍然串行，await 无法带来并发加速
  - 因此 SQLite 场景下"异步 ≈ 同步甚至略慢"是正常现象，并非代码问题
  - 真正受益于 async/await 的是 MySQL/PostgreSQL 等网络数据库后端
    （aiomysql / asyncpg 使用真正的异步网络 I/O，await 期间可处理其他协程）
""")


if __name__ == "__main__":
    main()
