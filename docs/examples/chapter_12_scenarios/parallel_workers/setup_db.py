# setup_db.py - 数据库初始化脚本
# docs/examples/chapter_12_scenarios/parallel_workers/setup_db.py
"""
初始化实验数据库 parallel_workers.db。

同时提供同步版和异步版初始化，两者建出相同的 schema 和测试数据：
    5  个用户
    20 篇文章（每用户 4 篇）
    60 条评论（每篇文章 3 条）

运行方式：
    python setup_db.py          # 同步初始化（默认）
    python setup_db.py --async  # 异步初始化
"""

from __future__ import annotations

import asyncio
import os
import sys

# 将项目 src 目录加入 sys.path
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

from models import (  # noqa: E402
    SCHEMA_SQL,
    AsyncComment,
    AsyncPost,
    AsyncUser,
    Comment,
    Post,
    User,
)

DB_PATH = "parallel_workers.db"
NUM_USERS = 5
POSTS_PER_USER = 4
COMMENTS_PER_POST = 3


def make_config(path: str = DB_PATH) -> SQLiteConnectionConfig:
    return SQLiteConnectionConfig(
        database=path,
        pragmas={"journal_mode": "WAL", "foreign_keys": "ON"},
    )


# ─────────────────────────────────────────
# 同步初始化
# ─────────────────────────────────────────


def init_sync(path: str = DB_PATH) -> None:
    """同步版：建表 + 插入测试数据"""
    config = make_config(path)
    User.configure(config, SQLiteBackend)
    # 所有模型共用同一个 backend 实例（同一连接）
    backend = User.backend()
    Post.__backend__ = backend
    Comment.__backend__ = backend

    # 建表（DROP + CREATE）
    backend.executescript(
        "DROP TABLE IF EXISTS comments;\nDROP TABLE IF EXISTS posts;\nDROP TABLE IF EXISTS users;\n" + SCHEMA_SQL
    )

    print("建表完成，开始插入测试数据…")

    # 插入用户
    users: list[User] = []
    for i in range(1, NUM_USERS + 1):
        u = User(username=f"user{i:02d}", email=f"user{i:02d}@example.com")
        u.save()
        users.append(u)
        print(f"  User #{u.id}: {u.username}")

    # 插入文章
    posts: list[Post] = []
    for u in users:
        for j in range(1, POSTS_PER_USER + 1):
            p = Post(
                user_id=u.id,  # type: ignore[arg-type]
                title=f"{u.username} 的第 {j} 篇文章",
                body=f"这是 {u.username} 写的第 {j} 篇文章的正文。",
                status="published" if j % 2 == 0 else "draft",
            )
            p.save()
            posts.append(p)

    print(f"  共插入 {len(posts)} 篇文章")

    # 插入评论
    comment_count = 0
    for post in posts:
        for k in range(1, COMMENTS_PER_POST + 1):
            commenter = users[(post.user_id + k - 1) % NUM_USERS]  # type: ignore[index]
            c = Comment(
                post_id=post.id,  # type: ignore[arg-type]
                user_id=commenter.id,  # type: ignore[arg-type]
                body=f"这是对《{post.title}》的第 {k} 条评论。",
                is_approved=(k % 2 == 1),
            )
            c.save()
            comment_count += 1

    print(f"  共插入 {comment_count} 条评论")
    print(f"\n✓ 同步初始化完成：{path}")
    print(f"  用户 {NUM_USERS} / 文章 {len(posts)} / 评论 {comment_count}")


# ─────────────────────────────────────────
# 异步初始化
# ─────────────────────────────────────────


async def init_async(path: str = DB_PATH) -> None:
    """异步版：建表 + 插入测试数据（方法名与同步版相同，加 await）"""
    config = make_config(path)
    await AsyncUser.configure(config, AsyncSQLiteBackend)
    backend = AsyncUser.backend()
    AsyncPost.__backend__ = backend
    AsyncComment.__backend__ = backend

    await backend.executescript(
        "DROP TABLE IF EXISTS comments;\nDROP TABLE IF EXISTS posts;\nDROP TABLE IF EXISTS users;\n" + SCHEMA_SQL
    )

    print("建表完成，开始插入测试数据（异步）…")

    users: list[AsyncUser] = []
    for i in range(1, NUM_USERS + 1):
        u = AsyncUser(username=f"user{i:02d}", email=f"user{i:02d}@example.com")
        await u.save()
        users.append(u)
        print(f"  User #{u.id}: {u.username}")

    posts: list[AsyncPost] = []
    for u in users:
        for j in range(1, POSTS_PER_USER + 1):
            p = AsyncPost(
                user_id=u.id,  # type: ignore[arg-type]
                title=f"{u.username} 的第 {j} 篇文章",
                body=f"这是 {u.username} 写的第 {j} 篇文章的正文。",
                status="published" if j % 2 == 0 else "draft",
            )
            await p.save()
            posts.append(p)

    print(f"  共插入 {len(posts)} 篇文章")

    comment_count = 0
    for post in posts:
        for k in range(1, COMMENTS_PER_POST + 1):
            commenter = users[(post.user_id + k - 1) % NUM_USERS]  # type: ignore[index]
            c = AsyncComment(
                post_id=post.id,  # type: ignore[arg-type]
                user_id=commenter.id,  # type: ignore[arg-type]
                body=f"这是对《{post.title}》的第 {k} 条评论。",
                is_approved=(k % 2 == 1),
            )
            await c.save()
            comment_count += 1

    print(f"  共插入 {comment_count} 条评论")
    print(f"\n✓ 异步初始化完成：{path}")
    print(f"  用户 {NUM_USERS} / 文章 {len(posts)} / 评论 {comment_count}")


# ─────────────────────────────────────────
# 入口
# ─────────────────────────────────────────


def main() -> None:
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"已删除旧数据库：{DB_PATH}")

    use_async = "--async" in sys.argv

    if use_async:
        print("=== 异步初始化模式 ===\n")
        asyncio.run(init_async())
    else:
        print("=== 同步初始化模式 ===\n")
        init_sync()

    print(
        "\n可运行以下实验：\n"
        "  python exp1_basic_multiprocess.py\n"
        "  python exp2_sqlite_wal_mode.py\n"
        "  python exp3_deadlock_wrong.py\n"
        "  python exp4_partition_correct.py\n"
        "  python exp5_multithread_warning.py\n"
    )


if __name__ == "__main__":
    main()
