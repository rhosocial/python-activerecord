# src/rhosocial/activerecord/testsuite/feature/relation/fixtures/models.py
"""
Relation model fixtures for the testsuite.

This module provides model classes for testing relation features:
- Employee/Department: Basic BelongsTo/HasMany relations
- Author/Book/Chapter/Profile: Nested relations with HasOne
- User/Post/Comment: Relations with FieldProxy, DerivedField, and JSON fields
"""
from typing import Optional, ClassVar

from typing_extensions import Annotated

from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord
from rhosocial.activerecord.base import DerivedField, FieldProxy
from rhosocial.activerecord.backend.expression import Column, Literal
from rhosocial.activerecord.backend.expression.functions import (
    json_extract_text, length, coalesce
)
from rhosocial.activerecord.relation.descriptors import BelongsTo, HasMany, HasOne
from rhosocial.activerecord.relation.async_descriptors import AsyncBelongsTo, AsyncHasMany, AsyncHasOne


# ── Basic Relation Models ────────────────────────────────

class Employee(ActiveRecord):
    __table_name__ = "employees"

    id: Optional[int] = None
    username: str
    department_id: int

    department: ClassVar[BelongsTo["Department"]] = BelongsTo(
        foreign_key="department_id",
        inverse_of="employees"
    )


class Department(ActiveRecord):
    __table_name__ = "departments"

    id: Optional[int] = None
    name: str
    description: str = ""

    employees: ClassVar[HasMany["Employee"]] = HasMany(
        foreign_key="department_id",
        inverse_of="department"
    )


class Author(ActiveRecord):
    __table_name__ = "authors"

    id: Optional[int] = None
    name: str

    books: ClassVar[HasMany["Book"]] = HasMany(
        foreign_key="author_id",
        inverse_of="author"
    )
    profile: ClassVar[HasOne["Profile"]] = HasOne(
        foreign_key="author_id",
        inverse_of="author"
    )


class Book(ActiveRecord):
    __table_name__ = "books"

    id: Optional[int] = None
    title: str
    author_id: int

    author: ClassVar[BelongsTo["Author"]] = BelongsTo(
        foreign_key="author_id",
        inverse_of="books"
    )
    chapters: ClassVar[HasMany["Chapter"]] = HasMany(
        foreign_key="book_id",
        inverse_of="book"
    )


class Chapter(ActiveRecord):
    __table_name__ = "chapters"

    id: Optional[int] = None
    title: str
    book_id: int

    book: ClassVar[BelongsTo["Book"]] = BelongsTo(
        foreign_key="book_id",
        inverse_of="chapters"
    )


class Profile(ActiveRecord):
    __table_name__ = "profiles"

    id: Optional[int] = None
    bio: str
    author_id: int

    author: ClassVar[BelongsTo["Author"]] = BelongsTo(
        foreign_key="author_id",
        inverse_of="profile"
    )


# ── Advanced Relation Models (with FieldProxy, DerivedField, JSON) ──

class User(ActiveRecord):
    __table_name__ = "users"

    c: ClassVar[FieldProxy] = FieldProxy()
    id: Optional[int] = None
    name: str
    email: Optional[str] = None
    settings: Optional[str] = None  # JSON: {"language": "zh-CN", "theme": "dark"}

    # DerivedField: display name (coalesce email to name)
    display_name: ClassVar[Annotated[str, DerivedField(
        lambda d: coalesce(d, Column(d, "email"), Column(d, "name")),
    )]]

    # DerivedField (JSON): extract language preference
    language: ClassVar[Annotated[str, DerivedField(
        lambda d: json_extract_text(d, Column(d, "settings"), "$.language"),
    )]]

    # DerivedField (JSON): extract theme preference
    theme: ClassVar[Annotated[str, DerivedField(
        lambda d: json_extract_text(d, Column(d, "settings"), "$.theme"),
    )]]

    # Relation
    posts: ClassVar[HasMany["Post"]] = HasMany(
        foreign_key="user_id",
        inverse_of="user"
    )


class Post(ActiveRecord):
    __table_name__ = "posts"

    c: ClassVar[FieldProxy] = FieldProxy()
    id: Optional[int] = None
    title: str
    body: str
    user_id: int
    view_count: int = 0
    metadata: Optional[str] = None  # JSON: {"tags": ["python", "orm"], "source": "blog"}

    # DerivedField: title length using FieldProxy
    title_length: ClassVar[Annotated[int, DerivedField(
        lambda d: length(d, Post.c.title),
    )]]

    # DerivedField: hotness score
    hotness: ClassVar[Annotated[int, DerivedField(
        lambda d: Column(d, "view_count") + Literal(d, 1),
    )]]

    # DerivedField (JSON): first tag from metadata
    first_tag: ClassVar[Annotated[str, DerivedField(
        lambda d: json_extract_text(d, Column(d, "metadata"), "$.tags[0]"),
    )]]

    # DerivedField (JSON): source from metadata
    source: ClassVar[Annotated[str, DerivedField(
        lambda d: json_extract_text(d, Column(d, "metadata"), "$.source"),
    )]]

    # Relations
    user: ClassVar[BelongsTo["User"]] = BelongsTo(
        foreign_key="user_id",
        inverse_of="posts"
    )
    comments: ClassVar[HasMany["Comment"]] = HasMany(
        foreign_key="post_id",
        inverse_of="post"
    )


class Comment(ActiveRecord):
    __table_name__ = "comments"

    c: ClassVar[FieldProxy] = FieldProxy()
    id: Optional[int] = None
    body: str
    post_id: int
    meta: Optional[str] = None  # JSON: {"platform": "web", "device": "mobile"}

    # DerivedField: body length using FieldProxy
    body_length: ClassVar[Annotated[int, DerivedField(
        lambda d: length(d, Comment.c.body),
    )]]

    # DerivedField (JSON): platform from meta
    platform: ClassVar[Annotated[str, DerivedField(
        lambda d: json_extract_text(d, Column(d, "meta"), "$.platform"),
    )]]

    # Relation
    post: ClassVar[BelongsTo["Post"]] = BelongsTo(
        foreign_key="post_id",
        inverse_of="comments"
    )


# ── Async Models ─────────────────────────────────────────

class AsyncUser(AsyncActiveRecord):
    __table_name__ = "users"

    c: ClassVar[FieldProxy] = FieldProxy()
    id: Optional[int] = None
    name: str
    email: Optional[str] = None
    settings: Optional[str] = None

    display_name: ClassVar[Annotated[str, DerivedField(
        lambda d: coalesce(d, Column(d, "email"), Column(d, "name")),
    )]]

    language: ClassVar[Annotated[str, DerivedField(
        lambda d: json_extract_text(d, Column(d, "settings"), "$.language"),
    )]]

    theme: ClassVar[Annotated[str, DerivedField(
        lambda d: json_extract_text(d, Column(d, "settings"), "$.theme"),
    )]]

    posts: ClassVar[AsyncHasMany["AsyncPost"]] = AsyncHasMany(
        foreign_key="user_id",
        inverse_of="user"
    )


class AsyncPost(AsyncActiveRecord):
    __table_name__ = "posts"

    c: ClassVar[FieldProxy] = FieldProxy()
    id: Optional[int] = None
    title: str
    body: str
    user_id: int
    view_count: int = 0
    metadata: Optional[str] = None

    title_length: ClassVar[Annotated[int, DerivedField(
        lambda d: length(d, AsyncPost.c.title),
    )]]

    hotness: ClassVar[Annotated[int, DerivedField(
        lambda d: Column(d, "view_count") + Literal(d, 1),
    )]]

    first_tag: ClassVar[Annotated[str, DerivedField(
        lambda d: json_extract_text(d, Column(d, "metadata"), "$.tags[0]"),
    )]]

    source: ClassVar[Annotated[str, DerivedField(
        lambda d: json_extract_text(d, Column(d, "metadata"), "$.source"),
    )]]

    user: ClassVar[AsyncBelongsTo["AsyncUser"]] = AsyncBelongsTo(
        foreign_key="user_id",
        inverse_of="posts"
    )
    comments: ClassVar[AsyncHasMany["AsyncComment"]] = AsyncHasMany(
        foreign_key="post_id",
        inverse_of="post"
    )


class AsyncComment(AsyncActiveRecord):
    __table_name__ = "comments"

    c: ClassVar[FieldProxy] = FieldProxy()
    id: Optional[int] = None
    body: str
    post_id: int
    meta: Optional[str] = None

    body_length: ClassVar[Annotated[int, DerivedField(
        lambda d: length(d, AsyncComment.c.body),
    )]]

    platform: ClassVar[Annotated[str, DerivedField(
        lambda d: json_extract_text(d, Column(d, "meta"), "$.platform"),
    )]]

    post: ClassVar[AsyncBelongsTo["AsyncPost"]] = AsyncBelongsTo(
        foreign_key="post_id",
        inverse_of="comments"
    )


# ── Relation Boundary Models ──────────────────────────────

class BoundaryOwner(ActiveRecord):
    __table_name__ = "relation_boundary_owners"

    id: Optional[int] = None
    name: str

    profile: ClassVar[HasOne["BoundaryProfile"]] = HasOne(
        foreign_key="owner_id",
        inverse_of="owner"
    )
    posts: ClassVar[HasMany["BoundaryPost"]] = HasMany(
        foreign_key="owner_id",
        inverse_of="owner"
    )


class BoundaryProfile(ActiveRecord):
    __table_name__ = "relation_boundary_profiles"

    id: Optional[int] = None
    bio: str
    owner_id: Optional[int] = None

    owner: ClassVar[BelongsTo["BoundaryOwner"]] = BelongsTo(
        foreign_key="owner_id",
        inverse_of="profile"
    )


class BoundaryPost(ActiveRecord):
    __table_name__ = "relation_boundary_posts"

    id: Optional[int] = None
    title: str
    owner_id: Optional[int] = None

    owner: ClassVar[BelongsTo["BoundaryOwner"]] = BelongsTo(
        foreign_key="owner_id",
        inverse_of="posts"
    )


class AsyncBoundaryOwner(AsyncActiveRecord):
    __table_name__ = "relation_boundary_owners"

    id: Optional[int] = None
    name: str

    profile: ClassVar[AsyncHasOne["AsyncBoundaryProfile"]] = AsyncHasOne(
        foreign_key="owner_id",
        inverse_of="owner"
    )
    posts: ClassVar[AsyncHasMany["AsyncBoundaryPost"]] = AsyncHasMany(
        foreign_key="owner_id",
        inverse_of="owner"
    )


class AsyncBoundaryProfile(AsyncActiveRecord):
    __table_name__ = "relation_boundary_profiles"

    id: Optional[int] = None
    bio: str
    owner_id: Optional[int] = None

    owner: ClassVar[AsyncBelongsTo["AsyncBoundaryOwner"]] = AsyncBelongsTo(
        foreign_key="owner_id",
        inverse_of="profile"
    )


class AsyncBoundaryPost(AsyncActiveRecord):
    __table_name__ = "relation_boundary_posts"

    id: Optional[int] = None
    title: str
    owner_id: Optional[int] = None

    owner: ClassVar[AsyncBelongsTo["AsyncBoundaryOwner"]] = AsyncBelongsTo(
        foreign_key="owner_id",
        inverse_of="posts"
    )
