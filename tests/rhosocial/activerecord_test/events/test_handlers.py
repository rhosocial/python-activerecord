# tests/rhosocial/activerecord_test/events/test_handlers.py
from src.rhosocial.activerecord.interface import ModelEvent
from .fixtures.models import event_test_model

def test_event_handler_registration(event_test_model):
    """测试事件处理器注册"""
    instance = event_test_model(name="test")

    # 注册事件处理器
    def handler1(instance, **kwargs):
        instance.log_event(ModelEvent.BEFORE_SAVE, handler="handler1", **kwargs)

    def handler2(instance, **kwargs):
        instance.log_event(ModelEvent.BEFORE_SAVE, handler="handler2", **kwargs)

    instance.on(ModelEvent.BEFORE_SAVE, handler1)
    instance.on(ModelEvent.BEFORE_SAVE, handler2)

    # 验证处理器已注册
    assert len(instance._event_handlers[ModelEvent.BEFORE_SAVE]) == 3  # 因为 TimestampMixin 也会注册一个 BEFORE_SAVE 事件。
    assert handler1 in instance._event_handlers[ModelEvent.BEFORE_SAVE]
    assert handler2 in instance._event_handlers[ModelEvent.BEFORE_SAVE]


def test_event_handler_removal(event_test_model):
    """测试事件处理器移除"""
    instance = event_test_model(name="test")

    def handler(instance, **kwargs):
        instance.log_event(ModelEvent.BEFORE_SAVE, handler="handler", **kwargs)

    # 注册然后移除处理器
    instance.on(ModelEvent.BEFORE_SAVE, handler)
    assert handler in instance._event_handlers[ModelEvent.BEFORE_SAVE]

    instance.off(ModelEvent.BEFORE_SAVE, handler)
    assert handler not in instance._event_handlers[ModelEvent.BEFORE_SAVE]


def test_event_handler_execution(event_test_model):
    """测试事件处理器执行"""
    instance = event_test_model(name="test")
    execution_order = []

    def handler1(instance, **kwargs):
        execution_order.append("handler1")
        instance.log_event(ModelEvent.BEFORE_SAVE, handler="handler1", **kwargs)

    def handler2(instance, **kwargs):
        execution_order.append("handler2")
        instance.log_event(ModelEvent.BEFORE_SAVE, handler="handler2", **kwargs)

    instance.on(ModelEvent.BEFORE_SAVE, handler1)
    instance.on(ModelEvent.BEFORE_SAVE, handler2)

    # 触发事件
    instance.save()

    # 验证执行顺序
    assert execution_order == ["handler1", "handler2"]

    # 验证事件日志
    logs = instance.get_event_logs()
    assert len(logs) == 2
    assert logs[0][0] == ModelEvent.BEFORE_SAVE
    assert logs[0][1]["handler"] == "handler1"
    assert logs[1][0] == ModelEvent.BEFORE_SAVE
    assert logs[1][1]["handler"] == "handler2"


def test_multiple_event_types(event_test_model):
    """测试多种事件类型"""
    instance = event_test_model(name="test")

    def save_handler(instance, **kwargs):
        instance.log_event(ModelEvent.BEFORE_SAVE, type="save", **kwargs)

    def delete_handler(instance, **kwargs):
        instance.log_event(ModelEvent.BEFORE_DELETE, type="delete", **kwargs)

    def validate_handler(instance, **kwargs):
        instance.log_event(ModelEvent.BEFORE_VALIDATE, type="validate", **kwargs)

    # 注册不同类型的事件处理器
    instance.on(ModelEvent.BEFORE_SAVE, save_handler)
    instance.on(ModelEvent.BEFORE_DELETE, delete_handler)
    instance.on(ModelEvent.BEFORE_VALIDATE, validate_handler)

    # 保存记录触发事件
    instance.save()

    # 验证事件记录
    logs = instance.get_event_logs()
    save_events = [log for log in logs if log[1]["type"] == "save"]
    assert len(save_events) == 1


def test_event_data_passing(event_test_model):
    """测试事件数据传递"""
    instance = event_test_model(name="test")
    received_data = {}

    def handler(instance, **kwargs):
        received_data.update(kwargs)
        instance.log_event(ModelEvent.BEFORE_SAVE, **kwargs)

    instance.on(ModelEvent.BEFORE_SAVE, handler)

    # 触发带数据的事件
    instance._trigger_event(ModelEvent.BEFORE_SAVE, custom_data="test", is_new=True)

    # 验证数据传递
    assert received_data["custom_data"] == "test"
    assert received_data["is_new"] is True

    # 验证事件日志
    logs = instance.get_event_logs()
    assert logs[0][1]["custom_data"] == "test"
    assert logs[0][1]["is_new"] is True