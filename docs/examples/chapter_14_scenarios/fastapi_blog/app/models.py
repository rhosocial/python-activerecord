# docs/examples/chapter_14_scenarios/fastapi_blog/app/models.py
"""博客 API 的 ActiveRecord 模型。

使用异步模型 (AsyncActiveRecord) 以配合 FastAPI 的异步事件循环。
- UUIDMixin / DefaultTimestampMixin：内置字段混入
- UseSqlType：显式指定 SQL 列类型（推导 DDL 会据此生成 CREATE TABLE）
"""
import uuid
from typing import Annotated, ClassVar, Optional

from rhosocial.activerecord.base import FieldProxy, UseColumn, UseSqlType
from rhosocial.activerecord.backend.expression.types import (
    BooleanType,
    DateTimeType,
    IntegerType,
    TextType,
    VarCharType,
)
from rhosocial.activerecord.field import DefaultTimestampMixin, UUIDMixin
from rhosocial.activerecord.model import AsyncActiveRecord
from rhosocial.activerecord.relation import AsyncBelongsTo, AsyncHasMany


class User(UUIDMixin, DefaultTimestampMixin, AsyncActiveRecord):
    """用户模型。"""

    __table_name__ = "users"

    username: Annotated[str, UseSqlType(VarCharType(length=50))]
    email: Annotated[str, UseSqlType(VarCharType(length=120))]
    bio: Annotated[Optional[str], UseSqlType(TextType())] = None
    is_active: Annotated[bool, UseSqlType(BooleanType())] = True

    # 类型安全的查询代理
    c: ClassVar[FieldProxy] = FieldProxy()

    # 关系：一个用户有多篇文章
    posts: ClassVar[AsyncHasMany["Post"]] = AsyncHasMany(
        foreign_key="user_id", inverse_of="author"
    )


class Post(UUIDMixin, DefaultTimestampMixin, AsyncActiveRecord):
    """文章模型。"""

    __table_name__ = "posts"

    title: Annotated[str, UseSqlType(VarCharType(length=200))]
    content: Annotated[str, UseSqlType(TextType())]
    is_published: Annotated[bool, UseSqlType(BooleanType())] = False
    # UseColumn：Python 属性名 user_id 对应数据库列 user_id
    user_id: Annotated[uuid.UUID, UseColumn("user_id")]
    published_at: Annotated[Optional[object], UseSqlType(DateTimeType())] = None

    c: ClassVar[FieldProxy] = FieldProxy()

    # 关系：文章属于一个用户
    author: ClassVar[AsyncBelongsTo["User"]] = AsyncBelongsTo(
        foreign_key="user_id", inverse_of="posts"
    )