# src/rhosocial/activerecord/backend/expression/functions/conditional.py
"""Conditional function factories."""

from typing import Any, Union, Optional, TYPE_CHECKING, overload

from ..bases import BaseExpression, SQLValueExpression
from ..column_types import IntegerColumn, NumericColumn
from ..core import FunctionCall, IntegerValueExpression, Literal, NumericValueExpression
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


#: Column class -> the result class an operation over it hands back.
_RESULT_OF = {
    "IntegerColumn": "IntegerValueExpression",
    "NumericColumn": "NumericValueExpression",
    "StringColumn": "StringValueExpression",
    "DateTimeColumn": "DateTimeValueExpression",
    "JSONColumn": "JSONValueExpression",
    "ArrayColumn": "ArrayValueExpression",
    "BooleanColumn": "BooleanValueExpression",
}


def _result_class(expr: object) -> Optional[type]:
    """The result class an expression of this kind carries, or None if unknown.

    Read off the class rather than off a family attribute, so the answer comes
    from the type the caller wrote rather than from state set at construction.
    """
    from .. import core

    name = _RESULT_OF.get(type(expr).__name__)
    return getattr(core, name) if name else None


def _widest(dialect: "SQLDialectBase", call: "FunctionCall", exprs: list) -> "SQLValueExpression":
    """Give GREATEST/LEAST the type of its arguments when they agree on one.

    Every argument is a candidate for the result, so when they all answer with
    the same kind the answer is that kind. When they disagree the operation is
    legal SQL with no single answer -- GREATEST of an integer and a string is
    neither -- and the call stays generic rather than guessing the first
    argument or the widest, either of which would promise a surface the
    database does not.
    """
    classes = {_result_class(e) for e in exprs}
    if len(classes) == 1 and None not in classes:
        return classes.pop()(dialect, call)
    return call


#: NULLIF gives back its first argument, or NULL when the two match, so the
#: result takes the type of the value rather than of the comparison. Overloads
#: say which one a caller passed; the third covers everything else.
@overload
def nullif(
    dialect: "SQLDialectBase", value: IntegerColumn, null_value: Any
) -> "IntegerValueExpression": ...


@overload
def nullif(
    dialect: "SQLDialectBase", value: NumericColumn, null_value: Any
) -> "NumericValueExpression": ...


@overload
def nullif(
    dialect: "SQLDialectBase", value: Any, null_value: Any
) -> "SQLValueExpression": ...


def nullif(
    dialect: "SQLDialectBase", value: Any, null_value: Any
) -> "SQLValueExpression":
    """
    Creates a NULLIF scalar function call.

    Usage rules:
    - To generate NULLIF(column, null_val), pass Column objects:
      nullif(dialect, Column(dialect, "col1"), Column(dialect, "col2"))
    - To generate NULLIF(?, ?), pass literal values:
      nullif(dialect, "value", "null_value")

    Args:
        dialect: The SQL dialect instance
        value: The value to compare. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.
        null_value: The value to compare against. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        The type of *value*, since NULLIF returns it unless it matches. A literal
        says nothing about its own type, so that case stays generic.
    """
    value_expr = value if isinstance(value, BaseExpression) else Literal(dialect, value)
    null_expr = null_value if isinstance(null_value, BaseExpression) else Literal(dialect, null_value)
    call = FunctionCall(dialect, "NULLIF", value_expr, null_expr)
    result = _result_class(value_expr)
    if result is not None:
        return result(dialect, call)
    return call


def greatest(
    dialect: "SQLDialectBase", *exprs: Union[str, "BaseExpression"]
) -> "SQLValueExpression":
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
        The type its arguments agree on, or a generic FunctionCall if they do not
    """
    target_exprs = [e if isinstance(e, BaseExpression) else Literal(dialect, e) for e in exprs]
    return _widest(dialect, FunctionCall(dialect, "GREATEST", *target_exprs), target_exprs)


def least(
    dialect: "SQLDialectBase", *exprs: Union[str, "BaseExpression"]
) -> "SQLValueExpression":
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
        The type its arguments agree on, or a generic FunctionCall if they do not
    """
    target_exprs = [e if isinstance(e, BaseExpression) else Literal(dialect, e) for e in exprs]
    return _widest(dialect, FunctionCall(dialect, "LEAST", *target_exprs), target_exprs)
