# src/rhosocial/activerecord/backend/impl/sqlite/adapters.py
"""
SQLite-specific type adapters.

This module provides specialized type adapters for the SQLite database,
handling its specific data type quirks and limitations, following the new
type adapter philosophy.

Design Rationale:
-----------------
This module implements only the adapters necessary to handle SQLite's
unique behaviors. For types where a standard adapter is sufficient, the
standard adapter is used directly by the backend, promoting code reuse.

Implemented Adapters:
- SQLiteBlobAdapter: Necessary because there is no standard adapter for
  BLOB data handling.
- SQLiteJSONAdapter: While a standard JSONAdapter exists, this custom
  version provides a more powerful serializer that can handle common Python
  types like datetime, UUID, and Decimal, which is a significant
  convenience for a backend that stores JSON as TEXT.
- SQLiteUUIDAdapter: The standard UUIDAdapter only handles string
  representations. SQLite can store UUIDs as TEXT or BLOBs, so this
  adapter is required to handle both cases correctly.

Omitted Adapters (Using Standard Instead):
- DecimalAdapter: The standard `DecimalAdapter` is sufficient for SQLite's
  needs, as it correctly handles conversion between Python's Decimal and
  SQLite's typical storage formats (TEXT or REAL/float). Therefore, a
  specific SQLite version is unnecessary.
- DateTimeAdapter, BooleanAdapter: The standard adapters for these types
  are fully compatible with SQLite's common practices (storing as ISO
  strings, timestamps, or integers).
"""
import datetime
import json
import uuid
from decimal import Decimal
from typing import Any, Dict, Optional, Type

from ...type_adapter import BaseSQLTypeAdapter
from ...errors import TypeConversionError


class SQLiteBlobAdapter(BaseSQLTypeAdapter):
    """
    Handles conversion between Python bytes objects and SQLite BLOBs.
    """
    def __init__(self):
        super().__init__()
        self._register_type(bytes, bytes)

    def _do_to_database(self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None) -> bytes:
        """Converts a Python value (str or bytes) to a SQLite-compatible BLOB."""
        if isinstance(value, str):
            return value.encode('utf-8')
        if isinstance(value, bytes):
            return value
        raise TypeConversionError(f"Cannot convert {type(value).__name__} to BLOB (bytes)")

    def _do_from_database(self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None) -> bytes:
        """Converts a SQLite BLOB to a Python bytes object."""
        if isinstance(value, bytes):
            return value
        # In case the DB returns a string representation or similar for a BLOB
        if isinstance(value, str):
            return value.encode('utf-8')
        raise TypeConversionError(f"Cannot convert database value of type {type(value).__name__} to bytes")


class SQLiteJSONAdapter(BaseSQLTypeAdapter):
    """
    Handles conversion for JSON stored as TEXT in SQLite.

    Includes an enhanced serializer to handle common Python types like
    datetime, UUID, and Decimal, which is a SQLite-specific convenience.
    """
    def __init__(self):
        super().__init__()
        self._register_type(dict, str)
        self._register_type(list, str)

    @staticmethod
    def _extended_json_serializer(obj: Any) -> Any:
        """A serializer for objects not handled by default json.dumps."""
        if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
            return obj.isoformat()
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, Decimal):
            return float(obj) # Representing as float is a common choice
        if isinstance(obj, set):
            return list(obj)
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    def _do_to_database(self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None) -> str:
        """Converts a Python dict or list to a JSON string."""
        if not isinstance(value, (dict, list)):
            raise TypeConversionError(f"Cannot convert {type(value).__name__} to JSON string; expected dict or list")

        try:
            return json.dumps(value, default=self._extended_json_serializer)
        except TypeError as e:
            raise TypeConversionError(f"Failed to serialize object to JSON: {e}")

    def _do_from_database(self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None) -> Any:
        """Converts a JSON string from the database back to a Python object."""
        if not isinstance(value, str):
             raise TypeConversionError(f"Cannot decode JSON from non-string type: {type(value).__name__}")
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            raise TypeConversionError(f"Failed to decode JSON string '{value[:100]}...': {e}")


class SQLiteUUIDAdapter(BaseSQLTypeAdapter):
    """
    Handles conversion between Python UUID objects and SQLite's TEXT or BLOB.
    """
    def __init__(self):
        super().__init__()
        self._register_type(uuid.UUID, str)
        self._register_type(uuid.UUID, bytes)

    def _do_to_database(self, value: uuid.UUID, target_type: Type, options: Optional[Dict[str, Any]] = None) -> Any:
        """Converts a Python UUID to a string or bytes."""
        if target_type == str:
            return str(value)
        if target_type == bytes:
            return value.bytes
        raise TypeConversionError(f"Cannot convert UUID to unsupported target type: {target_type.__name__}")

    def _do_from_database(self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None) -> uuid.UUID:
        """Converts a string or bytes from the database to a Python UUID."""
        try:
            if isinstance(value, str):
                return uuid.UUID(value)
            if isinstance(value, bytes):
                return uuid.UUID(bytes=value)
        except (ValueError, TypeError) as e:
            raise TypeConversionError(f"Could not convert value of type {type(value).__name__} to UUID: {e}")

        raise TypeConversionError(f"Cannot convert {type(value).__name__} to UUID")
