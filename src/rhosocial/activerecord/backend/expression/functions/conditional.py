# src/rhosocial/activerecord/backend/expression/functions/conditional.py
"""Conditional function factories."""

from typing import Union, Optional, TYPE_CHECKING

from ..bases import BaseExpression
from ..core import FunctionCall, Literal
from ..advanced_functions import CaseExpression

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


def case(
    dialect: "SQLDialectBase", value: Optional["BaseExpression"] = None, alias: Optional[str] = None
) -> "CaseExpression":
    """
    Creates a CASE expression.

    Args:
        dialect: The SQL dialect instance
        value: Optional value to compare against in searched CASE. If provided, used as the base expression.
        alias: Optional alias for the result.

    Returns:
        A CaseExpression instance representing the CASE expression
    """
    return CaseExpression(dialect, value=value, alias=alias)


def nullif(
    dialect: "SQLDialectBase", value: Union[str, "BaseExpression"], null_value: Union[str, "BaseExpression"]
) -> "FunctionCall":
    """
    Creates a NULLIF scalar function call.

    Usage rules:
    - To generate NULLIF(column, null_val), pass Column objects:
      nullif(dialect, Column(dialect, "col1"), Column(dialect, "col2"))
    - To generate NULLIF(?, ?), pass literal values
      nullif(dialect, "value", "null_value")

    Args:
        dialect: The SQL dialect instance
        value: The value to compare. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.
        null_value: The value to compare against. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the NULLIF function
    """
    value_expr = value if isinstance(value, BaseExpression) else Literal(dialect, value)
    null_expr = null_value if isinstance(null_value, BaseExpression) else Literal(dialect, null_value)
    return FunctionCall(dialect, "NULLIF", value_expr, null_expr)


def greatest(dialect: "SQLDialectBase", *exprs: Union[str, "BaseExpression"]) -> "FunctionCall":
    """
    Creates a GREATEST scalar function call.

    Usage rules:
    - To generate GREATEST(column1, column2, ...), pass Column objects:
      greatest(dialect, Column(dialect, "col1"), Column(dialect, "col2"))
    - To generate GREATEST(?, ?, ...), pass literal values
      greatest(dialect, "val1", "val2", "val3")

    Args:
        dialect: The SQL dialect instance
        *exprs: Variable number of expressions to compare. If strings are passed, they're treated as literal values.
                If BaseExpressions are passed, they're used as-is.

    Returns:
        A FunctionCall instance representing the GREATEST function
    """
    target_exprs = [e if isinstance(e, BaseExpression) else Literal(dialect, e) for e in exprs]
    return FunctionCall(dialect, "GREATEST", *target_exprs)


def least(dialect: "SQLDialectBase", *exprs: Union[str, "BaseExpression"]) -> "FunctionCall":
    """
    Creates a LEAST scalar function call.

    Usage rules:
    - To generate LEAST(column1, column2, ...), pass Column objects:
      least(dialect, Column(dialect, "col1"), Column(dialect, "col2"))
    - To generate LEAST(?, ?, ...), pass literal values:
      least(dialect, "val1", "val2", "val3")

    Args:
        dialect: The SQL dialect instance
        *exprs: Variable number of expressions to compare. If strings are passed, they're treated as literal values.
                If BaseExpressions are passed, they're used as-is.

    Returns:
        A FunctionCall instance representing the LEAST function
    """
    target_exprs = [e if isinstance(e, BaseExpression) else Literal(dialect, e) for e in exprs]
    return FunctionCall(dialect, "LEAST", *target_exprs)
