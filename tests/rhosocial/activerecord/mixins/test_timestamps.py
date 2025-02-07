import time
from datetime import datetime

from .fixtures.models import timestamped_post


def test_timestamps(timestamped_post):
    """测试时间戳功能"""
    # 创建新记录
    post = timestamped_post(title="Test Post", content="Test Content")
    post.save()

    # 验证时间戳存在且类型正确
    assert post.created_at is not None
    assert post.updated_at is not None
    assert isinstance(post.created_at, datetime)
    assert isinstance(post.updated_at, datetime)

    # 记录初始时间
    original_created_at = post.created_at
    original_updated_at = post.updated_at

    # 等待一点时间后更新记录
    post.title = "Updated Title"
    time.sleep(0.1)
    post.save()

    # 验证时间戳更新情况
    assert post.created_at == original_created_at  # 创建时间不变
    assert post.updated_at > original_updated_at  # 更新时间变化
