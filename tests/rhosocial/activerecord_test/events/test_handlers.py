# tests/rhosocial/activerecord_test/events/test_handlers.py
from src.rhosocial.activerecord.interface import ModelEvent
from .fixtures.models import event_test_model


def test_event_handler_registration(event_test_model):
    """Test event handler registration"""
    instance = event_test_model(name="test")

    # Register event handlers
    def handler1(instance, **kwargs):
        instance.log_event(ModelEvent.BEFORE_SAVE, handler="handler1", **kwargs)

    def handler2(instance, **kwargs):
        instance.log_event(ModelEvent.BEFORE_SAVE, handler="handler2", **kwargs)

    instance.on(ModelEvent.BEFORE_SAVE, handler1)
    instance.on(ModelEvent.BEFORE_SAVE, handler2)

    # Verify handlers are registered
    assert len(instance._event_handlers[
                   ModelEvent.BEFORE_SAVE]) == 3  # Because TimestampMixin also registers a BEFORE_SAVE event.
    assert handler1 in instance._event_handlers[ModelEvent.BEFORE_SAVE]
    assert handler2 in instance._event_handlers[ModelEvent.BEFORE_SAVE]


def test_event_handler_removal(event_test_model):
    """Test event handler removal"""
    instance = event_test_model(name="test")

    def handler(instance, **kwargs):
        instance.log_event(ModelEvent.BEFORE_SAVE, handler="handler", **kwargs)

    # Register then remove handler
    instance.on(ModelEvent.BEFORE_SAVE, handler)
    assert handler in instance._event_handlers[ModelEvent.BEFORE_SAVE]

    instance.off(ModelEvent.BEFORE_SAVE, handler)
    assert handler not in instance._event_handlers[ModelEvent.BEFORE_SAVE]


def test_event_handler_execution(event_test_model):
    """Test event handler execution"""
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

    # Trigger event
    instance.save()

    # Verify execution order
    assert execution_order == ["handler1", "handler2"]

    # Verify event logs
    logs = instance.get_event_logs()
    assert len(logs) == 2
    assert logs[0][0] == ModelEvent.BEFORE_SAVE
    assert logs[0][1]["handler"] == "handler1"
    assert logs[1][0] == ModelEvent.BEFORE_SAVE
    assert logs[1][1]["handler"] == "handler2"


def test_multiple_event_types(event_test_model):
    """Test multiple event types"""
    instance = event_test_model(name="test")

    def save_handler(instance, **kwargs):
        instance.log_event(ModelEvent.BEFORE_SAVE, type="save", **kwargs)

    def delete_handler(instance, **kwargs):
        instance.log_event(ModelEvent.BEFORE_DELETE, type="delete", **kwargs)

    def validate_handler(instance, **kwargs):
        instance.log_event(ModelEvent.BEFORE_VALIDATE, type="validate", **kwargs)

    # Register different types of event handlers
    instance.on(ModelEvent.BEFORE_SAVE, save_handler)
    instance.on(ModelEvent.BEFORE_DELETE, delete_handler)
    instance.on(ModelEvent.BEFORE_VALIDATE, validate_handler)

    # Save record to trigger events
    instance.save()

    # Verify event records
    logs = instance.get_event_logs()
    save_events = [log for log in logs if log[1]["type"] == "save"]
    assert len(save_events) == 1


def test_event_data_passing(event_test_model):
    """Test event data passing"""
    instance = event_test_model(name="test")
    received_data = {}

    def handler(instance, **kwargs):
        received_data.update(kwargs)
        instance.log_event(ModelEvent.BEFORE_SAVE, **kwargs)

    instance.on(ModelEvent.BEFORE_SAVE, handler)

    # Trigger event with data
    instance._trigger_event(ModelEvent.BEFORE_SAVE, custom_data="test", is_new=True)

    # Verify data passing
    assert received_data["custom_data"] == "test"
    assert received_data["is_new"] is True

    # Verify event logs
    logs = instance.get_event_logs()
    assert logs[0][1]["custom_data"] == "test"
    assert logs[0][1]["is_new"] is True
