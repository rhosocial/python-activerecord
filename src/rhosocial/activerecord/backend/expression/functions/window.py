# src/rhosocial/activerecord/backend/expression/functions/window.py
"""Window function factories."""

from typing import Union, Optional, Any, TYPE_CHECKING

from ..bases import BaseExpression
from ..column_types import value_class_of
from ..core import Column, FunctionCall, Literal, IntegerValueExpression

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


def _typed(call: FunctionCall, target: BaseExpression):
    """Wrap *call* in the value class matching *target*, when there is one.

    A window function that borrows a value hands that value back: ``LAG`` over a
    string answers with a string, over a float with a number. The column class
    already says which, so it is read off the class rather than off an attribute
    duplicating it -- see
    :func:`~...expression.column_types.value_class_of`.

    ``ROW_NUMBER``, ``RANK`` and ``DENSE_RANK`` are the exception -- they count
    or place rows rather than borrow a value, and are always whole numbers -- so
    they always wrap in :class:`IntegerValueExpression` and never come here.

    A target that says nothing -- a ``Literal``, an untyped ``Column`` -- leaves
    the call untyped, which is the honest answer: the database decides.
    """
    value_class = value_class_of(target)
    if value_class is not None:
        return value_class(call._dialect, call)
    return call


def row_number(dialect: "SQLDialectBase", alias: Optional[str] = None) -> "FunctionCall":
    """Creates a ROW_NUMBER window function call."""
    return IntegerValueExpression(
        dialect, FunctionCall(dialect, "ROW_NUMBER", alias=alias)
    )


def rank(dialect: "SQLDialectBase", alias: Optional[str] = None) -> "FunctionCall":
    """Creates a RANK window function call."""
    return IntegerValueExpression(dialect, FunctionCall(dialect, "RANK", alias=alias))


def dense_rank(dialect: "SQLDialectBase", alias: Optional[str] = None) -> "FunctionCall":
    """Creates a DENSE_RANK window function call."""
    return IntegerValueExpression(
        dialect, FunctionCall(dialect, "DENSE_RANK", alias=alias)
    )


def lag(
    dialect: "SQLDialectBase",
    expr: Union[str, "BaseExpression"],
    offset: int = 1,
    default: Optional[Any] = None,
    alias: Optional[str] = None,
) -> "FunctionCall":
    """
    Creates a LAG window function call.

    Usage rules:
    - To generate LAG(column, offset, default), pass a Column object: lag(dialect, Column(dialect, "column_name"), 1, 0)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to lag. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        offset: Number of rows to look back. Default is 1.
        default: Default value if lag goes beyond the partition. Optional.
        alias: Optional alias for the result.

    Returns:
        A FunctionCall instance representing the LAG function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    args = [target_expr, Literal(dialect, offset)]
    if default is not None:
        args.append(Literal(dialect, default))
    return _typed(FunctionCall(dialect, "LAG", *args, alias=alias), target_expr)


def lead(
    dialect: "SQLDialectBase",
    expr: Union[str, "BaseExpression"],
    offset: int = 1,
    default: Optional[Any] = None,
    alias: Optional[str] = None,
) -> "FunctionCall":
    """
    Creates a LEAD window function call.

    Usage rules:
    - To generate LEAD(column, offset, default), pass a Column object:
      lead(dialect, Column(dialect, "column_name"), 1, 0)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to lead. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        offset: Number of rows to look ahead. Default is 1.
        default: Default value if lead goes beyond the partition. Optional.
        alias: Optional alias for the result.

    Returns:
        A FunctionCall instance representing the LEAD function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    args = [target_expr, Literal(dialect, offset)]
    if default is not None:
        args.append(Literal(dialect, default))
    return _typed(FunctionCall(dialect, "LEAD", *args, alias=alias), target_expr)


def first_value(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], alias: Optional[str] = None
) -> "FunctionCall":
    """
    Creates a FIRST_VALUE window function call.

    Usage rules:
    - To generate FIRST_VALUE(column), pass a Column object: first_value(dialect, Column(dialect, "column_name"))

    Args:
        dialect: The SQL dialect instance
        expr: The expression to get first value of. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        alias: Optional alias for the result.

    Returns:
        A FunctionCall instance representing the FIRST_VALUE function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    return _typed(
        FunctionCall(dialect, "FIRST_VALUE", target_expr, alias=alias),
        target_expr,
    )


def last_value(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], alias: Optional[str] = None
) -> "FunctionCall":
    """
    Creates a LAST_VALUE window function call.

    Usage rules:
    - To generate LAST_VALUE(column), pass a Column object: last_value(dialect, Column(dialect, "column_name"))

    Args:
        dialect: The SQL dialect instance
        expr: The expression to get last value of. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        alias: Optional alias for the result.

    Returns:
        A FunctionCall instance representing the LAST_VALUE function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    return _typed(
        FunctionCall(dialect, "LAST_VALUE", target_expr, alias=alias),
        target_expr,
    )


def nth_value(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], n: int, alias: Optional[str] = None
) -> "FunctionCall":
    """
    Creates an NTH_VALUE window function call.

    Usage rules:
    - To generate NTH_VALUE(column, n), pass a Column object: nth_value(dialect, Column(dialect, "column_name"), 2)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to get nth value of. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        n: Position of the value to retrieve (1-indexed).
        alias: Optional alias for the result.

    Returns:
        A FunctionCall instance representing the NTH_VALUE function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    n_expr = Literal(dialect, n)
    return _typed(
        FunctionCall(dialect, "NTH_VALUE", target_expr, n_expr, alias=alias),
        target_expr,
    )
