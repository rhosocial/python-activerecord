# src/rhosocial/activerecord/backend/impl/sqlite/functions/datetime.py
"""
SQLite date/time function factories.

Functions: date_func, time_func, datetime_func, julianday, strftime_func
"""

from typing import Union, Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.expression import bases, core

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


def date_func(
    dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], *modifiers: str
) -> "core.FunctionCall":
    """
    Creates a DATE function call.

    SQLite's date function with optional modifiers.

    Usage:
        - date_func(dialect, "now") -> DATE('now')
        - date_func(dialect, "now", "+1 day") -> DATE('now', '+1 day')

    Args:
        dialect: The SQL dialect instance
        expr: The date expression or 'now'
        *modifiers: Optional date modifiers

    Returns:
        A FunctionCall instance representing the DATE function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    modifier_exprs = [core.Literal(dialect, m) for m in modifiers]
    return core.FunctionCall(dialect, "DATE", target_expr, *modifier_exprs)


def time_func(
    dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], *modifiers: str
) -> "core.FunctionCall":
    """
    Creates a TIME function call.

    SQLite's time function with optional modifiers.

    Usage:
        - time_func(dialect, "now") -> TIME('now')
        - time_func(dialect, "now", "localtime") -> TIME('now', 'localtime')

    Args:
        dialect: The SQL dialect instance
        expr: The time expression or 'now'
        *modifiers: Optional time modifiers

    Returns:
        A FunctionCall instance representing the TIME function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    modifier_exprs = [core.Literal(dialect, m) for m in modifiers]
    return core.FunctionCall(dialect, "TIME", target_expr, *modifier_exprs)


def datetime_func(
    dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], *modifiers: str
) -> "core.FunctionCall":
    """
    Creates a DATETIME function call.

    SQLite's datetime function with optional modifiers.

    Usage:
        - datetime_func(dialect, "now") -> DATETIME('now')
        - datetime_func(dialect, "now", "localtime") -> DATETIME('now', 'localtime')

    Args:
        dialect: The SQL dialect instance
        expr: The datetime expression or 'now'
        *modifiers: Optional datetime modifiers

    Returns:
        A FunctionCall instance representing the DATETIME function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    modifier_exprs = [core.Literal(dialect, m) for m in modifiers]
    return core.FunctionCall(dialect, "DATETIME", target_expr, *modifier_exprs)


def julianday(
    dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], *modifiers: str
) -> "core.FunctionCall":
    """
    Creates a JULIANDAY function call.

    Returns the Julian day number for a date/time expression.

    Usage:
        - julianday(dialect, "now") -> JULIANDAY('now')
        - julianday(dialect, Column("created_at")) -> JULIANDAY("created_at")

    Args:
        dialect: The SQL dialect instance
        expr: The date expression
        *modifiers: Optional date modifiers

    Returns:
        A FunctionCall instance representing the JULIANDAY function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    modifier_exprs = [core.Literal(dialect, m) for m in modifiers]
    return core.FunctionCall(dialect, "JULIANDAY", target_expr, *modifier_exprs)


def strftime_func(
    dialect: "SQLDialectBase", format_str: str, expr: Union[str, "bases.BaseExpression"], *modifiers: str
) -> "core.FunctionCall":
    """
    Creates a STRFTIME function call.

    SQLite's date/time formatting function.

    Usage:
        - strftime_func(dialect, "%Y-%m-%d", "now") -> STRFTIME('%Y-%m-%d', 'now')
        - strftime_func(dialect, "%H:%M", Column("timestamp")) -> STRFTIME('%H:%M', "timestamp")

    Args:
        dialect: The SQL dialect instance
        format_str: Format string (SQLite strftime format)
        expr: The date/time expression
        *modifiers: Optional date modifiers

    Returns:
        A FunctionCall instance representing the STRFTIME function
    """
    format_expr = core.Literal(dialect, format_str)
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    modifier_exprs = [core.Literal(dialect, m) for m in modifiers]
    return core.FunctionCall(dialect, "STRFTIME", format_expr, target_expr, *modifier_exprs)


__all__ = [
    "date_func",
    "time_func",
    "datetime_func",
    "julianday",
    "strftime_func",
]
