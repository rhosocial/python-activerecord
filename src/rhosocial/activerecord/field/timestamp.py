# src/rhosocial/activerecord/field/timestamp.py
"""Module providing timestamp functionality."""

from datetime import datetime, timezone
from pydantic import Field
from typing import Dict, Any

from ..interface import ModelEvent
from ..interface.update import IUpdateBehavior


class TimestampMixin(IUpdateBehavior):
    """Adds created_at and updated_at timestamp fields.

    Automatically maintains timestamps on record creation/updates.
    All timestamps are generated in Python using UTC timezone to ensure
    consistency across different database backends.

    Events used:
    - BEFORE_INSERT: Sets both created_at and updated_at for new records
    - BEFORE_UPDATE: Updates updated_at for existing records
    """

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def __init__(self, **data):
        super().__init__(**data)
        # Use separate events for INSERT and UPDATE operations
        self.on(ModelEvent.BEFORE_INSERT, self._set_timestamps_on_insert)
        self.on(ModelEvent.BEFORE_UPDATE, self._set_updated_at)

    def _set_timestamps_on_insert(self, instance: "TimestampMixin", data: Dict[str, Any], **kwargs):
        """Set both created_at and updated_at for INSERT operations.

        This callback is triggered before INSERT to set timestamps for new records.
        Both timestamps are set to the same value to ensure consistency.
        All timestamps are generated as UTC datetime objects in Python,
        ensuring consistent format across database backends.

        Args:
            instance: The model instance being saved
            data: The data dictionary to be inserted (can be modified)
            **kwargs: Additional event arguments
        """
        now = datetime.now(timezone.utc)
        instance.created_at = now
        instance.updated_at = now
        # Also update the data dictionary to ensure timestamps are saved
        data['created_at'] = now
        data['updated_at'] = now

    def _set_updated_at(self, instance: "TimestampMixin", data: Dict[str, Any], **kwargs):
        """Set updated_at for UPDATE operations.

        This callback is triggered before UPDATE to refresh the updated_at timestamp.
        All timestamps are generated as UTC datetime objects in Python,
        ensuring consistent format across database backends.

        Args:
            instance: The model instance being saved
            data: The data dictionary to be updated (can be modified)
            **kwargs: Additional event arguments (includes dirty_fields)
        """
        now = datetime.now(timezone.utc)
        instance.updated_at = now
        # Also update the data dictionary to ensure timestamp is saved
        data['updated_at'] = now

    def get_update_conditions(self):
        """Get additional WHERE conditions for UPDATE operations.

        For TimestampMixin, no additional conditions are needed during updates.
        """
        return []

    def get_update_expressions(self) -> Dict[str, Any]:
        """Provide update expressions for timestamp updates.

        Returns the updated_at field value, which is set by _set_updated_at.
        This ensures consistent UTC datetime format for both insert and update.
        """
        # updated_at is already set by _set_updated_at before save
        # Return empty dict to let the normal field value be used
        return {}
