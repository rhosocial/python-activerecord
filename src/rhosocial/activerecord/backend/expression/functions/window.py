# src/rhosocial/activerecord/backend/expression/functions/window.py
"""Window function factories."""

from abc import abstractmethod
from typing import Union, Optional, Any, TYPE_CHECKING

from ..advanced_functions import DeclaredValueType
from ..bases import BaseExpression
from ..column_types import annotation_for
from ..core import Column, FunctionCall, Literal

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


from ..value_types import NumericValue


def _typed(call: FunctionCall, target: BaseExpression):
    """Wrap *call* in the annotation matching *target*, when there is one.

    A window function that borrows a value hands that value back: ``LAG`` over a
    string answers with a string, over a float with a number. The column class
    already says which, so it is read off the class rather than off an attribute
    duplicating it -- see
    :func:`~...expression.column_types.annotation_for`.

    ``ROW_NUMBER``, ``RANK`` and ``DENSE_RANK`` are the exception -- they count
    or place rows rather than borrow a value, and are always whole numbers -- so
    they are their own node carrying :class:`NumericValue` and never come
    here.

    A target that says nothing -- a ``Literal``, an untyped ``Column`` -- leaves
    the call untyped, which is the honest answer: the database decides.
    """
    annotation = annotation_for(target)
    if annotation is not None:
        return annotation(call._dialect, call)
    return call

class _WindowRank(
    DeclaredValueType,
    NumericValue,
):
    # DeclaredValueType first: it is what keeps this node's own rendering ahead
    # of NumericValue's declaration that a surface cannot render.
    """Shared base for the ranking window functions.

    None of them takes an operand: the rank is over the window the node is placed
    in, so what is being ranked is said by the clause around it, not by an
    argument. An alias is still carried, because a ranked column in a select
    list usually gets a name.
    """

    #: The function name. Overridden per subclass; the base does not render.
    function_name: str = ""

    def __init__(self, dialect: "SQLDialectBase", alias: Optional[str] = None):
        BaseExpression.__init__(self, dialect)
        self.alias = alias

    @property
    @abstractmethod
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression.

        Abstract, so this base is not mistaken for a node: it declares no
        function name of its own, and a subclass that did not supply one would
        have nothing to write.
        """
        raise NotImplementedError


class RowNumberFunction(_WindowRank):
    """``ROW_NUMBER()`` -- the row's position, counting from 1 with no ties."""

    function_name = "ROW_NUMBER"

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_row_number_function"


class RankFunction(_WindowRank):
    """``RANK()`` -- the position, counting ties as one rank.

    ``1, 2, 2, 4`` rather than ``1, 2, 2, 3``: that skipping is what
    distinguishes it from :class:`DenseRankFunction`, and it is why they are two
    nodes rather than one with a flag.
    """

    function_name = "RANK"

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_rank_function"


class DenseRankFunction(_WindowRank):
    """``DENSE_RANK()`` -- the position with no gaps between ties."""

    function_name = "DENSE_RANK"

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_dense_rank_function"


def row_number(dialect: "SQLDialectBase", alias: Optional[str] = None) -> "RowNumberFunction":
    """Creates a ROW_NUMBER window function call."""
    return RowNumberFunction(dialect, alias)


def rank(dialect: "SQLDialectBase", alias: Optional[str] = None) -> "RankFunction":
    """Creates a RANK window function call."""
    return RankFunction(dialect, alias)


def dense_rank(dialect: "SQLDialectBase", alias: Optional[str] = None) -> "DenseRankFunction":
    """Creates a DENSE_RANK window function call."""
    return DenseRankFunction(dialect, alias)


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
    args = [target_expr, offset if isinstance(offset, BaseExpression) else Literal(dialect, offset)]
    if default is not None:
        args.append(default if isinstance(default, BaseExpression) else Literal(dialect, default))
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
    args = [target_expr, offset if isinstance(offset, BaseExpression) else Literal(dialect, offset)]
    if default is not None:
        args.append(default if isinstance(default, BaseExpression) else Literal(dialect, default))
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
    n_expr = n if isinstance(n, BaseExpression) else Literal(dialect, n)
    return _typed(
        FunctionCall(dialect, "NTH_VALUE", target_expr, n_expr, alias=alias),
        target_expr,
    )
