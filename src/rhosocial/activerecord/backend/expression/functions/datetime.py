# src/rhosocial/activerecord/backend/expression/functions/datetime.py
"""Date/Time function factories."""

from typing import Union, Optional, TYPE_CHECKING

from ..bases import BaseExpression
from ..core import (
    Column,
)
from ..datetime import (
    CurrentDateFunction,
    ExtractFieldExpression,
    CurrentTimeFunction,
    CurrentTimestampFunction,
    LocalTimestampFunction,
    NowFunction,
    DatePartExpression,
    DatetimeAddExpression,
    DatetimeDiffExpression,
    DatetimeSubtractExpression,
    DateTruncExpression,
    ExtractExpression,
    IntervalExpression,
)

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


def now(dialect: "SQLDialectBase", precision: Optional[int] = None) -> "NowFunction":
    """
    Creates a NOW scalar function call.

    Args:
        dialect: The SQL dialect instance

    Returns:
        A TimestampValue wrapping NOW
    """
    return NowFunction(dialect, precision)


def current_date(dialect: "SQLDialectBase", precision: Optional[int] = None) -> "CurrentDateFunction":
    """
    Creates a CURRENT_DATE niladic value function.

    SQL:2003 standard niladic function — generates CURRENT_DATE without
    parentheses, as required by the standard.

    Args:
        dialect: The SQL dialect instance
        precision: Optional fractional seconds precision. The standard writes
            this function with no arguments, so this is normally ``None``; a
            backend that spells the scale needs somewhere to read it from.

    Returns:
        A :class:`~...expression.datetime.CurrentDateFunction` node.
    """
    return CurrentDateFunction(dialect, precision)


def current_time(dialect: "SQLDialectBase", precision: Optional[int] = None) -> "CurrentTimeFunction":
    """
    Creates a CURRENT_TIME niladic value function.

    SQL:2003 standard niladic function — generates CURRENT_TIME
    without parentheses, as required by the standard.

    Args:
        dialect: The SQL dialect instance

    Returns:
        A TimeValue wrapping CURRENT_TIME
    """
    return CurrentTimeFunction(dialect, precision)


def year(dialect: "SQLDialectBase", expr: "BaseExpression") -> "ExtractFieldExpression":
    """
    Creates a YEAR scalar function call.

    Usage rules:
    - To generate YEAR(column), pass a Column object: year(dialect, Column(dialect, "column_name"))
    - To generate YEAR(?), pass a numeric value: year(dialect, 2023)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to extract year from. If a numeric value (int/float) is passed,
              it's treated as a literal value. If a BaseExpression is passed, it's used as-is.

    Returns:
        An IntegerValue wrapping YEAR
    """
    target_expr = expr
    return ExtractFieldExpression(dialect, field="year", source=target_expr, spelling="YEAR")


def month(dialect: "SQLDialectBase", expr: "BaseExpression") -> "ExtractFieldExpression":
    """
    Creates a MONTH scalar function call.

    Usage rules:
    - To generate MONTH(column), pass a Column object: month(dialect, Column(dialect, "column_name"))
    - To generate MONTH(?), pass a numeric value: month(dialect, 12)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to extract month from. If a numeric value (int/float)
              is passed, it's treated as a literal value. If a BaseExpression
              is passed, it's used as-is.

    Returns:
        An IntegerValue wrapping MONTH
    """
    target_expr = expr
    return ExtractFieldExpression(dialect, field="month", source=target_expr, spelling="MONTH")


def day(dialect: "SQLDialectBase", expr: "BaseExpression") -> "ExtractFieldExpression":
    """
    Creates a DAY scalar function call.

    Usage rules:
    - To generate DAY(column), pass a Column object: day(dialect, Column(dialect, "column_name"))
    - To generate DAY(?), pass a numeric value: day(dialect, 25)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to extract day from. If a numeric value (int/float) is passed,
              it's treated as a literal value. If a BaseExpression is passed, it's used as-is.

    Returns:
        An IntegerValue wrapping DAY
    """
    target_expr = expr
    return ExtractFieldExpression(dialect, field="day", source=target_expr, spelling="DAY")


def hour(dialect: "SQLDialectBase", expr: "BaseExpression") -> "ExtractFieldExpression":
    """
    Creates an HOUR scalar function call.

    Usage rules:
    - To generate HOUR(column), pass a Column object: hour(dialect, Column(dialect, "column_name"))
    - To generate HOUR(?), pass a numeric value: hour(dialect, 14)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to extract hour from. If a numeric value (int/float) is passed,
              it's treated as a literal value. If a BaseExpression is passed, it's used as-is.

    Returns:
        An IntegerValue wrapping HOUR
    """
    target_expr = expr
    return ExtractFieldExpression(dialect, field="hour", source=target_expr, spelling="HOUR")


def minute(dialect: "SQLDialectBase", expr: "BaseExpression") -> "ExtractFieldExpression":
    """
    Creates a MINUTE scalar function call.

    Usage rules:
    - To generate MINUTE(column), pass a Column object: minute(dialect, Column(dialect, "column_name"))
    - To generate MINUTE(?), pass a numeric value: minute(dialect, 30)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to extract minute from. If a numeric value (int/float) is passed,
              it's treated as a literal value. If a BaseExpression is passed, it's used as-is.

    Returns:
        An IntegerValue wrapping MINUTE
    """
    target_expr = expr
    return ExtractFieldExpression(dialect, field="minute", source=target_expr, spelling="MINUTE")


def second(dialect: "SQLDialectBase", expr: "BaseExpression") -> "ExtractFieldExpression":
    """
    Creates a SECOND scalar function call.

    Usage rules:
    - To generate SECOND(column), pass a Column object: second(dialect, Column(dialect, "column_name"))
    - To generate SECOND(?), pass a numeric value: second(dialect, 45)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to extract second from. If a numeric value (int/float) is passed,
              it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        An IntegerValue wrapping SECOND
    """
    target_expr = expr
    return ExtractFieldExpression(dialect, field="second", source=target_expr, spelling="SECOND")


def date_part(dialect: "SQLDialectBase", field: str, expr: "BaseExpression") -> "DatePartExpression":
    """Creates a DATE_PART expression."""
    target_expr = expr
    return DatePartExpression(dialect, field, target_expr)


def date_trunc(dialect: "SQLDialectBase", field: str, expr: "BaseExpression") -> "DateTruncExpression":
    """Creates a DATE_TRUNC expression."""
    target_expr = expr
    return DateTruncExpression(dialect, field, target_expr)


def current_timestamp(
    dialect: "SQLDialectBase", precision: Optional[int] = None
) -> "CurrentTimestampFunction":
    """
    Creates a CURRENT_TIMESTAMP niladic value function.

    SQL:2003 standard niladic function — generates CURRENT_TIMESTAMP
    without parentheses when no precision is specified. When precision
    is specified, generates CURRENT_TIMESTAMP(precision) with parentheses.

    Usage rules:
    - To generate CURRENT_TIMESTAMP: current_timestamp(dialect)
    - To generate CURRENT_TIMESTAMP(6): current_timestamp(dialect, 6)

    Args:
        dialect: The SQL dialect instance
        precision: Optional fractional seconds precision

    Returns:
        A TimeValue wrapping CURRENT_TIMESTAMP
    """
    return CurrentTimestampFunction(dialect, precision)


def localtimestamp(
    dialect: "SQLDialectBase", precision: Optional[int] = None
) -> "LocalTimestampFunction":
    """
    Creates a LOCALTIMESTAMP niladic value function.

    SQL:2003 standard niladic function — generates LOCALTIMESTAMP
    without parentheses when no precision is specified. When precision
    is specified, generates LOCALTIMESTAMP(precision) with parentheses.

    Usage rules:
    - To generate LOCALTIMESTAMP: localtimestamp(dialect)
    - To generate LOCALTIMESTAMP(6): localtimestamp(dialect, 6)

    Args:
        dialect: The SQL dialect instance
        precision: Optional fractional seconds precision

    Returns:
        A TimestampValue wrapping LOCALTIMESTAMP
    """
    return LocalTimestampFunction(dialect, precision)


def extract(dialect: "SQLDialectBase", field: str, expr: "BaseExpression") -> "ExtractExpression":
    """Creates an EXTRACT expression."""
    target_expr = expr
    return ExtractExpression(dialect, field, target_expr)


def interval(dialect: "SQLDialectBase", value: Union[int, float], unit: str) -> "IntervalExpression":
    """Creates a structured interval expression."""
    return IntervalExpression(dialect, value, unit)


def _ensure_interval(
    dialect: "SQLDialectBase",
    value_or_interval: Union[int, float, "IntervalExpression"],
    unit: Optional[str],
) -> "IntervalExpression":
    if isinstance(value_or_interval, IntervalExpression):
        if unit is not None:
            raise ValueError("unit must not be provided when value_or_interval is IntervalExpression")
        return value_or_interval
    if unit is None:
        raise ValueError("unit is required when value_or_interval is numeric")
    return IntervalExpression(dialect, value_or_interval, unit)


def date_add(
    dialect: "SQLDialectBase",
    expr: "BaseExpression",
    value_or_interval: Union[int, float, "IntervalExpression"],
    unit: Optional[str] = None,
) -> "DatetimeAddExpression":
    """Creates an expression that adds an interval to a datetime expression."""
    target_expr = expr
    interval_expr = _ensure_interval(dialect, value_or_interval, unit)
    return DatetimeAddExpression(dialect, target_expr, interval_expr)


def date_sub(
    dialect: "SQLDialectBase",
    expr: "BaseExpression",
    value_or_interval: Union[int, float, "IntervalExpression"],
    unit: Optional[str] = None,
) -> "DatetimeSubtractExpression":
    """Creates an expression that subtracts an interval from a datetime expression."""
    target_expr = expr
    interval_expr = _ensure_interval(dialect, value_or_interval, unit)
    return DatetimeSubtractExpression(dialect, target_expr, interval_expr)


def date_diff(
    dialect: "SQLDialectBase",
    unit: str,
    start_expr: "BaseExpression",
    end_expr: "BaseExpression",
) -> "DatetimeDiffExpression":
    """Creates an expression for the difference between two datetime expressions."""
    start = start_expr if isinstance(start_expr, BaseExpression) else Column(dialect, start_expr)
    end = end_expr if isinstance(end_expr, BaseExpression) else Column(dialect, end_expr)
    return DatetimeDiffExpression(dialect, unit, start, end)
