# src/rhosocial/activerecord/backend/expression/functions/datetime.py
"""Date/Time function factories."""

from typing import Union, Optional, TYPE_CHECKING

from ..bases import BaseExpression
from ..core import Column, FunctionCall, Literal
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


def date_part(dialect: "SQLDialectBase", field: str, expr: Union[str, "BaseExpression"]) -> "FunctionCall":
    """
    Creates a DATE_PART scalar function call.

    Usage rules:
    - To generate DATE_PART(field, column), pass a Column object:
      date_part(dialect, "year", Column(dialect, "date_col"))
    - To generate DATE_PART(field, ?), pass a literal value:
      date_part(dialect, "month", "2023-01-01")

    Args:
        dialect: The SQL dialect instance
        field: The date part field (e.g., "year", "month", "day", "hour", "minute", "second")
        expr: The expression to extract date part from. If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the DATE_PART function
    """
    field_expr = Literal(dialect, field)
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    return FunctionCall(dialect, "DATE_PART", field_expr, target_expr)


def date_trunc(dialect: "SQLDialectBase", field: str, expr: Union[str, "BaseExpression"]) -> "FunctionCall":
    """
    Creates a DATE_TRUNC scalar function call.

    Usage rules:
    - To generate DATE_TRUNC(field, column), pass a Column object:
      date_trunc(dialect, "month", Column(dialect, "date_col"))
    - To generate DATE_TRUNC(field, ?), pass a literal value
      date_trunc(dialect, "day", "2023-01-01 14:30:00")

    Args:
        dialect: The SQL dialect instance
        field: The date part field to truncate to (e.g., "year", "month", "day", "hour", "minute")
        expr: The expression to truncate. If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the DATE_TRUNC function
    """
    field_expr = Literal(dialect, field)
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    return FunctionCall(dialect, "DATE_TRUNC", field_expr, target_expr)


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


def extract(dialect: "SQLDialectBase", field: str, expr: Union[str, "BaseExpression"]) -> "FunctionCall":
    """
    Creates an EXTRACT function call.

    SQL:2003 standard function extracting datetime fields.

    Usage rules:
    - To generate EXTRACT(YEAR FROM column): extract(dialect, "YEAR", Column("date"))
    - To generate EXTRACT(MONTH FROM CURRENT_DATE): extract(dialect, "MONTH", "CURRENT_DATE")

    Args:
        dialect: The SQL dialect instance
        field: The field to extract (YEAR, MONTH, DAY, HOUR, MINUTE, SECOND, etc.)
        expr: The datetime expression

    Returns:
        A FunctionCall instance representing the EXTRACT function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Literal(dialect, expr)
    return FunctionCall(dialect, "EXTRACT", Literal(dialect, field), target_expr)
