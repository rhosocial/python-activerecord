# src/rhosocial/activerecord/field/timestamp.py
"""Module providing timestamp functionality."""
from datetime import datetime, timezone
from pydantic import Field
from typing import Dict, Any

from ..interface import ModelEvent
from ..interface.update import IUpdateBehavior
from ..backend.expression.core import FunctionCall


class TimestampMixin(IUpdateBehavior):
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

    def get_update_conditions(self):
        """Get additional WHERE conditions for UPDATE operations.

        For TimestampMixin, no additional conditions are needed during updates.
        """
        return []

    def get_update_expressions(self) -> Dict[str, Any]:
        """Provide update expressions for timestamp updates using expression system."""
        backend = self.backend()
        if not self.is_new_record:
            from ..backend.expression.operators import RawSQLExpression
            return {
                'updated_at': RawSQLExpression(backend.dialect, 'CURRENT_TIMESTAMP')
            }
        from ..backend.expression.operators import RawSQLExpression
        return {
            'created_at': RawSQLExpression(backend.dialect, 'CURRENT_TIMESTAMP'),
            'updated_at': RawSQLExpression(backend.dialect, 'CURRENT_TIMESTAMP')
        }
