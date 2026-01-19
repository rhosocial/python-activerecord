# src/rhosocial/activerecord/backend/type_adapter.py
"""
This module implements the SQLTypeAdapter protocol and various standard
type adapters for converting between Python and database values.

Key principles from the design:
1.  **Simplicity**: No async converters, as type conversion is CPU-bound.
2.  **Exact Matching**: Converters are for specific (Python type, DB type) pairs.
3.  **Stateless**: Converters should be stateless and thread-safe.

Defined Type Adapters:
- DateTimeAdapter: Converts between Python datetime/date/time and SQL types (str, int, float).
- JSONAdapter: Converts between Python dict/list and SQL JSON (string).
- UUIDAdapter: Converts between Python UUID and SQL string.
- EnumAdapter: Converts between Python Enum and SQL types (str, int).
- BooleanAdapter: Converts between Python bool and SQL types (int, str).
- DecimalAdapter: Converts between Python Decimal and SQL types (str, float).
- ArrayAdapter: Converts between Python list and SQL string (JSON representation). Does not register default types; intended for explicit use.
"""

from abc import ABC, abstractmethod
from datetime import datetime, date, time
from enum import Enum
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Protocol,
    Set,
    Type,
    Union,
    get_args,
    get_origin,
    runtime_checkable,
)
import json
from uuid import UUID
from decimal import Decimal, ROUND_HALF_UP


@runtime_checkable
class SQLTypeAdapter(Protocol):
    """
    Protocol for type conversion between Python and database values.
    Implementations must be stateless and thread-safe.
    """

    def to_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Converts a Python value to a database-compatible value."""
        ...

    def from_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Converts a database value to a Python value."""
        ...

    @property
    def supported_types(self) -> Dict[Type, Set[Type]]:
        """
        Returns a dictionary of supported type mappings.
        Format: {python_type: {db_type1, db_type2, ...}}
        """
        ...


class BatchConversionMixin:
    """
    Mixin providing batch conversion capabilities.
    This can be overridden by specific adapters for more optimized batch processing.
    """

    def to_database_batch(
        self,
        values: List[Any],
        target_type: Type,
        options: Optional[Dict[str, Any]] = None,
    ) -> List[Any]:
        """Batch converts Python values to database values."""
        # This is a naive implementation. A real implementation could optimize
        # by passing options to each call if needed.
        return [
            self.to_database(value, target_type, options) for value in values
        ]

    def from_database_batch(
        self,
        values: List[Any],
        target_type: Type,
        options: Optional[Dict[str, Any]] = None,
    ) -> List[Any]:
        """Batch converts database values to Python values."""
        return [
            self.from_database(value, target_type, options) for value in values
        ]


class BaseSQLTypeAdapter(ABC, BatchConversionMixin):
    """
    Base class for SQL type adapters.
    Handles None values and provides a helper for registering supported types.
    """

    def __init__(self):
        self._supported_types: Dict[Type, Set[Type]] = {}

    @property
    def supported_types(self) -> Dict[Type, Set[Type]]:
        return self._supported_types

    def _register_type(self, py_type: Type, db_type: Type) -> None:
        """Registers a supported (Python type, DB type) pair."""
        if py_type not in self._supported_types:
            self._supported_types[py_type] = set()
        self._supported_types[py_type].add(db_type)

    def to_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None
    ) -> Any:
        if value is None:
            return None
        return self._do_to_database(value, target_type, options)

    def from_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None
    ) -> Any:
        if value is None:
            return None

        origin = get_origin(target_type)
        if origin is Union:
            args = get_args(target_type)
            # Filter out NoneType
            non_none_args = [arg for arg in args if arg is not type(None)]
            if len(non_none_args) == 1:
                target_type = non_none_args[0]

        return self._do_from_database(value, target_type, options)

    @abstractmethod
    def _do_to_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Any:
        """Actual conversion logic for non-None values (to database)."""
        pass

    @abstractmethod
    def _do_from_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Any:
        """Actual conversion logic for non-None values (from database)."""
        pass


# --- Standard SQL Type Adapter Presets ---


class DateTimeAdapter(BaseSQLTypeAdapter):
    """Converts between Python datetime objects and SQL types (str, int, float)."""

    def __init__(self):
        super().__init__()
        self._register_type(datetime, str)
        self._register_type(datetime, int)
        self._register_type(datetime, float)
        self._register_type(date, str)
        self._register_type(date, int)
        self._register_type(time, str)

    def _do_to_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Any:
        if isinstance(value, datetime):
            if target_type == str:
                return value.isoformat()
            elif target_type in (int, float):
                return value.timestamp()
        elif isinstance(value, date):
            if target_type == str:
                return value.isoformat()
            elif target_type == int:
                return int(datetime.combine(value, time.min).timestamp())
        elif isinstance(value, time):
            if target_type == str:
                return value.isoformat()
        raise TypeError(f"Cannot convert {type(value).__name__} to {getattr(target_type, '__name__', repr(target_type))}")

    def _do_from_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Any:
        if target_type == datetime:
            if isinstance(value, datetime):
                return value
            if isinstance(value, (int, float)):
                return datetime.fromtimestamp(value)
            elif isinstance(value, str):
                return datetime.fromisoformat(value)
        elif target_type == date:
            if isinstance(value, date):
                return value
            if isinstance(value, (int, float)):
                return date.fromtimestamp(value)
            elif isinstance(value, str):
                return date.fromisoformat(value)
        elif target_type == time:
            if isinstance(value, time):
                return value
            if isinstance(value, str):
                return time.fromisoformat(value)
        raise TypeError(f"Cannot convert {type(value).__name__} to {getattr(target_type, '__name__', repr(target_type))}")


class JSONAdapter(BaseSQLTypeAdapter):
    """Converts between Python dict/list and SQL JSON (usually string)."""

    def __init__(self):
        super().__init__()
        self._register_type(dict, str)
        self._register_type(list, str)

    def _do_to_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Any:
        if target_type == str:
            return json.dumps(value)
        raise TypeError(f"Cannot convert {type(value).__name__} to {getattr(target_type, '__name__', repr(target_type))}")

    def _do_from_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Any:
        if isinstance(value, str):
            return json.loads(value)
        raise TypeError(f"Cannot convert {type(value).__name__} to {getattr(target_type, '__name__', repr(target_type))}")


class UUIDAdapter(BaseSQLTypeAdapter):
    """Converts between Python UUID and SQL string."""

    def __init__(self):
        super().__init__()
        self._register_type(UUID, str)

    def _do_to_database(
        self, value: UUID, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Any:
        if target_type == str:
            return str(value)
        raise TypeError(f"Cannot convert {type(value).__name__} to {getattr(target_type, '__name__', repr(target_type))}")

    def _do_from_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Any:
        if target_type == UUID:
            if isinstance(value, UUID):
                return value
            # Only allow conversion from str and bytes, which are unambiguous.
            if isinstance(value, (str, bytes)):
                try:
                    return UUID(value)
                except ValueError as e:
                    # Catch cases like "not-a-uuid"
                    raise TypeError(f"Cannot convert {type(value).__name__} to UUID: {e}") from e
        # For any other type (like int), fall through and raise the TypeError.
        raise TypeError(f"Cannot convert {type(value).__name__} to {getattr(target_type, '__name__', repr(target_type))}")


class EnumAdapter(BaseSQLTypeAdapter):
    """Converts between Python Enum and SQL types (str, int)."""

    def __init__(self):
        super().__init__()
        # This adapter is generic; registration happens in the backend
        # based on the actual Enum type. We can't know the specific Enum class here.

    def _do_to_database(
        self, value: Enum, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Any:
        if target_type == str:
            return value.name
        if target_type == int:
            return value.value
        raise TypeError(f"Cannot convert {type(value).__name__} to {getattr(target_type, '__name__', repr(target_type))}")

    def _do_from_database(
        self, value: Any, target_type: Type[Enum], options: Optional[Dict[str, Any]]
    ) -> Any:
        # The target_type is the actual Enum class
        if isinstance(value, str):
            return target_type[value]
        if isinstance(value, int):
            return target_type(value)
        raise TypeError(f"Cannot convert {type(value).__name__} to {getattr(target_type, '__name__', repr(target_type))}")


class BooleanAdapter(BaseSQLTypeAdapter):
    """Converts between Python bool and SQL types (int, str)."""

    def __init__(self):
        super().__init__()
        self._register_type(bool, int)
        self._register_type(bool, str)

    def _do_to_database(
        self, value: bool, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Any:
        if target_type == int:
            return 1 if value else 0
        if target_type == str:
            return str(value).lower()  # 'true' or 'false'
        raise TypeError(f"Cannot convert {type(value).__name__} to {getattr(target_type, '__name__', repr(target_type))}")

    def _do_from_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Any:
        if target_type == bool:
            if isinstance(value, int):
                return bool(value)
            if isinstance(value, str):
                return value.lower() == 'true'
        raise TypeError(f"Cannot convert {type(value).__name__} to {getattr(target_type, '__name__', repr(target_type))}")


class DecimalAdapter(BaseSQLTypeAdapter):
    """
    Converts between Python Decimal and SQL types (str, float).
    Supports a 'precision' option for quantization.

    Rationale for dedicated adapter:
    While native Python `int` and `float` types typically map directly to
    corresponding database types through the driver without explicit ORM
    adapter intervention, `Decimal` requires special handling. This is
    because `Decimal` preserves exact precision, which standard `float`
    types do not. This adapter ensures that `Decimal` values are correctly
    and precisely converted to/from database representations (like `TEXT`
    or `REAL`), preventing loss of precision that might occur with default
    `float` conversions.
    """

    def __init__(self):
        super().__init__()
        self._register_type(Decimal, str)
        self._register_type(Decimal, float)

    def _do_to_database(
        self, value: Decimal, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Any:
        if target_type == str:
            return str(value)
        if target_type == float:
            return float(value)
        raise TypeError(f"Cannot convert {type(value).__name__} to {getattr(target_type, '__name__', repr(target_type))}")

    def _do_from_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Any:
        if target_type == Decimal:
            if isinstance(value, (str, float, int)):
                decimal_value = Decimal(str(value))
                if options and 'precision' in options:
                    precision = Decimal(options['precision'])
                    rounding = options.get('rounding', ROUND_HALF_UP)
                    return decimal_value.quantize(precision, rounding=rounding)
                return decimal_value
        raise TypeError(f"Cannot convert {type(value).__name__} to {getattr(target_type, '__name__', repr(target_type))}")


class ArrayAdapter(BaseSQLTypeAdapter):
    """
    Converts between Python list and SQL string (JSON representation).
    Does not register default types to avoid conflict with JSONAdapter;
    intended for explicit use via column_adapters or custom registration.
    """

    def __init__(self):
        super().__init__()
        # Removed default registration to avoid conflict with JSONAdapter
        # self._register_type(list, str) 

    def _do_to_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Any:
        if target_type == str:
            if isinstance(value, (list, tuple, set)): # Explicitly check for array-like types
                return json.dumps(list(value)) # Convert sets to list for JSON
            raise TypeError(f"Cannot convert {type(value).__name__} to JSON array string.")
        raise TypeError(f"Cannot convert {type(value).__name__} to {getattr(target_type, '__name__', repr(target_type))}")

    def _do_from_database(
        self, value: str, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Any:
        if target_type == list:
            return json.loads(value)
        raise TypeError(f"Cannot convert {type(value).__name__} to {getattr(target_type, '__name__', repr(target_type))}")