# src/rhosocial/activerecord/testsuite/feature/events/fixtures/models.py
"""
This file defines the generic ActiveRecord model classes used by the events tests.

These models are "generic" because they define the data structure and validation
rules (using Pydantic), but they are not tied to any specific database backend.
The backend-specific provider is responsible for taking these classes and
configuring them with a live database connection at test time.
"""
from typing import Optional, Dict, List, Tuple
from datetime import datetime

from pydantic import Field

from rhosocial.activerecord.interface import ModelEvent
from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin, TimestampMixin


class EventTestModel(IntegerPKMixin, TimestampMixin, ActiveRecord):
    """A model class for testing event mechanisms"""
    __table_name__ = "event_tests"

    id: Optional[int] = None
    name: str
    status: str = Field(default="draft")
    revision: int = Field(default=1)
    content: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        self._event_logs = []  # Used to record event triggering history

    def log_event(self, event: ModelEvent, **kwargs):
        """Record the trigger history of events"""
        self._event_logs.append((event, kwargs))

    def get_event_logs(self) -> List[Tuple[ModelEvent, Dict]]:
        """Get the event history"""
        return self._event_logs.copy()

    def clear_event_logs(self):
        """Empty the history of events"""
        self._event_logs.clear()


class AsyncEventTestModel(IntegerPKMixin, TimestampMixin, AsyncActiveRecord):
    """An async model class for testing event mechanisms"""
    __table_name__ = "event_tests"

    id: Optional[int] = None
    name: str
    status: str = Field(default="draft")
    revision: int = Field(default=1)
    content: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        self._event_logs = []  # Used to record event triggering history

    def log_event(self, event: ModelEvent, **kwargs):
        """Record the trigger history of events"""
        self._event_logs.append((event, kwargs))

    def get_event_logs(self) -> List[Tuple[ModelEvent, Dict]]:
        """Get the event history"""
        return self._event_logs.copy()

    def clear_event_logs(self):
        """Empty the history of events"""
        self._event_logs.clear()


class EventTrackingModel(IntegerPKMixin, ActiveRecord):
    """A model for testing event tracking functionality."""
    __table_name__ = "event_tracking_models"

    title: str
    content: str
    view_count: int = 0
    last_viewed_at: Optional[datetime] = None
