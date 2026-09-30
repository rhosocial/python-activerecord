# src/rhosocial/activerecord/field/uuid.py
"""Module providing UUID functionality."""

import uuid
from typing import Any, Dict
from pydantic import Field

from ..interface.update import IDataPreparationBehavior


class UUIDMixin(IDataPreparationBehavior):
    """Adds UUID primary key support.

    Automatically generates UUIDs for new records.

    Generation happens in Python, not in the database. That is deliberate: it
    keeps the value available before the INSERT is built, so a model can use
    its own primary key in the same transaction without a round trip, and it
    works unchanged on backends with no UUID function (SQLite has none). A
    model that would rather let the database generate the value can render
    :class:`~...expression.uuid.UUIDGenerationExpression` into a column default
    instead — the two approaches are independent.

    The field is annotated ``uuid.UUID`` and left to normal type inference for
    its column type; see :class:`~...expression.types.UUIDType` for how a
    backend declares explicit UUID storage instead.
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

        parent_prepare = super().prepare_save_data if hasattr(super(), "prepare_save_data") else None
        if parent_prepare:
            data = parent_prepare(data, is_new)

        return data
