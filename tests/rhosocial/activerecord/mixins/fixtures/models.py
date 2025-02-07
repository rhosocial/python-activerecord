from typing import Optional

from pydantic import Field

from src.rhosocial.activerecord import ActiveRecord
from src.rhosocial.activerecord.field import OptimisticLockMixin, SoftDeleteMixin, TimestampMixin, IntegerPKMixin
from tests.rhosocial.activerecord.utils import create_active_record_fixture


class TimestampedPost(IntegerPKMixin, TimestampMixin, ActiveRecord):
    """带时间戳的博文模型"""
    __table_name__ = "timestamped_posts"

    id: Optional[int] = None
    title: str
    content: str


class VersionedProduct(IntegerPKMixin, OptimisticLockMixin, ActiveRecord):
    """带乐观锁的产品模型"""
    __table_name__ = "versioned_products"

    id: Optional[int] = None
    name: str
    price: float = Field(default=0.0)


class Task(IntegerPKMixin, SoftDeleteMixin, ActiveRecord):
    """支持软删除的任务模型"""
    __table_name__ = "tasks"

    id: Optional[int] = None
    title: str
    is_completed: bool = Field(default=False)


class CombinedArticle(IntegerPKMixin, TimestampMixin, OptimisticLockMixin, SoftDeleteMixin, ActiveRecord):
    """综合使用所有混入的文章模型"""
    __table_name__ = "combined_articles"

    id: Optional[int] = None
    title: str
    content: str
    status: str = Field(default="draft")


# 创建测试夹具
timestamped_post = create_active_record_fixture(TimestampedPost)
versioned_product = create_active_record_fixture(VersionedProduct)
task = create_active_record_fixture(Task)
combined_article = create_active_record_fixture(CombinedArticle)