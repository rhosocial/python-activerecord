import time

import pytest

from src.rhosocial.activerecord.backend.errors import DatabaseError
from .fixtures.models import combined_article


def test_combined_update(combined_article):
    """测试更新记录时的综合功能"""
    # 创建并更新文章
    article = combined_article(title="Test", content="Test")
    article.save()
    original_updated_at = article.updated_at

    article.content = "Updated content"
    article.status = "published"
    time.sleep(0.1)
    article.save()

    # 验证更新后的状态
    assert article.version == 2  # 版本号增加
    assert article.created_at == original_updated_at  # 创建时间不变
    assert article.updated_at > original_updated_at  # 更新时间变化


def test_combined_delete(combined_article):
    """测试删除记录时的综合功能"""
    # 创建并删除文章
    article = combined_article(title="Test", content="Test")
    article.save()
    article.delete()

    # 验证软删除状态
    assert article.deleted_at is not None
    assert combined_article.find_one(article.id) is None

    # 验证可以找到已删除的记录
    found_article = combined_article.query_with_deleted().where(
        f"{combined_article.primary_key()} = ?",
        (article.id,)
    ).one()
    assert found_article is not None
    assert found_article.deleted_at is not None
    assert found_article.version == 1


def test_combined_concurrent_update(combined_article):
    """测试并发更新时的综合功能"""
    # 创建文章
    article = combined_article(title="Test", content="Test")
    article.save()

    # 模拟并发更新
    concurrent_article = combined_article.query_with_deleted().where(
        f"{combined_article.primary_key()} = ?",
        (article.id,)
    ).one()

    # 第一次更新成功
    article.content = "Updated by first"
    article.save()

    # 第二次更新失败
    concurrent_article.content = "Updated by second"
    with pytest.raises(DatabaseError, match="Record was updated by another process"):
        concurrent_article.save()

    # 验证最终状态
    final_article = combined_article.find_one(article.id)
    assert final_article.content == "Updated by first"
    assert final_article.version == 2