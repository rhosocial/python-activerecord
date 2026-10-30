# src/rhosocial/activerecord/backend/expression/functions/array.py
"""Array function factories."""

from typing import Union, Optional, TYPE_CHECKING

from ..advanced_functions import DeclaredValueType
from ..bases import BaseExpression
from ..core import (
    Column,
    Literal,
)
from .aggregate import AggregateFunction

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase

from ..value_types import (
    ArrayValue,
    NumericValue,
)

class UnnestFunction(
    DeclaredValueType,
    ArrayValue,
):
    """``UNNEST(array)`` -- the array's elements, one per row.

    Not an aggregate: it does not combine rows, it *multiplies* them, which is
    why a FROM source is where it belongs and why counting its output is a
    different question from ``ARRAY_LENGTH``.
    """


    def __init__(self, dialect: "SQLDialectBase", target):
        from ..core import Literal

        # BaseExpression directly, not super(): the value class is a *wrapper*
        # whose __init__ takes the call it delegates to, and this node has no
        # call -- it renders itself. DeclaredValueType keeps that from mattering.
        BaseExpression.__init__(self, dialect)
        # See ArrayLengthFunction: an array is not text and not a number, so a
        # bare host value becomes the untyped literal for now.
        self.target = target if isinstance(target, BaseExpression) else Literal(dialect, target)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_unnest_function"


class ArrayLengthFunction(
    DeclaredValueType,
    NumericValue,
):
    """``ARRAY_LENGTH(array[, dimension])`` -- how many elements.

    :attr:`dimension` is optional and its absence is not the same as dimension 1
    on a backend that counts the array's extents rather than its elements, so it
    is ``None`` when not asked for and the formatter drops it.
    """


    def __init__(self, dialect: "SQLDialectBase", target, dimension=None):
        from .. import values
        from ..core import Literal

        # BaseExpression directly, not super(): the value class is a *wrapper*
        # whose __init__ takes the call it delegates to, and this node has no
        # call -- it renders itself. DeclaredValueType keeps that from mattering.
        BaseExpression.__init__(self, dialect)
        # An array is not text and not a number, so there is no typed value node
        # for it; a bare host value becomes the untyped literal until the array
        # value type lands.
        self.target = target if isinstance(target, BaseExpression) else Literal(dialect, target)
        # Normalised here so the count is a node however it arrived; a bare int
        # reaching the formatter is what made it fail at render instead of here.
        self.dimension = (
            None
            if dimension is None
            else dimension if isinstance(dimension, BaseExpression) else Literal(dialect, dimension)
        )

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_array_length_function"

class ArrayAggregateFunction(
    AggregateFunction,
    DeclaredValueType,
    ArrayValue,
):
    """``ARRAY_AGG(operand)`` -- the rows gathered into one array.

    An aggregate, so it carries ``DISTINCT`` and the window and filter clauses an
    aggregate takes; :class:`~...expression.advanced_functions.AggregateFunction`
    holds those.

    The result is an array whatever the gathered values were, which is why the
    node says so instead of reading a type off the operand.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_array_agg_function"


def array_agg(
    dialect: "SQLDialectBase",
    expr: Union[str, "BaseExpression"],
    is_distinct: bool = False,
    alias: Optional[str] = None,
) -> "ArrayAggregateFunction":
    """Creates an ARRAY_AGG aggregate function call.

    The result is always an array -- gathering values produces a list of them,
    whatever the gathered type was -- so this node says so rather than reading a
    type off the argument.
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    node = ArrayAggregateFunction(dialect, target_expr, distinct=is_distinct)
    # The alias goes through the aliasing contract rather than the constructor:
    # AggregateFunction takes the operand and DISTINCT, and the name is applied
    # afterwards, which is what every other aggregate factory does.
    return node.as_(alias) if alias else node


def unnest(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "UnnestFunction":
    """Creates an UNNEST function call."""
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    return UnnestFunction(dialect, target_expr)


def array_length(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], dimension: int = 1
) -> "ArrayLengthFunction":
    """Creates an ARRAY_LENGTH function call."""
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    dimension_expr = dimension if isinstance(dimension, BaseExpression) else Literal(dialect, dimension)
    return ArrayLengthFunction(dialect, target_expr, dimension_expr)
