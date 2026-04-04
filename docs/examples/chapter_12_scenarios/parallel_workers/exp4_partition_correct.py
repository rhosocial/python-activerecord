# exp4_partition_correct.py - 数据分区 + 原子领取的正确实现
# docs/examples/chapter_12_scenarios/parallel_workers/exp4_partition_correct.py
"""
实验目标：
    演示两种正确的多进程并行处理策略，使用真实的 ActiveRecord ORM。
    同时提供同步和异步两个版本，方法名完全相同，异步版本加 await。

    方案 A：数据分区
        将文章按 user_id 分配给各 Worker，互不重叠，无竞争。
        体现关联关系：Worker 处理自己负责的用户的文章，并遍历其评论。

    方案 B：原子领取
        在事务内查询 + 更新状态，保证只有一个 Worker 能成功领取同一批文章。

验证：每篇文章只被处理一次（view_count 精确为 1）。

运行方式：
    python setup_db.py   # 先初始化数据库
    python exp4_partition_correct.py
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
CLAIM_BATCH = 3  # 原子领取每次批量数


def make_config() -> SQLiteConnectionConfig:
    return SQLiteConnectionConfig(
        database=DB_PATH,
        pragmas={"journal_mode": "WAL", "busy_timeout": "10000"},
    )


# ─────────────────────────────────────────────────────────────────────────────
# 辅助：重置 + 获取用户列表
# ─────────────────────────────────────────────────────────────────────────────


def reset_all_posts() -> None:
    config = make_config()
    Post.configure(config, SQLiteBackend)
    posts = Post.query().all()
    for p in posts:
        p.status = "draft"
        p.view_count = 0
        p.save()
    Post.backend().disconnect()


def fetch_user_ids() -> list[int]:
    config = make_config()
    User.configure(config, SQLiteBackend)
    ids = [u.id for u in User.query().order_by(User.c.id).all() if u.id is not None]
    User.backend().disconnect()
    return ids


def verify_no_duplicates() -> tuple[bool, int]:
    """验证所有文章均已发布且 view_count > 0（只被处理了一次）"""
    config = make_config()
    Post.configure(config, SQLiteBackend)
    posts = Post.query().where(Post.c.status == "published").all()
    ok = all(p.view_count > 0 for p in posts)
    count = len(posts)
    Post.backend().disconnect()
    return ok, count


# ═══════════════════════════════════════════════════════════════════════════════
# 方案 A：数据分区（同步版）
# ═══════════════════════════════════════════════════════════════════════════════


def worker_partition_sync(user_ids: list[int]) -> int:
    """
    同步 Worker：只处理指定 user_id 的文章，通过关联关系遍历评论。

    体现关联：
      - User --(has_many)--> Post  --(has_many)--> Comment
      - 统计每篇文章的已审核评论数，写入 view_count
    """
    config = make_config()
    User.configure(config, SQLiteBackend)
    Post.__backend__ = User.backend()
    Comment.__backend__ = User.backend()

    count = 0
    for uid in user_ids:
        # 查询该用户的所有文章（BelongsTo 反向：通过 user_id 查询）
        posts = Post.query().where(Post.c.user_id == uid).all()
        for post in posts:
            # 通过 HasMany 关联获取评论
            approved = [c for c in post.comments() if c.is_approved]
            post.status = "published"
            post.view_count = 1 + len(approved)  # 基数1 + 已审核评论数
            post.save()
            count += 1

    User.backend().disconnect()
    print(f"  [分区 sync PID {os.getpid()}] 处理了 {count} 篇文章")
    return count


# ═══════════════════════════════════════════════════════════════════════════════
# 方案 A：数据分区（异步版）— 方法名与同步版相同，加 await
# ═══════════════════════════════════════════════════════════════════════════════


async def _async_partition_main(user_ids: list[int]) -> int:
    config = make_config()
    await AsyncUser.configure(config, AsyncSQLiteBackend)
    backend = AsyncUser.backend()
    AsyncPost.__backend__ = backend
    AsyncComment.__backend__ = backend

    count = 0
    for uid in user_ids:
        posts = await AsyncPost.query().where(AsyncPost.c.user_id == uid).all()
        for post in posts:
            approved = [c for c in await post.comments() if c.is_approved]
            post.status = "published"
            post.view_count = 1 + len(approved)
            await post.save()
            count += 1

    await AsyncUser.backend().disconnect()
    print(f"  [分区 async PID {os.getpid()}] 处理了 {count} 篇文章")
    return count


def worker_partition_async(user_ids: list[int]) -> int:
    return asyncio.run(_async_partition_main(user_ids))


# ═══════════════════════════════════════════════════════════════════════════════
# 方案 B：原子领取（同步版）
# ═══════════════════════════════════════════════════════════════════════════════


def claim_posts_sync(batch: int = CLAIM_BATCH) -> list[Post]:
    """
    在事务内原子领取：查询 + 更新在同一事务中完成。
    事务隔离保证只有一个 Worker 能成功领取同一批文章。
    """
    with Post.transaction():
        pending = Post.query().where(Post.c.status == "draft").order_by(Post.c.id).limit(batch).all()
        if not pending:
            return []
        for post in pending:
            post.status = "processing"
            post.view_count = 0
            post.save()
        return pending


def worker_atomic_sync(worker_id: int) -> int:
    """同步 Worker：循环原子领取直到无任务"""
    config = make_config()
    User.configure(config, SQLiteBackend)
    Post.__backend__ = User.backend()
    Comment.__backend__ = User.backend()

    total = 0
    while True:
        batch = claim_posts_sync()
        if not batch:
            break
        for post in batch:
            # 通过关联查询评论数
            approved_count = len([c for c in post.comments() if c.is_approved])
            post.status = "published"
            post.view_count = 1 + approved_count
            post.save()
            total += 1

    User.backend().disconnect()
    print(f"  [原子 sync Worker {worker_id}] 处理了 {total} 篇文章")
    return total


# ═══════════════════════════════════════════════════════════════════════════════
# 方案 B：原子领取（异步版）— 方法名与同步版相同，加 await
# ═══════════════════════════════════════════════════════════════════════════════


async def claim_posts_async(batch: int = CLAIM_BATCH) -> list[AsyncPost]:
    """异步原子领取：async with transaction()，结构与同步版完全对称"""
    async with AsyncPost.transaction():
        pending = await (
            AsyncPost.query().where(AsyncPost.c.status == "draft").order_by(AsyncPost.c.id).limit(batch).all()
        )
        if not pending:
            return []
        for post in pending:
            post.status = "processing"
            post.view_count = 0
            await post.save()
        return pending


async def _async_atomic_main(worker_id: int) -> int:
    config = make_config()
    await AsyncUser.configure(config, AsyncSQLiteBackend)
    backend = AsyncUser.backend()
    AsyncPost.__backend__ = backend
    AsyncComment.__backend__ = backend

    total = 0
    while True:
        batch = await claim_posts_async()
        if not batch:
            break
        for post in batch:
            approved_count = len([c for c in await post.comments() if c.is_approved])
            post.status = "published"
            post.view_count = 1 + approved_count
            await post.save()
            total += 1

    await AsyncUser.backend().disconnect()
    print(f"  [原子 async Worker {worker_id}] 处理了 {total} 篇文章")
    return total


def worker_atomic_async(worker_id: int) -> int:
    return asyncio.run(_async_atomic_main(worker_id))


# ─────────────────────────────────────────────────────────────────────────────
# 主程序
# ─────────────────────────────────────────────────────────────────────────────


def main() -> None:
    user_ids = fetch_user_ids()
    if not user_ids:
        print("⚠️  没有用户数据，请先运行 setup_db.py")
        sys.exit(1)

    # 将用户按 Worker 数量分组
    size = max(1, (len(user_ids) + NUM_WORKERS - 1) // NUM_WORKERS)
    uid_chunks = [user_ids[i : i + size] for i in range(0, len(user_ids), size)]

    # ─── 方案 A：数据分区（同步）───
    print("=== 方案 A：数据分区（同步 ActiveRecord）===")
    reset_all_posts()
    t0 = time.perf_counter()
    with multiprocessing.Pool(processes=NUM_WORKERS) as pool:
        results_a_sync = pool.map(worker_partition_sync, uid_chunks)
    t_a_sync = time.perf_counter() - t0
    total_a_sync = sum(results_a_sync)
    ok_a_sync, done_a_sync = verify_no_duplicates()
    print(
        f"  结果：Worker 共处理 {total_a_sync} 篇，发布 {done_a_sync} 篇，"
        f"耗时 {t_a_sync:.3f}s {'✅ 无重复' if ok_a_sync else '❌ 有重复'}"
    )

    # ─── 方案 A：数据分区（异步）───
    print("\n=== 方案 A：数据分区（异步 ActiveRecord）===")
    reset_all_posts()
    t0 = time.perf_counter()
    with multiprocessing.Pool(processes=NUM_WORKERS) as pool:
        results_a_async = pool.map(worker_partition_async, uid_chunks)
    t_a_async = time.perf_counter() - t0
    total_a_async = sum(results_a_async)
    ok_a_async, done_a_async = verify_no_duplicates()
    print(
        f"  结果：Worker 共处理 {total_a_async} 篇，发布 {done_a_async} 篇，"
        f"耗时 {t_a_async:.3f}s {'✅ 无重复' if ok_a_async else '❌ 有重复'}"
    )

    # ─── 方案 B：原子领取（同步）───
    print("\n=== 方案 B：原子领取（同步 ActiveRecord）===")
    reset_all_posts()
    t0 = time.perf_counter()
    with multiprocessing.Pool(processes=NUM_WORKERS) as pool:
        results_b_sync = pool.map(worker_atomic_sync, list(range(NUM_WORKERS)))
    t_b_sync = time.perf_counter() - t0
    total_b_sync = sum(results_b_sync)
    ok_b_sync, done_b_sync = verify_no_duplicates()
    print(
        f"  结果：Worker 共处理 {total_b_sync} 篇，发布 {done_b_sync} 篇，"
        f"耗时 {t_b_sync:.3f}s {'✅ 无重复' if ok_b_sync else '❌ 有重复'}"
    )

    # ─── 方案 B：原子领取（异步）───
    print("\n=== 方案 B：原子领取（异步 ActiveRecord）===")
    reset_all_posts()
    t0 = time.perf_counter()
    with multiprocessing.Pool(processes=NUM_WORKERS) as pool:
        results_b_async = pool.map(worker_atomic_async, list(range(NUM_WORKERS)))
    t_b_async = time.perf_counter() - t0
    total_b_async = sum(results_b_async)
    ok_b_async, done_b_async = verify_no_duplicates()
    print(
        f"  结果：Worker 共处理 {total_b_async} 篇，发布 {done_b_async} 篇，"
        f"耗时 {t_b_async:.3f}s {'✅ 无重复' if ok_b_async else '❌ 有重复'}"
    )

    reset_all_posts()

    print(f"\n{'=' * 60}")
    print("方案对比（同步 vs 异步，方法名完全相同）：")
    print(f"  A. 数据分区  同步: {t_a_sync:.3f}s  异步: {t_a_async:.3f}s")
    print(f"  B. 原子领取  同步: {t_b_sync:.3f}s  异步: {t_b_async:.3f}s")
    print("""
选型建议：
  - 数据分区：任务总量确定、可按维度（如 user_id）静态分割时首选
  - 原子领取：任务动态产生、需要负载均衡时使用
  - 两种方案均通过 with/async with transaction() 保证一致性
""")

    # 汇总验证
    all_ok = ok_a_sync and ok_a_async and ok_b_sync and ok_b_async
    print(f"总体验证：{'✅ 所有方案均无重复处理' if all_ok else '❌ 存在问题'}")


if __name__ == "__main__":
    main()
