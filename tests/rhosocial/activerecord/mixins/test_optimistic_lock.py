import pytest

from src.rhosocial.activerecord.backend.errors import DatabaseError
from .fixtures.models import versioned_product


def test_optimistic_lock(versioned_product):
    """测试乐观锁功能"""
    # 创建新记录
    product = versioned_product(name="Test Product", price=10.0)
    product.save()

    # 验证初始版本号
    assert product.version == 1

    # 更新记录
    product.price = 15.0
    product.save()

    # 验证版本号增加
    assert product.version == 2

    # 模拟并发更新冲突
    product_conflict = versioned_product.find_one(product.id)
    product_conflict.price = 20.0
    product_conflict.save()  # 此更新成功，版本号变为3

    # 原始记录再次更新应该失败
    product.price = 25.0  # 此时 product.version 仍为 2
    with pytest.raises(DatabaseError, match="Record was updated by another process"):
        product.save()

    # 验证最终版本
    latest_product = versioned_product.find_one(product.id)
    assert latest_product.version == 3
    assert latest_product.price == 20.0


def test_version_increment(versioned_product):
    """测试版本号正确递增"""
    # 创建新记录
    product = versioned_product(name="Test Product", price=10.0)
    product.save()

    # 验证初始版本号
    assert product.version == 1

    # 第一次更新
    product.price = 15.0
    product.save()
    assert product.version == 2

    # 第二次更新
    product.price = 20.0
    product.save()
    assert product.version == 3

    # 验证数据库中的版本号
    db_product = versioned_product.find_one(product.id)
    assert db_product.version == 3