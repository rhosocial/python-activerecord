# src/rhosocial/activerecord/backend/impl/sqlite/adapters/binary.py
"""BLOB adapter for SQLite."""

from typing import Any, Dict, Optional, Type

from rhosocial.activerecord.backend.errors import TypeConversionError
from rhosocial.activerecord.backend.type_adapter import BaseSQLTypeAdapter


class SQLiteBlobAdapter(BaseSQLTypeAdapter):
    """
    Handles conversion between Python bytes objects and SQLite BLOBs.
    """

    def __init__(self):
        super().__init__()
        self.register_type(bytes, bytes)

    def _do_to_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """Converts a Python value (str or bytes) to a SQLite-compatible BLOB."""
        if isinstance(value, str):
            return value.encode("utf-8")
        if isinstance(value, bytes):
            return value
        raise TypeConversionError(f"Cannot convert {type(value).__name__} to BLOB (bytes)")

    def _do_from_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """Converts a SQLite BLOB to a Python bytes object."""
        if isinstance(value, bytes):
            return value
        # In case the DB returns a string representation or similar for a BLOB
        if isinstance(value, str):
            return value.encode("utf-8")
        raise TypeConversionError(
            f"Cannot convert database value of type {type(value).__name__} to bytes"
        )
