# tests/rhosocial/activerecord_test/events/fixtures/models.py
from typing import Optional, Dict, List, Tuple

from pydantic import Field

from rhosocial.activerecord.interface import ModelEvent
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin, TimestampMixin
from ...utils import create_active_record_fixture


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


# Create a test fixture
event_test_model = create_active_record_fixture(EventTestModel)