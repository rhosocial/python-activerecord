# src/rhosocial/activerecord/field/timestamp.py
"""Module providing timestamp functionality."""
from datetime import datetime, timezone
from pydantic import Field
from typing import Dict, Any

from ..interface import IActiveRecord, IUpdateBehavior, ModelEvent
from ..backend.expression.core import FunctionCall


class TimestampMixin(IActiveRecord):
    """Adds created_at and updated_at timestamp fields.

    Automatically maintains timestamps on record creation/updates.
    """

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def __init__(self, **data):
        super().__init__(**data)
        self.on(ModelEvent.BEFORE_SAVE, self._update_timestamps)

    def _update_timestamps(self, instance: 'TimestampMixin', is_new: bool, **kwargs):
        """Update created_at/updated_at timestamps.

        Sets created_at for new records.
        Updates updated_at for all saves.
        """
        now = datetime.now(timezone.utc)
        if is_new:
            instance.created_at = now
        instance.updated_at = now

    def get_update_expressions(self) -> Dict[str, Any]:
        """Provide update expressions for timestamp updates using expression system."""
        backend = self.backend()
        if not self.is_new_record:
            return {
                'updated_at': FunctionCall(backend.dialect, 'CURRENT_TIMESTAMP')
            }
        return {
            'created_at': FunctionCall(backend.dialect, 'CURRENT_TIMESTAMP'),
            'updated_at': FunctionCall(backend.dialect, 'CURRENT_TIMESTAMP')
        }
