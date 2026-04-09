# src/rhosocial/activerecord/backend/impl/sqlite/functions/conditional.py
"""
SQLite conditional function factories.

Functions: iif
"""

from typing import Union, TYPE_CHECKING

from rhosocial.activerecord.backend.expression import bases, core

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


def iif(
    dialect: "SQLDialectBase",
    condition: "bases.BaseExpression",
    true_value: Union[str, "bases.BaseExpression"],
    false_value: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """
    Creates an IIF function call (SQLite's inline IF).

    SQLite-specific shorthand for CASE WHEN ... THEN ... ELSE ... END.

    Usage:
        - iif(dialect, Column("active") > 0, "yes", "no") -> IIF("active" > 0, 'yes', 'no')

    Args:
        dialect: The SQL dialect instance
        condition: The condition expression
        true_value: Value if condition is true
        false_value: Value if condition is false

    Returns:
        A FunctionCall instance representing the IIF function
    """
    true_expr = true_value if isinstance(true_value, bases.BaseExpression) else core.Literal(dialect, true_value)
    false_expr = false_value if isinstance(false_value, bases.BaseExpression) else core.Literal(dialect, false_value)
    return core.FunctionCall(dialect, "IIF", condition, true_expr, false_expr)


__all__ = [
    "iif",
]
