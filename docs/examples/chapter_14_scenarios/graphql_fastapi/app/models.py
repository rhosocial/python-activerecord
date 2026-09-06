# docs/examples/chapter_14_scenarios/graphql_fastapi/app/models.py
"""GraphQL 演示：AsyncActiveRecord 模型 + 推导 DDL。

与 FastAPI 场景相同的现代写法：
- 异步模型 (AsyncActiveRecord)，配合 Graphene 的 async resolver 直接 await
- UseSqlType 显式声明 SQL 列类型，generate_create_table() 推导建表
"""
import uuid
from typing import Annotated, ClassVar

from rhosocial.activerecord.base import FieldProxy, UseSqlType
from rhosocial.activerecord.backend.expression.types import TextType, VarCharType
from rhosocial.activerecord.field import DefaultTimestampMixin, UUIDMixin
from rhosocial.activerecord.model import AsyncActiveRecord
from rhosocial.activerecord.relation import AsyncBelongsTo, AsyncHasMany


class User(UUIDMixin, DefaultTimestampMixin, AsyncActiveRecord):
    """用户。"""

    __table_name__ = "users"

    username: Annotated[str, UseSqlType(VarCharType(length=50))]
    email: Annotated[str, UseSqlType(VarCharType(length=120))]

    c: ClassVar[FieldProxy] = FieldProxy()

    posts: ClassVar[AsyncHasMany["Post"]] = AsyncHasMany(foreign_key="user_id", inverse_of="user")
    comments: ClassVar[AsyncHasMany["Comment"]] = AsyncHasMany(foreign_key="user_id", inverse_of="user")


class Post(UUIDMixin, DefaultTimestampMixin, AsyncActiveRecord):
    """文章。"""

    __table_name__ = "posts"

    user_id: uuid.UUID
    title: Annotated[str, UseSqlType(VarCharType(length=200))]
    content: Annotated[str, UseSqlType(TextType())]

    c: ClassVar[FieldProxy] = FieldProxy()

    user: ClassVar[AsyncBelongsTo["User"]] = AsyncBelongsTo(foreign_key="user_id", inverse_of="posts")
    comments: ClassVar[AsyncHasMany["Comment"]] = AsyncHasMany(foreign_key="post_id", inverse_of="post")


class Comment(UUIDMixin, DefaultTimestampMixin, AsyncActiveRecord):
    """评论。"""

    __table_name__ = "comments"

    user_id: uuid.UUID
    post_id: uuid.UUID
    content: Annotated[str, UseSqlType(TextType())]

    c: ClassVar[FieldProxy] = FieldProxy()

    user: ClassVar[AsyncBelongsTo["User"]] = AsyncBelongsTo(foreign_key="user_id", inverse_of="comments")
    post: ClassVar[AsyncBelongsTo["Post"]] = AsyncBelongsTo(foreign_key="post_id", inverse_of="comments")