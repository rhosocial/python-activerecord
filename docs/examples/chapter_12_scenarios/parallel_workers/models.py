# models.py - 并行 Worker 实验的共享模型定义
# docs/examples/chapter_12_scenarios/parallel_workers/models.py
"""
模型体系：
    User  --(has_many)--> Post  --(has_many)--> Comment
    User  <--(belongs_to)-- Post
    Post  <--(belongs_to)-- Comment
    User  <--(belongs_to)-- Comment （直接引用作者）

每个模型同时提供同步版（继承 ActiveRecord）和异步版（继承 AsyncActiveRecord），
方法名完全相同，异步版仅需加 await。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import ClassVar, Optional

from rhosocial.activerecord.base.field_proxy import FieldProxy
from rhosocial.activerecord.field import IntegerPKMixin, TimestampMixin
from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord
from rhosocial.activerecord.relation import BelongsTo, HasMany
from rhosocial.activerecord.relation.async_descriptors import (
    AsyncBelongsTo,
    AsyncHasMany,
)


# ─────────────────────────────────────────
# 同步模型
# ─────────────────────────────────────────


class User(IntegerPKMixin, TimestampMixin, ActiveRecord):
    """博客用户（同步）"""

    __table_name__ = "users"

    id: Optional[int] = None
    username: str
    email: str
    is_active: bool = True

    c: ClassVar[FieldProxy] = FieldProxy()

    # 关联：一个用户有多篇文章、多条评论
    posts: ClassVar[HasMany[Post]] = HasMany(foreign_key="user_id", inverse_of="author")
    comments: ClassVar[HasMany[Comment]] = HasMany(foreign_key="user_id", inverse_of="author")


class Post(IntegerPKMixin, TimestampMixin, ActiveRecord):
    """博客文章（同步）"""

    __table_name__ = "posts"

    id: Optional[int] = None
    user_id: int
    title: str
    body: str
    status: str = "draft"  # draft / published / archived
    view_count: int = 0

    c: ClassVar[FieldProxy] = FieldProxy()

    # 关联：文章属于一个用户，有多条评论
    author: ClassVar[BelongsTo[User]] = BelongsTo(foreign_key="user_id", inverse_of="posts")
    comments: ClassVar[HasMany[Comment]] = HasMany(foreign_key="post_id", inverse_of="post")


class Comment(IntegerPKMixin, TimestampMixin, ActiveRecord):
    """评论（同步）"""

    __table_name__ = "comments"

    id: Optional[int] = None
    post_id: int
    user_id: int
    body: str
    is_approved: bool = False

    c: ClassVar[FieldProxy] = FieldProxy()

    # 关联：评论属于一篇文章和一个用户
    post: ClassVar[BelongsTo[Post]] = BelongsTo(foreign_key="post_id", inverse_of="comments")
    author: ClassVar[BelongsTo[User]] = BelongsTo(foreign_key="user_id", inverse_of="comments")


# ─────────────────────────────────────────
# 异步模型（与同步版方法名完全相同，操作加 await）
# ─────────────────────────────────────────


class AsyncUser(IntegerPKMixin, TimestampMixin, AsyncActiveRecord):
    """博客用户（异步）"""

    __table_name__ = "users"

    id: Optional[int] = None
    username: str
    email: str
    is_active: bool = True

    c: ClassVar[FieldProxy] = FieldProxy()

    posts: ClassVar[AsyncHasMany[AsyncPost]] = AsyncHasMany(foreign_key="user_id", inverse_of="author")
    comments: ClassVar[AsyncHasMany[AsyncComment]] = AsyncHasMany(foreign_key="user_id", inverse_of="author")


class AsyncPost(IntegerPKMixin, TimestampMixin, AsyncActiveRecord):
    """博客文章（异步）"""

    __table_name__ = "posts"

    id: Optional[int] = None
    user_id: int
    title: str
    body: str
    status: str = "draft"
    view_count: int = 0

    c: ClassVar[FieldProxy] = FieldProxy()

    author: ClassVar[AsyncBelongsTo[AsyncUser]] = AsyncBelongsTo(foreign_key="user_id", inverse_of="posts")
    comments: ClassVar[AsyncHasMany[AsyncComment]] = AsyncHasMany(foreign_key="post_id", inverse_of="post")


class AsyncComment(IntegerPKMixin, TimestampMixin, AsyncActiveRecord):
    """评论（异步）"""

    __table_name__ = "comments"

    id: Optional[int] = None
    post_id: int
    user_id: int
    body: str
    is_approved: bool = False

    c: ClassVar[FieldProxy] = FieldProxy()

    post: ClassVar[AsyncBelongsTo[AsyncPost]] = AsyncBelongsTo(foreign_key="post_id", inverse_of="comments")
    author: ClassVar[AsyncBelongsTo[AsyncUser]] = AsyncBelongsTo(foreign_key="user_id", inverse_of="comments")


# ─────────────────────────────────────────
# 建表 DDL（SQLite）
# ─────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username   TEXT    NOT NULL UNIQUE,
    email      TEXT    NOT NULL,
    is_active  INTEGER NOT NULL DEFAULT 1,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS posts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    title      TEXT    NOT NULL,
    body       TEXT    NOT NULL DEFAULT '',
    status     TEXT    NOT NULL DEFAULT 'draft',
    view_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS comments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id     INTEGER NOT NULL REFERENCES posts(id),
    user_id     INTEGER NOT NULL REFERENCES users(id),
    body        TEXT    NOT NULL,
    is_approved INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT,
    updated_at  TEXT
);
"""


def now_utc() -> datetime:
    """返回当前 UTC 时间（naive datetime，SQLite 友好）"""
    return datetime.now(timezone.utc).replace(tzinfo=None)
