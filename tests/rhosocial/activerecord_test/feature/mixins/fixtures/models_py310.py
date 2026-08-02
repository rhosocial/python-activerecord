# src/rhosocial/activerecord/testsuite/feature/mixins/fixtures/models_py310.py
"""
Python 3.10+ fixture model definitions for mixins tests.

This file contains model classes using Python 3.10+ syntax features:
- `X | Y` syntax instead of `Optional[X]` or `Union[X, Y]`
- `Type | None` instead of `Optional[Type]`

Note: This file should only be imported and used in Python 3.10+ environments.
"""
from datetime import datetime

from pydantic import Field

from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin, TimestampMixin, OptimisticLockMixin, SoftDeleteMixin


# Declare that this module requires Python 3.10+
__requires_python__ = (3, 10)


class TimestampedPost(IntegerPKMixin, TimestampMixin, ActiveRecord):
    """Blog post model with timestamps.

    Python 3.10+ version using | syntax instead of Optional.
    """
    __table_name__ = "timestamped_posts"

    id: int | None = None
    title: str
    content: str


class VersionedProduct(IntegerPKMixin, OptimisticLockMixin, ActiveRecord):
    """Product model with optimistic locking.

    Python 3.10+ version using | syntax instead of Optional.
    """
    __table_name__ = "versioned_products"

    id: int | None = None
    name: str
    price: float = Field(default=0.0)


class Task(IntegerPKMixin, SoftDeleteMixin, ActiveRecord):
    """Task model supporting soft deletion.

    Python 3.10+ version using | syntax instead of Optional.
    """
    __table_name__ = "tasks"

    id: int | None = None
    title: str
    is_completed: bool = Field(default=False)


class CombinedArticle(IntegerPKMixin, TimestampMixin, OptimisticLockMixin, SoftDeleteMixin, ActiveRecord):
    """Article model combining all mixins.

    Python 3.10+ version using | syntax instead of Optional.
    """
    __table_name__ = "combined_articles"

    id: int | None = None
    title: str
    content: str
    status: str = Field(default="draft")
