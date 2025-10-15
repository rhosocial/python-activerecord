# src/rhosocial/activerecord/backend/basic_type_converter.py
"""
Basic type converters implementation.

This module provides standard type converters for common data types
that work across different database backends.
"""

import datetime
import json
import uuid
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from .typing import DatabaseType
from .type_converters import BaseTypeConverter
from .errors import TypeConversionError


class BasicTypeConverter(BaseTypeConverter):
    """
    Basic type converter for primitive data types.

    Handles conversion of integers, floats, strings, and booleans.
    """

    @property
    def priority(self) -> int:
        """Lower priority to allow specialized converters to take precedence."""
        return 10

    def can_handle(self, value: Any, target_type: Any = None) -> bool:
        """
        Check if this converter can handle the given value or type.

        Handles basic numerical and string types, but respects specific type hints.

        Args:
            value: The value to check
            target_type: Optional target type

        Returns:
            bool: True if this converter can handle the conversion
        """
        # If a specific target type is requested that's not typically handled by this converter,
        # return False to let specialized converters handle it
        if target_type is not None:
            # Don't handle specialized types, let specialized converters handle them
            specialized_types = [
                DatabaseType.DATE, DatabaseType.TIME, DatabaseType.DATETIME, DatabaseType.TIMESTAMP,
                DatabaseType.UUID, DatabaseType.JSON, DatabaseType.JSONB,
                DatabaseType.DECIMAL, DatabaseType.NUMERIC, DatabaseType.ARRAY
            ]
            if target_type in specialized_types:
                return False

        # Check if value is a basic type
        if isinstance(value, (int, float, str, bool)):
            return True

        return False

    def to_database(self, value: Any, target_type: Any = None) -> Any:
        """
        Convert a basic Python value to its database representation.

        Args:
            value: The Python value to convert
            target_type: Optional target type hint

        Returns:
            The converted value ready for database storage
        """
        if value is None:
            return None

        # Handle values without explicit target type
        if isinstance(value, (int, float, str)):
            return value
        if isinstance(value, bool):
            # Most DBs store booleans as 0/1
            return 1 if value else 0

        return value  # Default: return unchanged

    def from_database(self, value: Any, source_type: Any = None) -> Any:
        """
        Convert a database value to its Python representation.

        Args:
            value: The database value to convert
            source_type: Optional source type hint

        Returns:
            The converted Python value
        """
        if value is None:
            return None

        # Convert to appropriate Python type based on source_type
        if source_type == DatabaseType.BOOLEAN:
            return bool(value)

        # Return value unchanged for other basic types
        return value


class DateTimeConverter(BaseTypeConverter):
    """
    Enhanced converter for date and time types with timezone support.

    Handles conversion between Python datetime objects and database date/time representations,
    with proper timezone handling.
    """

    @property
    def priority(self) -> int:
        return 20

    def can_handle(self, value: Any, target_type: Any = None) -> bool:
        """
        Check if this converter can handle date/time values.

        Args:
            value: The value to check
            target_type: Optional target type

        Returns:
            bool: True if this converter can handle the conversion
        """
        if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
            return True

        if target_type and target_type in (DatabaseType.DATE, DatabaseType.TIME, DatabaseType.DATETIME,
                                           DatabaseType.TIMESTAMP):
            return True

        return False

    def to_database(self, value: Any, target_type: Any = None, timezone: Optional[str] = None) -> Any:
        """
        Convert a Python date/time value to its database representation with timezone handling.

        Args:
            value: The Python value to convert
            target_type: Optional target type hint
            timezone: Optional timezone name (e.g., 'UTC', 'America/New_York')

        Returns:
            The converted value ready for database storage
        """
        if value is None:
            return None

        # Return unchanged if already a string
        if isinstance(value, str):
            return value

        # Handle timezone if provided and value is datetime with tzinfo
        if isinstance(value, datetime.datetime):
            # Apply timezone if provided and datetime is naive (no timezone)
            if timezone and value.tzinfo is None:
                try:
                    import pytz
                    tz = pytz.timezone(timezone)
                    value = tz.localize(value)
                except (ImportError, pytz.exceptions.UnknownTimeZoneError):
                    # If pytz not available or timezone invalid, continue with naive datetime
                    pass

            # Convert based on target type
            if target_type == DatabaseType.DATE:
                return value.date().isoformat()  # YYYY-MM-DD
            elif target_type == DatabaseType.TIME:
                # Include timezone info in time if present
                if value.tzinfo:
                    return value.time().isoformat() + value.strftime('%z')
                return value.time().isoformat()  # HH:MM:SS.mmmmmm
            else:  # DATETIME, TIMESTAMP
                # Format with timezone if present
                if value.tzinfo:
                    return value.isoformat()  # Include timezone
                return value.isoformat(' ')  # YYYY-MM-DD HH:MM:SS.mmmmmm

        if isinstance(value, datetime.date):
            return value.isoformat()  # YYYY-MM-DD

        if isinstance(value, datetime.time):
            return value.isoformat()  # HH:MM:SS.mmmmmm

        return value  # Default: return unchanged

    def from_database(self, value: Any, source_type: Any = None, timezone: Optional[str] = None) -> Any:
        """
        Convert a database date/time value to its Python representation with timezone handling.

        Args:
            value: The database value to convert
            source_type: Optional source type hint
            timezone: Optional timezone name to use for naive datetimes

        Returns:
            The converted Python value
        """
        if value is None:
            return None

        # Already a datetime object, handle timezone if needed
        if isinstance(value, datetime.datetime):
            # Apply target timezone if requested and datetime has tzinfo
            if timezone and value.tzinfo is not None:
                try:
                    import pytz
                    tz = pytz.timezone(timezone)
                    return value.astimezone(tz)
                except (ImportError, pytz.exceptions.UnknownTimeZoneError):
                    # If pytz not available or timezone invalid, return as is
                    pass
            return value

        if isinstance(value, (datetime.date, datetime.time)):
            return value

        # Only convert string values
        if not isinstance(value, str):
            return value

        try:
            # Convert based on source type with timezone handling
            if source_type == DatabaseType.DATE:
                return datetime.date.fromisoformat(value)

            elif source_type == DatabaseType.TIME:
                # Handle time strings with timezone info
                try:
                    return datetime.time.fromisoformat(value)
                except ValueError:
                    # If standard parsing fails, try alternative formats
                    if '+' in value or '-' in value:
                        # Attempt to parse time with timezone
                        # This is simplified - real implementation would need more robust parsing
                        time_part = value.split('+')[0].split('-')[0]
                        return datetime.time.fromisoformat(time_part)
                    return value

            elif source_type in (DatabaseType.DATETIME, DatabaseType.TIMESTAMP):
                # Parse datetime with timezone awareness
                dt = None

                # Handle ISO format with space or T separator
                if ' ' in value:
                    dt = datetime.datetime.fromisoformat(value)
                elif 'T' in value:
                    dt = datetime.datetime.fromisoformat(value)

                # Apply timezone if requested and datetime is naive
                if dt and timezone and dt.tzinfo is None:
                    try:
                        import pytz
                        tz = pytz.timezone(timezone)
                        dt = tz.localize(dt)
                    except (ImportError, pytz.exceptions.UnknownTimeZoneError):
                        # If pytz not available or timezone invalid, return as is
                        pass

                return dt

            # Fallback for unknown source_type - try to determine from string format
            if 'T' in value or ' ' in value:
                # Looks like a datetime
                dt = datetime.datetime.fromisoformat(value)
                # Apply timezone if provided and datetime is naive
                if timezone and dt.tzinfo is None:
                    try:
                        import pytz
                        tz = pytz.timezone(timezone)
                        dt = tz.localize(dt)
                    except (ImportError, pytz.exceptions.UnknownTimeZoneError):
                        pass
                return dt
            elif ':' in value:  # Contains time separator
                return datetime.time.fromisoformat(value)
            else:  # Probably a date
                return datetime.date.fromisoformat(value)

        except ValueError:
            # If parsing fails, return the original value
            return value

        return value  # Default: return unchanged


class BooleanConverter(BaseTypeConverter):
    """
    Converter for boolean values.

    Handles conversion between Python bool and database boolean representations.
    """

    @property
    def priority(self) -> int:
        return 30

    def can_handle(self, value: Any, target_type: Any = None) -> bool:
        """
        Check if this converter can handle boolean values.

        Args:
            value: The value to check
            target_type: Optional target type

        Returns:
            bool: True if this converter can handle the conversion
        """
        if isinstance(value, bool):
            return True
        if target_type and target_type == DatabaseType.BOOLEAN:
            return True
        return False

    def to_database(self, value: Any, target_type: Any = None) -> Any:
        """
        Convert a Python boolean value to its database representation.

        Args:
            value: The Python value to convert
            target_type: Optional target type hint

        Returns:
            The converted value ready for database storage
        """
        if value is None:
            return None

        # Convert bool to 0/1 (common for SQLite and other DBs)
        if isinstance(value, bool):
            return 1 if value else 0

        # Convert string boolean representations
        if isinstance(value, str):
            value_lower = value.lower()
            if value_lower in ('true', 'yes', 'y', '1', 'on'):
                return 1
            elif value_lower in ('false', 'no', 'n', '0', 'off'):
                return 0

        # Try to convert other types
        try:
            return 1 if bool(value) else 0
        except (ValueError, TypeError):
            return value

    def from_database(self, value: Any, source_type: Any = None) -> Any:
        """
        Convert a database boolean value to its Python representation.

        Args:
            value: The database value to convert
            source_type: Optional source type hint

        Returns:
            The converted Python value
        """
        if value is None:
            return None

        # Convert to Python bool based on source type
        if source_type == DatabaseType.BOOLEAN:
            if isinstance(value, (int, float)):
                return bool(value)
            if isinstance(value, str):
                value_lower = value.lower()
                if value_lower in ('true', 'yes', 'y', '1', 'on'):
                    return True
                elif value_lower in ('false', 'no', 'n', '0', 'off'):
                    return False

        return value  # Default: return unchanged


class UUIDConverter(BaseTypeConverter):
    """
    Converter for UUID values.

    Handles conversion between Python UUID objects and database string representations.
    """

    @property
    def priority(self) -> int:
        return 40

    def can_handle(self, value: Any, target_type: Any = None) -> bool:
        """
        Check if this converter can handle UUID values.

        Args:
            value: The value to check
            target_type: Optional target type

        Returns:
            bool: True if this converter can handle the conversion
        """
        if isinstance(value, uuid.UUID):
            return True
        if target_type and target_type == DatabaseType.UUID:
            return True
        if isinstance(value, str) and self._is_uuid_string(value):
            return True
        return False

    def _is_uuid_string(self, value: str) -> bool:
        """Check if a string looks like a UUID."""
        if not isinstance(value, str):
            return False

        # Standard UUID format
        import re
        if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', value.lower()):
            return True

        # Compact UUID format without dashes
        if re.match(r'^[0-9a-f]{32}$', value.lower()):
            return True

        return False

    def to_database(self, value: Any, target_type: Any = None) -> Any:
        """
        Convert a Python UUID to its database representation.

        Args:
            value: The Python value to convert
            target_type: Optional target type hint

        Returns:
            The converted value ready for database storage
        """
        if value is None:
            return None

        # Convert UUID object to string
        if isinstance(value, uuid.UUID):
            return str(value)

        # Try to convert string to UUID and then back to string
        if isinstance(value, str) and self._is_uuid_string(value):
            try:
                return str(uuid.UUID(value))
            except ValueError:
                return value

        return value  # Default: return unchanged

    def from_database(self, value: Any, source_type: Any = None) -> Any:
        """
        Convert a database UUID value to its Python representation.

        Args:
            value: The database value to convert
            source_type: Optional source type hint

        Returns:
            The converted Python value
        """
        if value is None:
            return None

        # Convert string to UUID if source type indicates UUID
        if source_type == DatabaseType.UUID and isinstance(value, str):
            try:
                return uuid.UUID(value)
            except ValueError:
                return value

        return value  # Default: return unchanged


class JSONConverter(BaseTypeConverter):
    """
    Converter for JSON values.

    Handles conversion between Python dict/list objects and database JSON representations.
    """

    @property
    def priority(self) -> int:
        return 50

    def can_handle(self, value: Any, target_type: Any = None) -> bool:
        """
        Check if this converter can handle JSON values.

        Args:
            value: The value to check
            target_type: Optional target type

        Returns:
            bool: True if this converter can handle the conversion
        """
        if isinstance(value, (dict, list)):
            return True
        if target_type and target_type in (DatabaseType.JSON, DatabaseType.JSONB):
            return True
        return False

    def to_database(self, value: Any, target_type: Any = None) -> Any:
        """
        Convert a Python object to its JSON database representation.

        Args:
            value: The Python value to convert
            target_type: Optional target type hint

        Returns:
            The converted value ready for database storage
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
        Convert a database JSON value to its Python representation.

        Args:
            value: The database value to convert
            source_type: Optional source type hint

        Returns:
            The converted Python value
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
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class DecimalConverter(BaseTypeConverter):
    """
    Converter for Decimal values.
    Handles conversion between Python Decimal objects and database numeric representations.
    """

    @property
    def priority(self) -> int:
        return 45

    def can_handle(self, value: Any, target_type: Any = None) -> bool:
        """
        Check if this converter can handle Decimal values.

        Args:
            value: The value to check
            target_type: Optional target type

        Returns:
            bool: True if this converter can handle the conversion
        """
        if isinstance(value, Decimal):
            return True
        if target_type and target_type in (DatabaseType.DECIMAL, DatabaseType.NUMERIC):
            return True
        return False

    def to_database(self, value: Any, target_type: Any = None) -> Any:
        """
        Convert a Python Decimal to its database representation.

        Args:
            value: The Python value to convert
            target_type: Optional target type hint

        Returns:
            The converted value ready for database storage
        """
        if value is None:
            return None

        # Convert Decimal to string to preserve precision
        if isinstance(value, Decimal):
            return float(value)

        # Try to convert string to Decimal
        if isinstance(value, str):
            try:
                return float(Decimal(value))
            except:
                return value

        return value  # Default: return unchanged

    def from_database(self, value: Any, source_type: Any = None) -> Any:
        """
        Convert a database numeric value to its Python representation.

        Args:
            value: The database value to convert
            source_type: Optional source type hint

        Returns:
            The converted Python value
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


class ArrayConverter(BaseTypeConverter):
    """
    Converter for array values.

    Handles conversion between Python list/tuple objects and database array representations.
    For databases without native array support (like SQLite), it uses JSON serialization.
    """

    @property
    def priority(self) -> int:
        return 35  # Lower than JSON converter

    def can_handle(self, value: Any, target_type: Any = None) -> bool:
        """
        Check if this converter can handle array values.

        Args:
            value: The value to check
            target_type: Optional target type

        Returns:
            bool: True if this converter can handle the conversion
        """
        if isinstance(value, (list, tuple, set)):
            return True
        if target_type and target_type == DatabaseType.ARRAY:
            return True
        return False

    def to_database(self, value: Any, target_type: Any = None) -> Any:
        """
        Convert a Python sequence to its database array representation.

        Args:
            value: The Python value to convert
            target_type: Optional target type hint

        Returns:
            The converted value ready for database storage

        Raises:
            TypeConversionError: If value cannot be converted to array
        """
        if value is None:
            return None

        # Convert various sequence types to a list
        if isinstance(value, (list, tuple, set)):
            sequence = list(value)
            # Use JSON for databases without native array support
            return json.dumps(sequence, default=self._json_serializer)

        # If target type is explicitly ARRAY and value is not a sequence, raise error
        if target_type == DatabaseType.ARRAY:
            raise TypeConversionError(f"Cannot convert {type(value)} to array")

        return value  # Default: return unchanged for other cases

    def from_database(self, value: Any, source_type: Any = None) -> Any:
        """
        Convert a database array value to its Python representation.

        Args:
            value: The database value to convert
            source_type: Optional source type hint

        Returns:
            The converted Python value
        """
        if value is None:
            return None

        # Parse JSON string array into Python list
        if source_type == DatabaseType.ARRAY and isinstance(value, str):
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


class EnumConverter(BaseTypeConverter):
    """
    Converter for Enum values.
    Handles conversion between Python Enum objects and database representations.
    """

    @property
    def priority(self) -> int:
        return 60

    def can_handle(self, value: Any, target_type: Any = None) -> bool:
        """
        Check if this converter can handle Enum values.

        Args:
            value: The value to check
            target_type: Optional target type

        Returns:
            bool: True if this converter can handle the conversion
        """
        return isinstance(value, Enum)

    def to_database(self, value: Any, target_type: Any = None) -> Any:
        """
        Convert a Python Enum to its database representation.

        Args:
            value: The Python value to convert
            target_type: Optional target type hint

        Returns:
            The converted value ready for database storage
        """
        if value is None:
            return None

        if isinstance(value, Enum):
            # Use the value attribute by default
            return value.value

        return value  # Default: return unchanged

    def from_database(self, value: Any, source_type: Any = None) -> Any:
        """
        Convert a database value to its Python Enum representation.

        This method requires additional context (the specific Enum class)
        which is not available through this interface alone.
        It would typically be used with a custom converter for specific Enum types.

        Args:
            value: The database value to convert
            source_type: Optional source type hint

        Returns:
            The converted Python value (unchanged in base implementation)
        """
        # Base implementation can't convert to Enum without knowing the Enum class
        return value
