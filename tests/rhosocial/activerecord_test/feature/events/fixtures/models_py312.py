# src/rhosocial/activerecord/testsuite/feature/events/fixtures/models_py312.py
"""
Python 3.12+ fixture model definitions for events tests.

This file contains model classes using Python 3.12+ syntax features:
- `@override` decorator for inheritance safety
- `Self` type for methods that return an instance of the same class
- `X | Y` syntax (inherited from 3.10+)

Note: This file should only be imported and used in Python 3.12+ environments.
"""
from __future__ import annotations

from typing import Dict, Self, override
from datetime import datetime

from pydantic import Field

from rhosocial.activerecord.interface import ModelEvent
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin, TimestampMixin


# Declare that this module requires Python 3.12+
__requires_python__ = (3, 12)


class EventTestModel(IntegerPKMixin, TimestampMixin, ActiveRecord):
    """A model class for testing event mechanisms.

    Python 3.12+ version using | syntax, Self type, and @override.
    """
    __table_name__ = "event_tests"

    id: int | None = None
    name: str
    status: str = Field(default="draft")
    revision: int = Field(default=1)
    content: str | None = None

    def __init__(self, **data):
        super().__init__(**data)
        self._event_logs: list[tuple[ModelEvent, Dict]] = []  # Used to record event triggering history

    def log_event(self, event: ModelEvent, **kwargs):
        """Record the trigger history of events"""
        self._event_logs.append((event, kwargs))

    def get_event_logs(self) -> list[tuple[ModelEvent, Dict]]:
        """Get the event history"""
        return self._event_logs.copy()

    def clear_event_logs(self) -> Self:
        """Empty the history of events and return self for chaining."""
        self._event_logs.clear()
        return self

    def set_status(self, new_status: str) -> Self:
        """Set status and return self for chaining."""
        self.status = new_status
        return self

    def increment_revision(self) -> Self:
        """Increment revision and return self for chaining."""
        self.revision += 1
        return self


class EventTrackingModel(IntegerPKMixin, ActiveRecord):
    """A model for testing event tracking functionality.

    Python 3.12+ version using | syntax, Self type, and @override.
    """
    __table_name__ = "event_tracking_models"

    title: str
    content: str
    view_count: int = 0
    last_viewed_at: datetime | None = None

    def record_view(self) -> Self:
        """Record a view and return self for chaining."""
        self.view_count += 1
        self.last_viewed_at = datetime.now()
        return self
