# src/rhosocial/activerecord/backend/impl/sqlite/type_converters.py
"""
SQLite-specific type converters.

This module provides specialized type converters for SQLite database,
handling its specific data type quirks and limitations.
"""
import datetime
import json
import uuid
from decimal import Decimal
from typing import Any

from ...basic_type_converter import UUIDConverter
from ...dialect import DatabaseType
from ...errors import TypeConversionError
from ...type_converters import BaseTypeConverter


class SQLiteBlobConverter(BaseTypeConverter):
    """
    SQLite BLOB converter.

    Handles conversion between Python bytes objects and SQLite BLOB data.
    """

    @property
    def priority(self) -> int:
        return 60

    def can_handle(self, value: Any, target_type: Any = None) -> bool:
        """
        Check if this converter can handle BLOB data.

        Args:
            value: The value to check
            target_type: Optional target type

        Returns:
            bool: True if this converter can handle the conversion
        """
        if target_type in (DatabaseType.BLOB, DatabaseType.BYTEA):
            return True
        if isinstance(value, bytes):
            return True
        return False

    def to_database(self, value: Any, target_type: Any = None) -> Any:
        """
        Convert a Python value to a SQLite BLOB.

        Args:
            value: The Python value to convert
            target_type: Optional target type hint

        Returns:
            bytes: The converted value ready for database storage
        """
        if value is None:
            return None

        # Convert string to bytes if target is BLOB
        if isinstance(value, str) and target_type in (DatabaseType.BLOB, DatabaseType.BYTEA):
            return value.encode('utf-8')

        # Already bytes
        if isinstance(value, bytes):
            return value

        return value  # Default: return unchanged

    def from_database(self, value: Any, source_type: Any = None) -> Any:
        """
        Convert a SQLite BLOB to a Python bytes object.

        Args:
            value: The database value to convert
            source_type: Optional source type hint

        Returns:
            bytes: The converted Python value
        """
        if value is None:
            return None

        # SQLite typically returns BLOB data as bytes already
        if source_type in (DatabaseType.BLOB, DatabaseType.BYTEA) and not isinstance(value, bytes):
            # Try to convert to bytes
            try:
                return bytes(value)
            except (TypeError, ValueError):
                return value

        return value  # Default: return unchanged


class SQLiteJSONConverter(BaseTypeConverter):
    """
    SQLite JSON converter.
    Handles conversion between Python objects and SQLite JSON storage.
    SQLite doesn't have a native JSON type, but the JSON1 extension provides
    JSON functionality for text columns.
    """

    @property
    def priority(self) -> int:
        return 55  # Higher than standard JSON converter

    def can_handle(self, value: Any, target_type: Any = None) -> bool:
        """
        Check if this converter can handle JSON data.

        Args:
            value: The value to check
            target_type: Optional target type

        Returns:
            bool: True if this converter can handle the conversion
        """
        if target_type in (DatabaseType.JSON, DatabaseType.JSONB):
            return True
        if isinstance(value, (dict, list)):
            return True
        return False

    def to_database(self, value: Any, target_type: Any = None) -> Any:
        """
        Convert a Python object to a SQLite JSON representation.

        Args:
            value: The Python value to convert
            target_type: Optional target type hint

        Returns:
            str: JSON string representation
        """
        if value is None:
            return None

        # If already a JSON string, validate it
        if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
            try:
                # Verify it's valid JSON
                json.loads(value)
                return value
            except json.JSONDecodeError:
                pass

        # Convert dict/list to JSON string
        if isinstance(value, (dict, list, tuple)):
            try:
                return json.dumps(value, default=self._json_serializer)
            except TypeError:
                return str(value)

        return value  # Default: return unchanged

    def from_database(self, value: Any, source_type: Any = None) -> Any:
        """
        Convert a SQLite JSON value to its Python representation.

        Args:
            value: The database value to convert
            source_type: Optional source type hint

        Returns:
            The converted Python value (dict, list, etc.)
        """
        if value is None:
            return None

        # Parse JSON string into Python object
        if source_type in (DatabaseType.JSON, DatabaseType.JSONB) and isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value

        return value  # Default: return unchanged

    def _json_serializer(self, obj: Any) -> Any:
        """
        Custom JSON serializer to handle special types.

        Args:
            obj: The object to serialize

        Returns:
            A JSON-serializable representation of the object

        Raises:
            TypeError: If the object cannot be serialized
        """
        if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
            return obj.isoformat()
        elif isinstance(obj, uuid.UUID):
            return str(obj)
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, set):
            return list(obj)
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class SQLiteArrayConverter(BaseTypeConverter):
    """
    SQLite array converter.

    SQLite has no native array type, so arrays are stored as JSON strings.
    """

    @property
    def priority(self) -> int:
        return 55  # Higher than standard JSON converter

    def can_handle(self, value: Any, target_type: Any = None) -> bool:
        """
        Check if this converter can handle array data.

        Args:
            value: The value to check
            target_type: Optional target type

        Returns:
            bool: True if this converter can handle the conversion
        """
        if target_type == DatabaseType.ARRAY:
            return True
        if isinstance(value, (list, tuple, set)):
            return True
        return False

    def to_database(self, value: Any, target_type: Any = None) -> Any:
        """
        Convert a Python sequence to a SQLite array representation (JSON).

        Args:
            value: The Python value to convert
            target_type: Optional target type hint

        Returns:
            str: JSON string representation of the array

        Raises:
            TypeConversionError: If value cannot be converted to array
        """
        if value is None:
            return None

        # Convert sequence to list
        if isinstance(value, (list, tuple, set)):
            try:
                return json.dumps(list(value), default=self._json_serializer)
            except TypeError:
                return str(value)

        # If target type is explicitly ARRAY and value is not a sequence, raise error
        if target_type == DatabaseType.ARRAY:
            raise TypeConversionError(f"Cannot convert {type(value)} to array")

        return value  # Default: return unchanged for other cases

    def from_database(self, value: Any, source_type: Any = None) -> Any:
        """
        Convert a SQLite array representation (JSON) to a Python list.

        Args:
            value: The database value to convert
            source_type: Optional source type hint

        Returns:
            list: The converted Python value
        """
        if value is None:
            return None

        # Parse JSON string to list
        if source_type == DatabaseType.ARRAY and isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value

        return value  # Default: return unchanged

    def _json_serializer(self, obj: Any) -> Any:
        """
        Custom JSON serializer for array elements.

        Args:
            obj: The object to serialize

        Returns:
            A JSON-serializable representation

        Raises:
            TypeError: If the object cannot be serialized
        """
        if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
            return obj.isoformat()
        elif isinstance(obj, uuid.UUID):
            return str(obj)
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, set):
            return list(obj)
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class SQLiteNumericConverter(BaseTypeConverter):
    """
    SQLite numeric converter.

    Handles conversion between Python Decimal objects and SQLite NUMERIC data.
    SQLite has no native Decimal type, so they are stored as strings.
    """

    @property
    def priority(self) -> int:
        return 50  # Between bool and UUID

    def can_handle(self, value: Any, target_type: Any = None) -> bool:
        """
        Check if this converter can handle numeric data.

        Args:
            value: The value to check
            target_type: Optional target type

        Returns:
            bool: True if this converter can handle the conversion
        """
        if target_type in (DatabaseType.DECIMAL, DatabaseType.NUMERIC):
            return True
        if isinstance(value, Decimal):
            return True
        return False

    def to_database(self, value: Any, target_type: Any = None) -> Any:
        """
        Convert a Python Decimal to a SQLite representation.

        Args:
            value: The Python value to convert
            target_type: Optional target type hint

        Returns:
            str: String representation of the Decimal
        """
        if value is None:
            return None

        # Convert Decimal to string to preserve precision
        if isinstance(value, Decimal):
            return float(value)

        # Try to convert numeric strings to Decimal and then to string
        if isinstance(value, str) and target_type in (DatabaseType.DECIMAL, DatabaseType.NUMERIC):
            try:
                return float(Decimal(value))
            except:
                return value

        return value  # Default: return unchanged

    def from_database(self, value: Any, source_type: Any = None) -> Any:
        """
        Convert a SQLite numeric value to a Python Decimal.

        Args:
            value: The database value to convert
            source_type: Optional source type hint

        Returns:
            Decimal: The converted Python value
        """
        if value is None:
            return None

        # Convert string to Decimal
        if source_type in (DatabaseType.DECIMAL, DatabaseType.NUMERIC) and isinstance(value, str):
            try:
                return Decimal(value)
            except:
                return value

        return value  # Default: return unchanged


class SQLiteUUIDConverter(UUIDConverter):
    """
    SQLite UUID converter.

    Handles conversion between Python UUID objects and SQLite TEXT storage.
    """

    @property
    def priority(self) -> int:
        return 45  # Higher priority than base UUID converter

    def to_database(self, value: Any, target_type: Any = None) -> Any:
        """
        Convert a Python UUID to SQLite TEXT format.

        Args:
            value: The Python value to convert
            target_type: Optional target type hint

        Returns:
            str: The converted value ready for database storage
        """
        if value is None:
            return None

        # Convert UUID object to string
        if isinstance(value, uuid.UUID):
            return str(value)

        # Normalize UUID string
        if isinstance(value, str) and self._is_uuid_string(value):
            try:
                return str(uuid.UUID(value))
            except ValueError:
                return value

        # Convert bytes to UUID string if appropriate
        if isinstance(value, bytes) and len(value) == 16:
            try:
                return str(uuid.UUID(bytes=value))
            except ValueError:
                return value

        return value  # Default: return unchanged

    def from_database(self, value: Any, source_type: Any = None) -> Any:
        """
        Convert a SQLite TEXT UUID to Python UUID object.

        Args:
            value: The database value to convert
            source_type: Optional source type hint

        Returns:
            uuid.UUID: The converted Python value
        """
        if value is None:
            return None

        # Convert string to UUID
        if isinstance(value, str) and self._is_uuid_string(value):
            try:
                return uuid.UUID(value)
            except ValueError:
                return value

        return value  # Default: return unchanged
