# tests/rhosocial/activerecord_test/mixins/fixtures/models.py
from typing import Optional

from pydantic import Field

from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import OptimisticLockMixin, SoftDeleteMixin, TimestampMixin, IntegerPKMixin
from ...utils import create_active_record_fixture


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


# Create test fixtures
timestamped_post = create_active_record_fixture(TimestampedPost)
versioned_product = create_active_record_fixture(VersionedProduct)
task = create_active_record_fixture(Task)
combined_article = create_active_record_fixture(CombinedArticle)
