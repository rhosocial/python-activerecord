# src/rhosocial/activerecord/backend/expression/functions/datetime.py
"""Date/Time function factories."""

from typing import Union, Optional, TYPE_CHECKING

from ..bases import BaseExpression
from ..core import Column, FunctionCall, Literal
from ..datetime import (
    DatePartExpression,
    DateTimeAddExpression,
    DateTimeDiffExpression,
    DateTimeSubtractExpression,
    DateTruncExpression,
    ExtractExpression,
    IntervalExpression,
)
from ._utils import _convert_to_expression

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


def now(dialect: "SQLDialectBase") -> "FunctionCall":
    """
    Creates a NOW scalar function call.

    Args:
        dialect: The SQL dialect instance

    Returns:
        A FunctionCall instance representing the NOW function
    """
    return FunctionCall(dialect, "NOW")


def current_date(dialect: "SQLDialectBase") -> "FunctionCall":
    """
    Creates a CURRENT_DATE niladic value function.

    SQL:2003 standard niladic function — generates CURRENT_TIMESTAMP
    without parentheses, as required by the standard.

    Args:
        dialect: The SQL dialect instance

    Returns:
        A FunctionCall instance representing the CURRENT_DATE value function
    """
    return FunctionCall(dialect, "CURRENT_DATE", niladic=True)


def current_time(dialect: "SQLDialectBase") -> "FunctionCall":
    """
    Creates a CURRENT_TIME niladic value function.

    SQL:2003 standard niladic function — generates CURRENT_TIME
    without parentheses, as required by the standard.

    Args:
        dialect: The SQL dialect instance

    Returns:
        A FunctionCall instance representing the CURRENT_TIME value function
    """
    return FunctionCall(dialect, "CURRENT_TIME", niladic=True)


def year(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "FunctionCall":
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
        A FunctionCall instance representing the YEAR function
    """
    target_expr = _convert_to_expression(dialect, expr, handle_numeric_literals=True)
    return FunctionCall(dialect, "YEAR", target_expr)


def month(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "FunctionCall":
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
        A FunctionCall instance representing the MONTH function
    """
    target_expr = _convert_to_expression(dialect, expr, handle_numeric_literals=True)
    return FunctionCall(dialect, "MONTH", target_expr)


def day(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "FunctionCall":
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
        A FunctionCall instance representing the DAY function
    """
    target_expr = _convert_to_expression(dialect, expr, handle_numeric_literals=True)
    return FunctionCall(dialect, "DAY", target_expr)


def hour(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "FunctionCall":
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
        A FunctionCall instance representing the HOUR function
    """
    target_expr = _convert_to_expression(dialect, expr, handle_numeric_literals=True)
    return FunctionCall(dialect, "HOUR", target_expr)


def minute(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "FunctionCall":
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
        A FunctionCall instance representing the MINUTE function
    """
    target_expr = _convert_to_expression(dialect, expr, handle_numeric_literals=True)
    return FunctionCall(dialect, "MINUTE", target_expr)


def second(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "FunctionCall":
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
        A FunctionCall instance representing the SECOND function
    """
    target_expr = _convert_to_expression(dialect, expr, handle_numeric_literals=True)
    return FunctionCall(dialect, "SECOND", target_expr)


def date_part(dialect: "SQLDialectBase", field: str, expr: Union[str, "BaseExpression"]) -> "DatePartExpression":
    """Creates a DATE_PART expression."""
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    return DatePartExpression(dialect, field, target_expr)


def date_trunc(dialect: "SQLDialectBase", field: str, expr: Union[str, "BaseExpression"]) -> "DateTruncExpression":
    """Creates a DATE_TRUNC expression."""
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    return DateTruncExpression(dialect, field, target_expr)


def current_timestamp(dialect: "SQLDialectBase", precision: Optional[int] = None) -> "FunctionCall":
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
        A FunctionCall instance representing the CURRENT_TIMESTAMP value function
    """
    if precision is not None:
        return FunctionCall(dialect, "CURRENT_TIMESTAMP", Literal(dialect, precision))
    return FunctionCall(dialect, "CURRENT_TIMESTAMP", niladic=True)


def localtimestamp(dialect: "SQLDialectBase", precision: Optional[int] = None) -> "FunctionCall":
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
        A FunctionCall instance representing the LOCALTIMESTAMP value function
    """
    if precision is not None:
        return FunctionCall(dialect, "LOCALTIMESTAMP", Literal(dialect, precision))
    return FunctionCall(dialect, "LOCALTIMESTAMP", niladic=True)


def extract(dialect: "SQLDialectBase", field: str, expr: Union[str, "BaseExpression"]) -> "ExtractExpression":
    """Creates an EXTRACT expression."""
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
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
    expr: Union[str, "BaseExpression"],
    value_or_interval: Union[int, float, "IntervalExpression"],
    unit: Optional[str] = None,
) -> "DateTimeAddExpression":
    """Creates an expression that adds an interval to a datetime expression."""
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    interval_expr = _ensure_interval(dialect, value_or_interval, unit)
    return DateTimeAddExpression(dialect, target_expr, interval_expr)


def date_sub(
    dialect: "SQLDialectBase",
    expr: Union[str, "BaseExpression"],
    value_or_interval: Union[int, float, "IntervalExpression"],
    unit: Optional[str] = None,
) -> "DateTimeSubtractExpression":
    """Creates an expression that subtracts an interval from a datetime expression."""
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    interval_expr = _ensure_interval(dialect, value_or_interval, unit)
    return DateTimeSubtractExpression(dialect, target_expr, interval_expr)


def date_diff(
    dialect: "SQLDialectBase",
    unit: str,
    start_expr: Union[str, "BaseExpression"],
    end_expr: Union[str, "BaseExpression"],
) -> "DateTimeDiffExpression":
    """Creates an expression for the difference between two datetime expressions."""
    start = start_expr if isinstance(start_expr, BaseExpression) else Column(dialect, start_expr)
    end = end_expr if isinstance(end_expr, BaseExpression) else Column(dialect, end_expr)
    return DateTimeDiffExpression(dialect, unit, start, end)
