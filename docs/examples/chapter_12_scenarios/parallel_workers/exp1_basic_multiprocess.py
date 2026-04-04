# exp1_basic_multiprocess.py - 正确的多进程用法（含耗时对比）
# docs/examples/chapter_12_scenarios/parallel_workers/exp1_basic_multiprocess.py
"""
实验目标：演示多进程并行处理的正确写法，使用真实的 ActiveRecord ORM。

关键点：
  - configure() 必须在子进程内调用，不在父进程中共享连接
  - 每个进程独立拥有自己的数据库连接
  - 同时演示同步（BaseActiveRecord）和异步（AsyncBaseActiveRecord）两种用法
  - 体现关联关系：User --(has_many)--> Post

对比实验：
  A. 串行：单进程依次为每篇文章新增一条评论
  B. 多进程（同步）：4 个进程并行处理
  C. 多进程（异步）：4 个进程，每个进程内用 asyncio 协程

运行方式：
    python setup_db.py   # 先初始化数据库
    python exp1_basic_multiprocess.py
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

from models import AsyncComment, AsyncPost, AsyncUser, Comment, Post, User  # noqa: E402

DB_PATH = "parallel_workers.db"
NUM_WORKERS = 4


def make_config() -> SQLiteConnectionConfig:
    return SQLiteConnectionConfig(
        database=DB_PATH,
        pragmas={"journal_mode": "WAL", "busy_timeout": "10000"},
    )


# ─────────────────────────────────────────────────────────────────────────────
# 辅助：获取所有已发布文章的 ID 列表，并按 Worker 数量切片
# ─────────────────────────────────────────────────────────────────────────────


def fetch_published_post_ids() -> list[int]:
    """获取所有 published 状态的文章 ID（在主进程中调用一次）"""
    config = make_config()
    Post.configure(config, SQLiteBackend)
    posts = Post.query().where(Post.c.status == "published").all()
    Post.backend().disconnect()
    return [p.id for p in posts if p.id is not None]


def split_chunks(items: list, n: int) -> list[list]:
    size = max(1, (len(items) + n - 1) // n)
    return [items[i : i + size] for i in range(0, len(items), size)]


def reset_exp_comments() -> None:
    """删除本实验插入的评论（title 以 '[exp1]' 开头）"""
    config = make_config()
    Comment.configure(config, SQLiteBackend)
    to_delete = Comment.query().where(Comment.c.body.like("[exp1]%")).all()
    for c in to_delete:
        c.delete()
    Comment.backend().disconnect()


# ─────────────────────────────────────────────────────────────────────────────
# 实验 A：串行（单进程）
# ─────────────────────────────────────────────────────────────────────────────


def run_serial(post_ids: list[int]) -> int:
    """单进程串行：为每篇文章新增一条系统评论"""
    config = make_config()
    User.configure(config, SQLiteBackend)
    Post.__backend__ = User.backend()
    Comment.__backend__ = User.backend()

    # 找到第一个用户（用于评论的 user_id）
    bot = User.query().order_by(User.c.id).one()
    if bot is None:
        return 0

    count = 0
    for post_id in post_ids:
        post = Post.find_one(post_id)
        if post is None:
            continue
        c = Comment(
            post_id=post.id,  # type: ignore[arg-type]
            user_id=bot.id,  # type: ignore[arg-type]
            body=f"[exp1] 串行评论 post#{post.id} by pid={os.getpid()}",
            is_approved=True,
        )
        c.save()
        count += 1

    User.backend().disconnect()
    return count


# ─────────────────────────────────────────────────────────────────────────────
# 实验 B：多进程（同步 ActiveRecord）
# ─────────────────────────────────────────────────────────────────────────────


def worker_sync(post_ids: list[int]) -> int:
    """
    子进程 Worker（同步版）：
    1. 在进程内调用 configure()，建立独立连接
    2. 利用关联关系查询作者并添加评论
    """
    # ✅ configure() 在子进程内调用，连接完全隔离
    config = make_config()
    User.configure(config, SQLiteBackend)
    Post.__backend__ = User.backend()
    Comment.__backend__ = User.backend()

    bot = User.query().order_by(User.c.id).one()
    if bot is None:
        return 0

    count = 0
    for post_id in post_ids:
        post = Post.find_one(post_id)
        if post is None:
            continue
        # 通过关联关系获取作者
        author = post.author()  # BelongsTo 关联
        author_name = author.username if author else "unknown"

        c = Comment(
            post_id=post.id,  # type: ignore[arg-type]
            user_id=bot.id,  # type: ignore[arg-type]
            body=(f"[exp1] 多进程同步评论 post#{post.id}（作者：{author_name}）by pid={os.getpid()}"),
            is_approved=True,
        )
        c.save()
        count += 1

    User.backend().disconnect()
    print(f"  [sync PID {os.getpid()}] 完成 {count} 篇文章")
    return count


# ─────────────────────────────────────────────────────────────────────────────
# 实验 C：多进程（异步 ActiveRecord）
# ─────────────────────────────────────────────────────────────────────────────


async def async_process_post(post_id: int, bot_id: int) -> bool:
    """异步处理单篇文章：查询文章 + 获取关联作者 + 插入评论"""
    post = await AsyncPost.find_one(post_id)
    if post is None:
        return False
    # 通过异步关联关系获取作者
    author = await post.author()  # AsyncBelongsTo 关联
    author_name = author.username if author else "unknown"

    c = AsyncComment(
        post_id=post.id,  # type: ignore[arg-type]
        user_id=bot_id,
        body=(f"[exp1] 多进程异步评论 post#{post.id}（作者：{author_name}）by pid={os.getpid()}"),
        is_approved=True,
    )
    await c.save()
    return True


async def async_worker_main(post_ids: list[int]) -> int:
    """
    异步 Worker 主函数：
    在进程内 configure()，然后用 asyncio 并发处理文章列表
    """
    config = make_config()
    # ✅ 异步 configure() 也在子进程内调用
    await AsyncUser.configure(config, AsyncSQLiteBackend)
    backend = AsyncUser.backend()
    AsyncPost.__backend__ = backend
    AsyncComment.__backend__ = backend

    bot = await AsyncUser.query().order_by(AsyncUser.c.id).one()
    if bot is None:
        return 0

    # 协程并发处理（同一进程内串行访问数据库，安全）
    tasks = [async_process_post(pid, bot.id) for pid in post_ids]  # type: ignore[arg-type]
    results = await asyncio.gather(*tasks)
    count = sum(1 for r in results if r)

    await AsyncUser.backend().disconnect()
    print(f"  [async PID {os.getpid()}] 完成 {count} 篇文章")
    return count


def worker_async(post_ids: list[int]) -> int:
    """子进程入口：每个进程独立创建 event loop"""
    return asyncio.run(async_worker_main(post_ids))


# ─────────────────────────────────────────────────────────────────────────────
# 主程序
# ─────────────────────────────────────────────────────────────────────────────


def main() -> None:
    post_ids = fetch_published_post_ids()
    if not post_ids:
        print("⚠️  没有 published 状态的文章，请先运行 setup_db.py")
        sys.exit(1)

    print(f"共找到 {len(post_ids)} 篇已发布文章\n")
    chunks = split_chunks(post_ids, NUM_WORKERS)

    # ─── 实验 A：串行 ───
    print("=== 实验 A：串行处理（单进程，同步 ActiveRecord）===")
    t0 = time.perf_counter()
    serial_count = run_serial(post_ids)
    t_serial = time.perf_counter() - t0
    print(f"串行完成 {serial_count} 篇，耗时 {t_serial:.3f}s")

    reset_exp_comments()

    # ─── 实验 B：多进程同步 ───
    print(f"\n=== 实验 B：{NUM_WORKERS} 进程并行（同步 ActiveRecord）===")
    t0 = time.perf_counter()
    with multiprocessing.Pool(processes=NUM_WORKERS) as pool:
        results_b = pool.map(worker_sync, chunks)
    t_sync = time.perf_counter() - t0
    total_b = sum(results_b)
    print(f"并行完成 {total_b} 篇，耗时 {t_sync:.3f}s")
    if t_sync > 0:
        print(f"加速比：{t_serial / t_sync:.1f}x（理论最大 {NUM_WORKERS}x）")

    reset_exp_comments()

    # ─── 实验 C：多进程异步 ───
    print(f"\n=== 实验 C：{NUM_WORKERS} 进程并行（异步 ActiveRecord）===")
    t0 = time.perf_counter()
    with multiprocessing.Pool(processes=NUM_WORKERS) as pool:
        results_c = pool.map(worker_async, chunks)
    t_async = time.perf_counter() - t0
    total_c = sum(results_c)
    print(f"并行完成 {total_c} 篇，耗时 {t_async:.3f}s")
    if t_async > 0:
        print(f"加速比：{t_serial / t_async:.1f}x（理论最大 {NUM_WORKERS}x）")

    reset_exp_comments()

    print(f"\n{'=' * 50}")
    print("结论：")
    print(f"  串行（同步）：{t_serial:.3f}s")
    print(f"  多进程同步：  {t_sync:.3f}s  ({t_serial / t_sync:.1f}x)")
    print(f"  多进程异步：  {t_async:.3f}s  ({t_serial / t_async:.1f}x)")
    print("""
关键原则：configure() 必须在子进程内调用，同步异步版本均如此，方法名完全相同。

注意：SQLite 场景下多进程异步不一定比同步更快，原因：
  - SQLite 异步后端（aiosqlite）并非真正的异步 I/O，而是将同步调用
    封装进线程池（run_in_executor）模拟异步，多了额外的调度开销
  - 数据量小时，进程启动开销也会掩盖并行收益
  - MySQL / PostgreSQL 等网络数据库后端才能从真正的异步 I/O 中受益
    （aiomysql / asyncpg 在 await 期间可真正并发处理其他协程）
  生产环境中，选择异步的主要理由是高并发 Web 服务，而非单纯提速 SQLite
""")


if __name__ == "__main__":
    main()
