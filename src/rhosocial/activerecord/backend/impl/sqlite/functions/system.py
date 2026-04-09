# src/rhosocial/activerecord/backend/impl/sqlite/functions/system.py
"""
SQLite system and type function factories.

Functions: typeof, quote, last_insert_rowid, changes
"""

from typing import Union, TYPE_CHECKING

from rhosocial.activerecord.backend.expression import bases, core

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


def typeof(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a TYPEOF function call.

    Returns the storage type of the expression.

    Usage:
        - typeof(dialect, Column("data")) -> TYPEOF("data")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to check type of

    Returns:
        A FunctionCall instance representing the TYPEOF function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    return core.FunctionCall(dialect, "TYPEOF", target_expr)


def quote(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a QUOTE function call.

    Returns the SQL literal representation of the expression.

    Usage:
        - quote(dialect, Column("value")) -> QUOTE("value")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to quote

    Returns:
        A FunctionCall instance representing the QUOTE function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    return core.FunctionCall(dialect, "QUOTE", target_expr)


def last_insert_rowid(dialect: "SQLDialectBase") -> "core.FunctionCall":
    """
    Creates a LAST_INSERT_ROWID function call.

    Returns the ROWID of the most recent successful INSERT.

    Usage:
        - last_insert_rowid(dialect) -> LAST_INSERT_ROWID()

    Args:
        dialect: The SQL dialect instance

    Returns:
        A FunctionCall instance representing the LAST_INSERT_ROWID function
    """
    return core.FunctionCall(dialect, "LAST_INSERT_ROWID")


def changes(dialect: "SQLDialectBase") -> "core.FunctionCall":
    """
    Creates a CHANGES function call.

    Returns the number of rows modified by the most recent INSERT, UPDATE, or DELETE.

    Usage:
        - changes(dialect) -> CHANGES()

    Args:
        dialect: The SQL dialect instance

    Returns:
        A FunctionCall instance representing the CHANGES function
    """
    return core.FunctionCall(dialect, "CHANGES")


__all__ = [
    "typeof",
    "quote",
    "last_insert_rowid",
    "changes",
]
