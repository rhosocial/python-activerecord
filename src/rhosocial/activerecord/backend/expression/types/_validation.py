# src/rhosocial/activerecord/backend/expression/types/_validation.py
"""
Range validation for DataType constructor parameters.

Type parameters (VARCHAR length, DECIMAL precision/scale, TIME precision)
are concatenated verbatim into DDL statements, so they must be validated
before rendering. Validation is enumeration-and-range based — no regular
expressions — and fails fast at declaration time, so a bad parameter can
never reach the dialect's ``format_data_type()``.

Layers:
- *Core* types (this package) enforce the SQL-standard ranges: length ≥ 1,
  FLOAT precision 1–53, DECIMAL precision ≥ 1 with 0 ≤ scale ≤ precision,
  datetime precision 0–9.
- *Backend* subtypes may tighten (never loosen) the ranges via the same
  helpers, e.g. a MySQL VARCHAR subtype can cap ``length`` at 65535.
"""

from typing import Optional

# Literal decimal digits for the char-by-char integer check.
_DECIMAL_DIGITS = frozenset("0123456789")


class DataTypeRangeError(ValueError):
    """Raised when a DataType constructor parameter is outside its valid range."""


def require_int(value, type_name: str, param: str) -> int:
    """Require ``value`` to be a plain int (bool excluded), char-verified.

    bool is a subclass of int in Python and is rejected explicitly, as are
    floats and strings. The value is additionally verified digit-by-digit
    against the literal digit set, so exotic int subclasses that override
    ``__str__`` cannot smuggle arbitrary text into DDL.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise DataTypeRangeError(
            f"{type_name} {param} must be an int, got {type(value).__name__}: {value!r}"
        )
    if any(ch not in _DECIMAL_DIGITS for ch in str(abs(value))):
        raise DataTypeRangeError(
            f"{type_name} {param} contains non-digit characters: {value!r}"
        )
    return value


def require_optional_int(value, type_name: str, param: str) -> Optional[int]:
    """None-tolerant variant of :func:`require_int`."""
    if value is None:
        return None
    return require_int(value, type_name, param)


def require_range(value, type_name: str, param: str,
                  minimum: int, maximum: Optional[int] = None) -> int:
    """Require a mandatory int within ``[minimum, maximum]`` inclusive."""
    require_int(value, type_name, param)
    if value < minimum:
        raise DataTypeRangeError(
            f"{type_name} {param} must be >= {minimum}, got {value}"
        )
    if maximum is not None and value > maximum:
        raise DataTypeRangeError(
            f"{type_name} {param} must be <= {maximum}, got {value}"
        )
    return value


def require_optional_range(value, type_name: str, param: str,
                           minimum: int, maximum: Optional[int] = None) -> Optional[int]:
    """None-tolerant variant of :func:`require_range`."""
    if value is None:
        return None
    return require_range(value, type_name, param, minimum, maximum)


# SQL-standard ranges shared by the core types.
LENGTH_MIN = 1
FLOAT_PRECISION_MIN, FLOAT_PRECISION_MAX = 1, 53
DATETIME_PRECISION_MIN, DATETIME_PRECISION_MAX = 0, 9


__all__ = [
    "DataTypeRangeError",
    "require_int",
    "require_optional_int",
    "require_range",
    "require_optional_range",
    "LENGTH_MIN",
    "FLOAT_PRECISION_MIN",
    "FLOAT_PRECISION_MAX",
    "DATETIME_PRECISION_MIN",
    "DATETIME_PRECISION_MAX",
]
