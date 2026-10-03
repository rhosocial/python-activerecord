# src/rhosocial/activerecord/backend/expression/functions/datetime.py
"""Date/Time function factories."""

from typing import Union, Optional, TYPE_CHECKING

from ..bases import BaseExpression
from ..value_types import DATE, DATETIME, TIME
from ..core import (
    Column,
    DateTimeValueExpression,
    FunctionCall,
    IntegerValueExpression,
    Literal,
)
from ..datetime import (
    DatePartExpression,
    DateTimeAddExpression,
    DateTimeDiffExpression,
    DateTimeSubtractExpression,
    DateTruncExpression,
    ExtractExpression,
    IntervalExpression,
)

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


def now(dialect: "SQLDialectBase") -> "DateTimeValueExpression":
    """
    Creates a NOW scalar function call.

    Args:
        dialect: The SQL dialect instance

    Returns:
        A DateTimeValueExpression wrapping NOW
    """
    return DateTimeValueExpression(dialect, FunctionCall(dialect, 'NOW'))


def current_date(dialect: "SQLDialectBase") -> "DateTimeValueExpression":
    """
    Creates a CURRENT_DATE niladic value function.

    SQL:2003 standard niladic function — generates CURRENT_TIMESTAMP
    without parentheses, as required by the standard.

    Args:
        dialect: The SQL dialect instance

    Returns:
        A DateTimeValueExpression wrapping CURRENT_DATE
    """
    return DateTimeValueExpression(dialect, FunctionCall(dialect, 'CURRENT_DATE', niladic=True), family=DATE)


def current_time(dialect: "SQLDialectBase") -> "DateTimeValueExpression":
    """
    Creates a CURRENT_TIME niladic value function.

    SQL:2003 standard niladic function — generates CURRENT_TIME
    without parentheses, as required by the standard.

    Args:
        dialect: The SQL dialect instance

    Returns:
        A DateTimeValueExpression wrapping CURRENT_TIME
    """
    return DateTimeValueExpression(dialect, FunctionCall(dialect, 'CURRENT_TIME', niladic=True), family=TIME)


def year(dialect: "SQLDialectBase", expr: "BaseExpression") -> "IntegerValueExpression":
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
        An IntegerValueExpression wrapping YEAR
    """
    target_expr = expr
    return IntegerValueExpression(dialect, FunctionCall(dialect, 'YEAR', target_expr))


def month(dialect: "SQLDialectBase", expr: "BaseExpression") -> "IntegerValueExpression":
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
        An IntegerValueExpression wrapping MONTH
    """
    target_expr = expr
    return IntegerValueExpression(dialect, FunctionCall(dialect, 'MONTH', target_expr))


def day(dialect: "SQLDialectBase", expr: "BaseExpression") -> "IntegerValueExpression":
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
        An IntegerValueExpression wrapping DAY
    """
    target_expr = expr
    return IntegerValueExpression(dialect, FunctionCall(dialect, 'DAY', target_expr))


def hour(dialect: "SQLDialectBase", expr: "BaseExpression") -> "IntegerValueExpression":
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
        An IntegerValueExpression wrapping HOUR
    """
    target_expr = expr
    return IntegerValueExpression(dialect, FunctionCall(dialect, 'HOUR', target_expr))


def minute(dialect: "SQLDialectBase", expr: "BaseExpression") -> "IntegerValueExpression":
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
        An IntegerValueExpression wrapping MINUTE
    """
    target_expr = expr
    return IntegerValueExpression(dialect, FunctionCall(dialect, 'MINUTE', target_expr))


def second(dialect: "SQLDialectBase", expr: "BaseExpression") -> "IntegerValueExpression":
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
        An IntegerValueExpression wrapping SECOND
    """
    target_expr = expr
    return IntegerValueExpression(dialect, FunctionCall(dialect, 'SECOND', target_expr))


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
) -> "DateTimeValueExpression":
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
        A DateTimeValueExpression wrapping CURRENT_TIMESTAMP
    """
    if precision is not None:
        return FunctionCall(dialect, "CURRENT_TIMESTAMP", Literal(dialect, precision))
    return DateTimeValueExpression(dialect, FunctionCall(dialect, 'CURRENT_TIMESTAMP', niladic=True), family=DATETIME)


def localtimestamp(
    dialect: "SQLDialectBase", precision: Optional[int] = None
) -> "DateTimeValueExpression":
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
        A DateTimeValueExpression wrapping LOCALTIMESTAMP
    """
    if precision is not None:
        return FunctionCall(dialect, "LOCALTIMESTAMP", Literal(dialect, precision))
    return DateTimeValueExpression(dialect, FunctionCall(dialect, 'LOCALTIMESTAMP', niladic=True), family=DATETIME)


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
) -> "DateTimeAddExpression":
    """Creates an expression that adds an interval to a datetime expression."""
    target_expr = expr
    interval_expr = _ensure_interval(dialect, value_or_interval, unit)
    return DateTimeAddExpression(dialect, target_expr, interval_expr)


def date_sub(
    dialect: "SQLDialectBase",
    expr: "BaseExpression",
    value_or_interval: Union[int, float, "IntervalExpression"],
    unit: Optional[str] = None,
) -> "DateTimeSubtractExpression":
    """Creates an expression that subtracts an interval from a datetime expression."""
    target_expr = expr
    interval_expr = _ensure_interval(dialect, value_or_interval, unit)
    return DateTimeSubtractExpression(dialect, target_expr, interval_expr)


def date_diff(
    dialect: "SQLDialectBase",
    unit: str,
    start_expr: "BaseExpression",
    end_expr: "BaseExpression",
) -> "DateTimeDiffExpression":
    """Creates an expression for the difference between two datetime expressions."""
    start = start_expr if isinstance(start_expr, BaseExpression) else Column(dialect, start_expr)
    end = end_expr if isinstance(end_expr, BaseExpression) else Column(dialect, end_expr)
    return DateTimeDiffExpression(dialect, unit, start, end)
