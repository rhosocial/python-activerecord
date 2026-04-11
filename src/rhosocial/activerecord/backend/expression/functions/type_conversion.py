# src/rhosocial/activerecord/backend/expression/functions/type_conversion.py
"""Type conversion function factories."""

from typing import Union, Optional, TYPE_CHECKING

from ..bases import BaseExpression, SQLValueExpression
from ..core import Column, FunctionCall, Literal

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


def cast(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], target_type: str
) -> "SQLValueExpression":
    """
    Creates a type cast on an expression.

    This function applies a type cast using the cast() method on the expression.
    The cast is stored in the _cast_types list and applied during to_sql().

    Usage rules:
    - To generate CAST(column AS type), pass a Column object: cast(dialect, Column(dialect, "column_name"), "INTEGER")
    - To generate CAST("col" AS type), pass a string: cast(dialect, "column_name", "INTEGER")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to cast. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        target_type: The target data type to cast to.

    Returns:
        The expression with the type cast applied (same object, modified in-place)
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    target_expr.cast(target_type)
    return target_expr


def to_char(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], format: Optional[str] = None
) -> "FunctionCall":
    """
    Creates a TO_CHAR function call.

    Usage rules:
    - To generate TO_CHAR(column), pass a Column object:
      to_char(dialect, Column(dialect, "date_col"))
    - To generate TO_CHAR(column, format), pass a format string:
      to_char(dialect, Column(dialect, "date_col"), "YYYY-MM-DD")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to convert to character. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        format: Optional format string for conversion.

    Returns:
        A FunctionCall instance representing the TO_CHAR function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    if format is not None:
        format_expr = Literal(dialect, format)
        return FunctionCall(dialect, "TO_CHAR", target_expr, format_expr)
    return FunctionCall(dialect, "TO_CHAR", target_expr)


def to_number(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], format: Optional[str] = None
) -> "FunctionCall":
    """
    Creates a TO_NUMBER function call.

    Usage rules:
    - To generate TO_NUMBER(column), pass a Column object:
      to_number(dialect, Column(dialect, "char_col"))
    - To generate TO_NUMBER(column, format), pass a format string:
      to_number(dialect, Column(dialect, "char_col"), "9999")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to convert to number. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        format: Optional format string for conversion.

    Returns:
        A FunctionCall instance representing the TO_NUMBER function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    if format is not None:
        format_expr = Literal(dialect, format)
        return FunctionCall(dialect, "TO_NUMBER", target_expr, format_expr)
    return FunctionCall(dialect, "TO_NUMBER", target_expr)


def to_date(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], format: Optional[str] = None
) -> "FunctionCall":
    """
    Creates a TO_DATE function call.

    Usage rules:
    - To generate TO_DATE(column), pass a Column object:
      to_date(dialect, Column(dialect, "char_col"))
    - To generate TO_DATE(column, format), pass a format string:
      to_date(dialect, Column(dialect, "char_col"), "YYYY-MM-DD")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to convert to date. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        format: Optional format string for conversion.

    Returns:
        A FunctionCall instance representing the TO_DATE function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    if format is not None:
        format_expr = Literal(dialect, format)
        return FunctionCall(dialect, "TO_DATE", target_expr, format_expr)
    return FunctionCall(dialect, "TO_DATE", target_expr)
