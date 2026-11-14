# src/rhosocial/activerecord/backend/impl/sqlite/adapters/document.py
"""JSON-as-TEXT adapter for SQLite."""

import datetime
import json
import uuid
from decimal import Decimal
from typing import Any, Dict, Optional, Type

from rhosocial.activerecord.backend.errors import TypeConversionError
from rhosocial.activerecord.backend.type_adapter import BaseSQLTypeAdapter


class SQLiteJSONAdapter(BaseSQLTypeAdapter):
    """
    Handles conversion for JSON stored as TEXT in SQLite.

    Includes an enhanced serializer to handle common Python types like
    datetime, UUID, and Decimal, which is a SQLite-specific convenience.
    """

    def __init__(self, default=None, object_hook=None):
        super().__init__()
        # ``default=None`` keeps the historical extended serializer; a caller
        # supplied function replaces it (e.g. AdapterJSONCodec.default).
        self._json_default = default
        self._json_object_hook = object_hook
        self.register_type(dict, str)
        self.register_type(list, str)

    @staticmethod
    def _extended_json_serializer(obj: Any) -> Any:
        """A serializer for objects not handled by default json.dumps."""
        if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
            return obj.isoformat()
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, Decimal):
            return float(obj)  # Representing as float is a common choice
        if isinstance(obj, set):
            return list(obj)
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    def _do_to_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None
    ) -> str:
        """Converts a Python dict or list to a JSON string."""
        if not isinstance(value, (dict, list)):
            raise TypeConversionError(
                f"Cannot convert {type(value).__name__} to JSON string; expected dict or list"
            )

        try:
            serializer = self._json_default or self._extended_json_serializer
            return json.dumps(value, default=serializer)
        except TypeError as e:
            raise TypeConversionError(f"Failed to serialize object to JSON: {e}") from e

    def _do_from_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Converts a JSON string from the database back to a Python object."""
        if not isinstance(value, str):
            raise TypeConversionError(
                f"Cannot decode JSON from non-string type: {type(value).__name__}"
            )
        try:
            return json.loads(value, object_hook=self._json_object_hook)
        except json.JSONDecodeError as e:
            raise TypeConversionError(
                f"Failed to decode JSON string '{value[:100]}...': {e}"
            ) from e
