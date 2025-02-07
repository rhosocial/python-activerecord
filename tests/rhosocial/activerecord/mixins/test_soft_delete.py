from datetime import datetime

import tzlocal

from .fixtures.models import task

def test_soft_delete_basic(task):
    """测试软删除基本功能"""
    # 创建新记录
    t = task(title="Test Task")
    t.save()

    # 验证初始状态
    assert t.deleted_at is None

    # 记录删除前时间
    before_delete = datetime.now(tzlocal.get_localzone())

    # 执行软删除
    t.delete()

    # 记录删除后时间
    after_delete = datetime.now(tzlocal.get_localzone())

    # 验证删除时间已正确设置
    assert t.deleted_at is not None
    assert isinstance(t.deleted_at, datetime)
    assert before_delete <= t.deleted_at <= after_delete

    # 验证数据库记录的一致性
    db_task = task.query_with_deleted().where(f"{task.primary_key()} = ?", (t.id,)).one()
    assert db_task is not None
    assert db_task.deleted_at == t.deleted_at


def test_soft_delete_query(task):
    """测试软删除查询功能"""
    # 创建测试数据
    t1 = task(title="Task 1")
    t1.save()
    t2 = (task(title="Task 2"))
    t2.save()
    t3 = task(title="Task 3")
    t3.save()

    # 删除其中一个记录
    t2.delete()

    # 测试普通查询（应该只能看到未删除的记录）
    active_tasks = task.find_all()
    assert len(active_tasks) == 2
    assert all(t.deleted_at is None for t in active_tasks)

    # 测试包含已删除记录的查询
    all_tasks = task.query_with_deleted().all()
    assert len(all_tasks) == 3

    # 测试只查询已删除记录
    deleted_tasks = task.query_only_deleted().all()
    assert len(deleted_tasks) == 1
    assert deleted_tasks[0].id == t2.id


def test_soft_delete_restore(task):
    """测试恢复已删除记录"""
    # 创建并删除记录
    t = task(title="Test Task")
    t.save()
    t.delete()

    # 确认记录已被软删除
    assert t.deleted_at is not None
    assert task.find_one(t.id) is None

    # 恢复记录
    t.restore()

    # 验证恢复结果
    assert t.deleted_at is None
    restored_task = task.find_one(t.id)
    assert restored_task is not None
    assert restored_task.deleted_at is None


def test_soft_delete_identity(task):
    """测试软删除后记录身份的保持"""
    t = task(title="Test Task")
    t.save()
    original_id = t.id

    # 执行软删除
    t.delete()

    # 验证主键没有被清空
    assert t.id == original_id

    # 验证可以通过主键查询到已删除的记录
    found = task.query_with_deleted().where(f"{task.primary_key()} = ?", (original_id,)).one()
    assert found is not None
    assert found.id == original_id

    # 验证可以恢复删除
    t.restore()
    assert t.id == original_id  # 主键始终保持不变