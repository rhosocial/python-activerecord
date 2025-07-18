# tests/rhosocial/activerecord_test/events/test_lifecycle.py
import pytest
from src.rhosocial.activerecord.interface import ModelEvent

from .fixtures.models import event_test_model


def test_save_lifecycle_events(event_test_model):
    """Test save lifecycle events"""
    instance = event_test_model(name="test")

    # Record event trigger sequence
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

    # Register all event handlers
    instance.on(ModelEvent.BEFORE_VALIDATE, on_before_validate)
    instance.on(ModelEvent.AFTER_VALIDATE, on_after_validate)
    instance.on(ModelEvent.BEFORE_SAVE, on_before_save)
    instance.on(ModelEvent.AFTER_SAVE, on_after_save)

    # Save record
    instance.save()

    # Verify event sequence
    expected_sequence = [
        ("BEFORE_VALIDATE", 1),
        ("AFTER_VALIDATE", 1),
        ("BEFORE_SAVE", 1),
        ("AFTER_SAVE", 2)
    ]
    assert event_sequence == expected_sequence


def test_delete_lifecycle_events(event_test_model):
    """Test delete lifecycle events"""
    instance = event_test_model(name="test")
    instance.save()

    event_sequence = []

    def on_before_delete(instance, **kwargs):
        event_sequence.append("BEFORE_DELETE")
        instance.status = "deleting"

    def on_after_delete(instance, **kwargs):
        event_sequence.append("AFTER_DELETE")

    # Register delete event handlers
    instance.on(ModelEvent.BEFORE_DELETE, on_before_delete)
    instance.on(ModelEvent.AFTER_DELETE, on_after_delete)

    # Delete record
    instance.delete()

    # Verify event sequence and status change
    assert event_sequence == ["BEFORE_DELETE", "AFTER_DELETE"]
    assert instance.status == "deleting"


def test_validation_lifecycle_events(event_test_model):
    """Test validation lifecycle events"""
    instance = event_test_model(name="test")

    validation_data = {}

    def on_before_validate(instance, **kwargs):
        validation_data["before"] = instance.name
        instance.name = instance.name.strip()

    def on_after_validate(instance, **kwargs):
        validation_data["after"] = instance.name

    # Register validation event handlers
    instance.on(ModelEvent.BEFORE_VALIDATE, on_before_validate)
    instance.on(ModelEvent.AFTER_VALIDATE, on_after_validate)

    # Create instance with name containing spaces and save
    instance.name = " test_name "
    instance.save()

    # Verify name changes before and after validation
    assert validation_data["before"] == " test_name "
    assert validation_data["after"] == "test_name"
    assert instance.name == "test_name"


def test_nested_event_handling(event_test_model):
    """Test nested event handling"""
    parent = event_test_model(name="parent")
    child = event_test_model(name="child")

    event_sequence = []

    def parent_save_handler(instance, **kwargs):
        event_sequence.append("parent_before_save")
        # Save child object when parent object is saved
        child.save()

    def child_save_handler(instance, **kwargs):
        event_sequence.append("child_before_save")

    # Register event handlers
    parent.on(ModelEvent.BEFORE_SAVE, parent_save_handler)
    child.on(ModelEvent.BEFORE_SAVE, child_save_handler)

    # Save parent object
    parent.save()

    # Verify execution order of nested events
    assert event_sequence == ["parent_before_save", "child_before_save"]


def test_event_error_handling(event_test_model):
    """Test event error handling"""
    instance = event_test_model(name="test")

    def error_handler(instance, **kwargs):
        raise ValueError("Test error in event handler")

    # Register handler that may raise errors
    instance.on(ModelEvent.BEFORE_SAVE, error_handler)

    # Verify error propagates correctly
    with pytest.raises(ValueError) as exc_info:
        instance.save()
    assert "Test error in event handler" in str(exc_info.value)


def test_conditional_event_handling(event_test_model):
    """Test conditional event handling"""
    instance = event_test_model(name="test", status="draft")
    handled_events = []

    def status_change_handler(instance, **kwargs):
        if instance.is_dirty and "status" in instance.dirty_fields:
            handled_events.append(("status_change", instance.status))

    def content_change_handler(instance, **kwargs):
        if instance.is_dirty and "content" in instance.dirty_fields:
            handled_events.append(("content_change", instance.content))

    # Register conditional handlers
    instance.on(ModelEvent.BEFORE_SAVE, status_change_handler)
    instance.on(ModelEvent.BEFORE_SAVE, content_change_handler)

    # Test status change
    instance.status = "published"
    instance.save()

    # Test content change
    instance.content = "new content"
    instance.save()

    # Verify only relevant handlers were triggered
    assert handled_events == [
        ("status_change", "published"),
        ("content_change", "new content")
    ]
