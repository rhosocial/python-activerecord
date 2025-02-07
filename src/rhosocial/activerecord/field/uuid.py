"""Module providing UUID functionality."""
import uuid
from typing import Dict, Any
from pydantic import Field

from ..interface import IActiveRecord


class UUIDMixin(IActiveRecord):
    """Adds UUID primary key support.

    Automatically generates UUIDs for new records.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4)

    def __init__(self, **data):
        pk_field = self.primary_key()
        if pk_field not in data:
            data[pk_field] = uuid.uuid4()
        super().__init__(**data)

    def prepare_save_data(self, data: Dict[str, Any], is_new: bool) -> Dict[str, Any]:
        """Prepare save data ensuring proper UUID handling

        Args:
            data: Current prepared data
            is_new: Whether this is a new record

        Returns:
            Dict[str, Any]: Processed data
        """
        pk_field = self.primary_key()

        if is_new and not getattr(self, pk_field, None):
            uuid_value = uuid.uuid4()
            setattr(self, pk_field, uuid_value)
            data[pk_field] = uuid_value
        elif pk_field not in data and getattr(self, pk_field, None):
            data[pk_field] = getattr(self, pk_field)

        parent_prepare = super().prepare_save_data if hasattr(super(), 'prepare_save_data') else None
        if parent_prepare:
            data = parent_prepare(data, is_new)

        return data