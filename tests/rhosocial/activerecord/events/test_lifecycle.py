import pytest
from src.rhosocial.activerecord.interface import ModelEvent

from .fixtures.models import event_test_model

def test_save_lifecycle_events(event_test_model):
    """测试保存生命周期事件"""
    instance = event_test_model(name="test")

    # 记录事件触发顺序
    event_sequence = []

    def on_before_validate(instance, **kwargs):
        event_sequence.append(("BEFORE_VALIDATE", instance.revision))

    def on_after_validate(instance, **kwargs):
        event_sequence.append(("AFTER_VALIDATE", instance.revision))

    def on_before_save(instance, **kwargs):
        event_sequence.append(("BEFORE_SAVE", instance.revision))
        instance.revision += 1

    def on_after_save(instance, **kwargs):
        event_sequence.append(("AFTER_SAVE", instance.revision))

    # 注册所有事件处理器
    instance.on(ModelEvent.BEFORE_VALIDATE, on_before_validate)
    instance.on(ModelEvent.AFTER_VALIDATE, on_after_validate)
    instance.on(ModelEvent.BEFORE_SAVE, on_before_save)
    instance.on(ModelEvent.AFTER_SAVE, on_after_save)

    # 保存记录
    instance.save()

    # 验证事件顺序
    expected_sequence = [
        ("BEFORE_VALIDATE", 1),
        ("AFTER_VALIDATE", 1),
        ("BEFORE_SAVE", 1),
        ("AFTER_SAVE", 2)
    ]
    assert event_sequence == expected_sequence


def test_delete_lifecycle_events(event_test_model):
    """测试删除生命周期事件"""
    instance = event_test_model(name="test")
    instance.save()

    event_sequence = []

    def on_before_delete(instance, **kwargs):
        event_sequence.append("BEFORE_DELETE")
        instance.status = "deleting"

    def on_after_delete(instance, **kwargs):
        event_sequence.append("AFTER_DELETE")

    # 注册删除事件处理器
    instance.on(ModelEvent.BEFORE_DELETE, on_before_delete)
    instance.on(ModelEvent.AFTER_DELETE, on_after_delete)

    # 删除记录
    instance.delete()

    # 验证事件顺序和状态变化
    assert event_sequence == ["BEFORE_DELETE", "AFTER_DELETE"]
    assert instance.status == "deleting"


def test_validation_lifecycle_events(event_test_model):
    """测试验证生命周期事件"""
    instance = event_test_model(name="test")

    validation_data = {}

    def on_before_validate(instance, **kwargs):
        validation_data["before"] = instance.name
        instance.name = instance.name.strip()

    def on_after_validate(instance, **kwargs):
        validation_data["after"] = instance.name

    # 注册验证事件处理器
    instance.on(ModelEvent.BEFORE_VALIDATE, on_before_validate)
    instance.on(ModelEvent.AFTER_VALIDATE, on_after_validate)

    # 使用带空格的名称创建实例并保存
    instance.name = " test_name "
    instance.save()

    # 验证名称在验证前后的变化
    assert validation_data["before"] == " test_name "
    assert validation_data["after"] == "test_name"
    assert instance.name == "test_name"


def test_nested_event_handling(event_test_model):
    """测试嵌套事件处理"""
    parent = event_test_model(name="parent")
    child = event_test_model(name="child")

    event_sequence = []

    def parent_save_handler(instance, **kwargs):
        event_sequence.append("parent_before_save")
        # 在父对象保存时保存子对象
        child.save()

    def child_save_handler(instance, **kwargs):
        event_sequence.append("child_before_save")

    # 注册事件处理器
    parent.on(ModelEvent.BEFORE_SAVE, parent_save_handler)
    child.on(ModelEvent.BEFORE_SAVE, child_save_handler)

    # 保存父对象
    parent.save()

    # 验证嵌套事件的执行顺序
    assert event_sequence == ["parent_before_save", "child_before_save"]


def test_event_error_handling(event_test_model):
    """测试事件错误处理"""
    instance = event_test_model(name="test")

    def error_handler(instance, **kwargs):
        raise ValueError("Test error in event handler")

    # 注册可能抛出错误的处理器
    instance.on(ModelEvent.BEFORE_SAVE, error_handler)

    # 验证错误正确传播
    with pytest.raises(ValueError) as exc_info:
        instance.save()
    assert "Test error in event handler" in str(exc_info.value)


def test_conditional_event_handling(event_test_model):
    """测试条件性事件处理"""
    instance = event_test_model(name="test", status="draft")
    handled_events = []

    def status_change_handler(instance, **kwargs):
        if instance.is_dirty and "status" in instance.dirty_fields:
            handled_events.append(("status_change", instance.status))

    def content_change_handler(instance, **kwargs):
        if instance.is_dirty and "content" in instance.dirty_fields:
            handled_events.append(("content_change", instance.content))

    # 注册条件处理器
    instance.on(ModelEvent.BEFORE_SAVE, status_change_handler)
    instance.on(ModelEvent.BEFORE_SAVE, content_change_handler)

    # 测试状态变更
    instance.status = "published"
    instance.save()

    # 测试内容变更
    instance.content = "new content"
    instance.save()

    # 验证只有相关的处理器被触发
    assert handled_events == [
        ("status_change", "published"),
        ("content_change", "new content")
    ]