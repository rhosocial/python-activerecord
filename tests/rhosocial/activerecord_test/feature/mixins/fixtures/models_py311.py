# src/rhosocial/activerecord/testsuite/feature/mixins/fixtures/models_py311.py
"""
Python 3.11+ fixture model definitions for mixins tests.

This file contains model classes using Python 3.11+ syntax features:
- `Self` type for methods that return an instance of the same class
- `X | Y` syntax (inherited from 3.10+)

Note: This file should only be imported and used in Python 3.11+ environments.
"""
from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import Field

from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin, TimestampMixin, OptimisticLockMixin, SoftDeleteMixin


# Declare that this module requires Python 3.11+
__requires_python__ = (3, 11)


class TimestampedPost(IntegerPKMixin, TimestampMixin, ActiveRecord):
    """Blog post model with timestamps.

    Python 3.11+ version using | syntax and Self type.
    """
    __table_name__ = "timestamped_posts"

    id: int | None = None
    title: str
    content: str

    def update_content(self, new_content: str) -> Self:
        """Update content and return self for chaining."""
        self.content = new_content
        return self


class VersionedProduct(IntegerPKMixin, OptimisticLockMixin, ActiveRecord):
    """Product model with optimistic locking.

    Python 3.11+ version using | syntax and Self type.
    """
    __table_name__ = "versioned_products"

    id: int | None = None
    name: str
    price: float = Field(default=0.0)

    def set_price(self, new_price: float) -> Self:
        """Set price and return self for chaining."""
        self.price = new_price
        return self


class Task(IntegerPKMixin, SoftDeleteMixin, ActiveRecord):
    """Task model supporting soft deletion.

    Python 3.11+ version using | syntax and Self type.
    """
    __table_name__ = "tasks"

    id: int | None = None
    title: str
    is_completed: bool = Field(default=False)

    def complete(self) -> Self:
        """Mark task as completed and return self for chaining."""
        self.is_completed = True
        return self

    def uncomplete(self) -> Self:
        """Mark task as not completed and return self for chaining."""
        self.is_completed = False
        return self


class CombinedArticle(IntegerPKMixin, TimestampMixin, OptimisticLockMixin, SoftDeleteMixin, ActiveRecord):
    """Article model combining all mixins.

    Python 3.11+ version using | syntax and Self type.
    """
    __table_name__ = "combined_articles"

    id: int | None = None
    title: str
    content: str
    status: str = Field(default="draft")

    def publish(self) -> Self:
        """Publish article and return self for chaining."""
        self.status = "published"
        return self

    def archive(self) -> Self:
        """Archive article and return self for chaining."""
        self.status = "archived"
        return self
