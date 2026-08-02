# src/rhosocial/activerecord/testsuite/feature/events/fixtures/models_py310.py
"""
Python 3.10+ fixture model definitions for events tests.

This file contains model classes using Python 3.10+ syntax features:
- `X | Y` syntax instead of `Optional[X]` or `Union[X, Y]`
- `Type | None` instead of `Optional[Type]`

Note: This file should only be imported and used in Python 3.10+ environments.
"""
from typing import Dict, List, Tuple
from datetime import datetime

from pydantic import Field

from rhosocial.activerecord.interface import ModelEvent
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin, TimestampMixin


# Declare that this module requires Python 3.10+
__requires_python__ = (3, 10)


class EventTestModel(IntegerPKMixin, TimestampMixin, ActiveRecord):
    """A model class for testing event mechanisms.

    Python 3.10+ version using | syntax instead of Optional.
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

    def clear_event_logs(self):
        """Empty the history of events"""
        self._event_logs.clear()


class EventTrackingModel(IntegerPKMixin, ActiveRecord):
    """A model for testing event tracking functionality.

    Python 3.10+ version using | syntax instead of Optional.
    """
    __table_name__ = "event_tracking_models"

    title: str
    content: str
    view_count: int = 0
    last_viewed_at: datetime | None = None
