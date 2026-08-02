# src/rhosocial/activerecord/testsuite/feature/mixins/fixtures/models.py
"""
This file defines the generic ActiveRecord model classes used by the mixins tests.

These models are "generic" because they define the data structure and validation
rules (using Pydantic), but they are not tied to any specific database backend.
The backend-specific provider is responsible for taking these classes and
configuring them with a live database connection at test time.
"""
from typing import Optional
from datetime import datetime

from pydantic import Field

from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin, TimestampMixin, OptimisticLockMixin, SoftDeleteMixin, AsyncSoftDeleteMixin


class TimestampedPost(IntegerPKMixin, TimestampMixin, ActiveRecord):
    """Blog post model with timestamps"""
    __table_name__ = "timestamped_posts"

    id: Optional[int] = None
    title: str
    content: str


class VersionedProduct(IntegerPKMixin, OptimisticLockMixin, ActiveRecord):
    """Product model with optimistic locking"""
    __table_name__ = "versioned_products"

    id: Optional[int] = None
    name: str
    price: float = Field(default=0.0)


class Task(IntegerPKMixin, SoftDeleteMixin, ActiveRecord):
    """Task model supporting soft deletion"""
    __table_name__ = "tasks"

    id: Optional[int] = None
    title: str
    is_completed: bool = Field(default=False)


class CombinedArticle(IntegerPKMixin, TimestampMixin, OptimisticLockMixin, SoftDeleteMixin, ActiveRecord):
    """Article model combining all mixins"""
    __table_name__ = "combined_articles"

    id: Optional[int] = None
    title: str
    content: str
    status: str = Field(default="draft")


class AsyncTimestampedPost(IntegerPKMixin, TimestampMixin, AsyncActiveRecord):
    """Blog post model with timestamps (async version)"""
    __table_name__ = "timestamped_posts"

    id: Optional[int] = None
    title: str
    content: str


class AsyncVersionedProduct(IntegerPKMixin, OptimisticLockMixin, AsyncActiveRecord):
    """Product model with optimistic locking (async version)"""
    __table_name__ = "versioned_products"

    id: Optional[int] = None
    name: str
    price: float = Field(default=0.0)


class AsyncTask(IntegerPKMixin, AsyncSoftDeleteMixin, AsyncActiveRecord):
    """Task model supporting soft deletion (async version)"""
    __table_name__ = "tasks"

    id: Optional[int] = None
    title: str
    is_completed: bool = Field(default=False)


class AsyncCombinedArticle(IntegerPKMixin, TimestampMixin, OptimisticLockMixin, AsyncSoftDeleteMixin, AsyncActiveRecord):
    """Article model combining all mixins (async version)"""
    __table_name__ = "combined_articles"

    id: Optional[int] = None
    title: str
    content: str
    status: str = Field(default="draft")
