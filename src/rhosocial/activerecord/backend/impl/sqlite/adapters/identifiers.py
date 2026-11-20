# src/rhosocial/activerecord/backend/impl/sqlite/adapters/identifiers.py
"""UUID adapter for SQLite."""

import uuid
from typing import Any, Dict, Optional, Type

from rhosocial.activerecord.backend.errors import TypeConversionError
from rhosocial.activerecord.backend.type_adapter import BaseSQLTypeAdapter


class SQLiteUUIDAdapter(BaseSQLTypeAdapter):
    """
    Handles conversion between Python UUID objects and SQLite's TEXT or BLOB.
    """

    def __init__(self):
        super().__init__()
        self.register_type(uuid.UUID, str)
        self.register_type(uuid.UUID, bytes)

    def _do_to_database(
        self, value: uuid.UUID, target_type: Type, options: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Converts a Python UUID to a string or bytes."""
        if target_type is str:
            return str(value)
        if target_type is bytes:
            return value.bytes
        raise TypeConversionError(
            f"Cannot convert UUID to unsupported target type: {target_type.__name__}"
        )

    def _do_from_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None
    ) -> uuid.UUID:
        """Converts a string or bytes from the database to a Python UUID."""
        try:
            if isinstance(value, str):
                return uuid.UUID(value)
            if isinstance(value, bytes):
                return uuid.UUID(bytes=value)
        except (ValueError, TypeError) as e:
            raise TypeConversionError(
                f"Could not convert value of type {type(value).__name__} to UUID: {e}"
            ) from e

        raise TypeConversionError(f"Cannot convert {type(value).__name__} to UUID")
