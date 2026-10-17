# src/rhosocial/activerecord/backend/expression/functions/aggregate.py
"""Aggregate function nodes and factories.

Every standard aggregate is its own node class with its own kind, so the
identity of the function travels on the node instead of inside a generic name
string. ``FunctionCall`` is left to user-defined functions (see catalog §3.4).

``AggregateFunction`` is a **shared implementation base**, not an expression
contract: it owns no kind, declares no formatter, cannot be instantiated, never
enters an artifact and never participates in kind dispatch (catalog §3.4,
spec 4.2). It carries what the family does the same way — the ``operand`` plus
``distinct`` shape and the check that the row-count wildcard is only ever the
operand of ``COUNT(*)``.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, Union

from ..bases import BaseExpression, SQLValue
from ..core import (
    AllColumnsWildcard,
    Column,
    RowCountWildcard,
)
from ..mixins import (
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    NumericValueMixin,
    TranscendentalMixin,
    TypeCastingMixin,
)

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase
    from ..bases import SQLPredicate
    from ..core import FunctionCall


class AggregateFunction(AliasableMixin, SQLValue, ABC):
    """The shared implementation base of the aggregate family.

    ``CountFunction`` / ``SumFunction`` / ``AvgFunction`` / ``MinFunction`` /
    ``MaxFunction`` each embed this. It is a code-reuse base, not an expression
    node: it has no kind of its own, no formatter of its own, cannot be
    instantiated, never enters an artifact and never takes part in kind
    dispatch. Each concrete aggregate owns its kind and its formatter.

    The construction parameters are exactly the wire contract of every
    aggregate (``operand`` and ``distinct``). The one cross-cutting rule they
    share is enforced here: the row-count wildcard is legal only as the operand
    of ``COUNT(*)`` — never for another aggregate, and never with ``DISTINCT``.
    """

    #: Whether a row-count wildcard is a legal operand. ``True`` only on
    #: :class:`CountFunction`: ``COUNT(*)`` counts rows, and no other
    #: aggregate has a row to count.
    admits_row_count_wildcard: bool = False

    def __init__(
        self,
        dialect: "SQLDialectBase",
        operand: "BaseExpression",
        distinct: bool = False,
    ):
        if not isinstance(distinct, bool):
            raise TypeError(
                f"distinct must be a bool, got {type(distinct).__name__}"
            )
        if isinstance(operand, RowCountWildcard):
            if not self.admits_row_count_wildcard:
                raise ValueError(
                    f"{type(self).__name__} does not accept a row-count "
                    f"wildcard: the bare * counts rows, and COUNT is the only "
                    f"aggregate whose contract admits it."
                )
            if distinct:
                raise ValueError(
                    "COUNT(DISTINCT *) is not valid SQL: the row-count "
                    "wildcard counts rows, which have no duplicates."
                )
        elif isinstance(operand, AllColumnsWildcard):
            raise ValueError(
                f"{type(self).__name__} takes a value expression, not the "
                f"all-columns wildcard: '*' expands columns and belongs to a "
                f"select list or RETURNING clause."
            )
        # BaseExpression directly, not super(): these nodes render themselves and
        # hold no call, and an aggregate that also declares its value type --
        # ARRAY_AGG is an array, JSON_OBJECTAGG a document -- inherits the value
        # class for that type, whose __init__ is the *wrapper's* and wants a call
        # this node does not have. Going through super() would reach it.
        BaseExpression.__init__(self, dialect)
        self.operand = operand
        self.distinct = distinct

    @abstractmethod
    def format_method(self) -> str:
        """Name of the dialect formatting method that renders this aggregate."""
        raise NotImplementedError

    def filter(self, predicate: "SQLPredicate") -> "FunctionCall":
        """Apply a ``FILTER (WHERE ...)`` clause, degrading to the generic node.

        ``FILTER`` is a modifier the aggregate nodes do not model yet: the wire
        contract of ``count_function`` / ``sum_function`` ... is exactly
        ``operand`` + ``distinct``, and the standalone ``FilterClause`` node is
        a later wave (catalog §3.2). Rather than drop the capability or smuggle
        an unmodelled parameter onto the node, this hands back the generic
        :class:`FunctionCall` — the escape hatch — carrying the same function,
        operand and filter.

        The result is deliberately untyped: it is no longer the classed
        aggregate node, so it no longer offers that node's value surface. This
        is the same shape the typed wrappers used to forward to, so
        ``count(x).filter(p)`` keeps producing the call that renders
        ``COUNT(x) FILTER (WHERE p)``.
        """
        from ..core import FunctionCall
        from ..registry import kind_of

        name = kind_of(type(self)).replace("_function", "").upper()
        return FunctionCall(
            self._dialect,
            name,
            self.operand,
            is_distinct=self.distinct,
            alias=self.alias,
            filter_predicate=predicate,
            is_aggregate=True,
        )


class CountFunction(
    ArithmeticMixin,
    ComparisonMixin,
    NumericValueMixin,
    TranscendentalMixin,
    TypeCastingMixin,
    AggregateFunction,
):
    """``COUNT(operand)`` / ``COUNT(DISTINCT operand)`` / ``COUNT(*)``.

    A count is a whole number however wide the thing counted, so the node
    carries the integer-value surface and not the string one.
    ``COUNT(*)`` is the only place the row-count wildcard may stand.
    """

    admits_row_count_wildcard = True

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_count_function"


class SumFunction(
    ArithmeticMixin,
    ComparisonMixin,
    NumericValueMixin,
    TranscendentalMixin,
    TypeCastingMixin,
    AggregateFunction,
):
    """``SUM(operand)`` / ``SUM(DISTINCT operand)`` — a numeric reduction."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_sum_function"


class AvgFunction(
    ArithmeticMixin,
    ComparisonMixin,
    NumericValueMixin,
    TranscendentalMixin,
    TypeCastingMixin,
    AggregateFunction,
):
    """``AVG(operand)`` / ``AVG(DISTINCT operand)``.

    Averaging whole numbers gives a fraction, so the node carries the numeric
    surface rather than the integer one.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_avg_function"


class MinFunction(ComparisonMixin, TypeCastingMixin, AggregateFunction):
    """``MIN(operand)`` / ``MIN(DISTINCT operand)``.

    The minimum hands back something of the operand's kind, and that kind is
    not known to the node, so it offers only the operations every value has:
    comparison and casting. A caller who knows the kind narrows the result
    with ``cast()`` or the ``as_*`` result-type helpers.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_min_function"


class MaxFunction(ComparisonMixin, TypeCastingMixin, AggregateFunction):
    """``MAX(operand)`` / ``MAX(DISTINCT operand)`` — the mirror of MIN."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_max_function"


def _named(node: BaseExpression, alias: Optional[str]) -> BaseExpression:
    """Apply *alias* through the aliasing contract, or return *node* untouched."""
    return node.as_(alias) if alias else node


def count(
    dialect: "SQLDialectBase",
    expr: Union[str, "BaseExpression"] = "*",
    is_distinct: bool = False,
    alias: Optional[str] = None,
) -> "CountFunction":
    """
    Creates a COUNT aggregate node.

    Usage rules:
    - To generate COUNT(*), pass "*" as a string: count(dialect, "*")
    - To generate COUNT(*), pass a RowCountWildcard: count(dialect, RowCountWildcard(dialect))
    - To generate COUNT(column), pass a Column object: count(dialect, Column(dialect, "column_name"))
    - To generate COUNT(?), pass a literal value: count(dialect, "literal_value")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to count. Defaults to "*" to generate COUNT(*).
              If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        is_distinct: Whether to use DISTINCT keyword
        alias: Optional alias for the result

    Returns:
        A :class:`CountFunction` node.
    """
    if expr == "*" and isinstance(expr, str):
        target_expr = RowCountWildcard(dialect)
    elif isinstance(expr, RowCountWildcard):
        target_expr = expr
    elif isinstance(expr, AllColumnsWildcard):
        raise ValueError(
            "COUNT takes column expressions or a row-count wildcard; the "
            "all-columns wildcard expands columns and belongs to a select "
            "list or RETURNING clause, not an aggregate parameter."
        )
    else:
        target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    return _named(CountFunction(dialect, target_expr, distinct=is_distinct), alias)


def sum_(
    dialect: "SQLDialectBase",
    expr: Union[str, "BaseExpression"],
    is_distinct: bool = False,
    alias: Optional[str] = None,
) -> "SumFunction":
    """
    Creates a SUM aggregate node.

    Usage rules:
    - To generate SUM(column), pass a Column object: sum_(dialect, Column(dialect, "column_name"))
    - To generate SUM(?), pass a literal value: sum_(dialect, "literal_value")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to sum. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        is_distinct: Whether to use DISTINCT keyword
        alias: Optional alias for the result

    Returns:
        A :class:`SumFunction` node.
    """
    if isinstance(expr, RowCountWildcard) or (isinstance(expr, str) and expr == "*"):
        raise ValueError(
            "SUM does not accept a row-count wildcard: the bare * counts "
            "rows, and COUNT is the only aggregate whose contract admits it."
        )
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    return _named(SumFunction(dialect, target_expr, distinct=is_distinct), alias)


def avg(
    dialect: "SQLDialectBase",
    expr: Union[str, "BaseExpression"],
    is_distinct: bool = False,
    alias: Optional[str] = None,
) -> "AvgFunction":
    """
    Creates an AVG aggregate node.

    Usage rules:
    - To generate AVG(column), pass a Column object: avg(dialect, Column(dialect, "column_name"))
    - To generate AVG(?), pass a literal value: avg(dialect, "literal_value")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to average. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        is_distinct: Whether to use DISTINCT keyword
        alias: Optional alias for the result

    Returns:
        An :class:`AvgFunction` node.
    """
    if isinstance(expr, RowCountWildcard) or (isinstance(expr, str) and expr == "*"):
        raise ValueError(
            "AVG does not accept a row-count wildcard: the bare * counts "
            "rows, and COUNT is the only aggregate whose contract admits it."
        )
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    return _named(AvgFunction(dialect, target_expr, distinct=is_distinct), alias)


def min_(
    dialect: "SQLDialectBase",
    expr: Union[str, "BaseExpression"],
    is_distinct: bool = False,
    alias: Optional[str] = None,
) -> "MinFunction":
    """
    Creates a MIN aggregate node.

    Usage rules:
    - To generate MIN(column), pass a Column object: min_(dialect, Column(dialect, "column_name"))
    - To generate MIN(?), pass a literal value: min_(dialect, "literal_value")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to find minimum of. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        is_distinct: Whether to use DISTINCT keyword
        alias: Optional alias for the result

    Returns:
        A :class:`MinFunction` node.
    """
    if isinstance(expr, RowCountWildcard) or (isinstance(expr, str) and expr == "*"):
        raise ValueError(
            "MIN does not accept a row-count wildcard: the bare * counts "
            "rows, and COUNT is the only aggregate whose contract admits it."
        )
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    return _named(MinFunction(dialect, target_expr, distinct=is_distinct), alias)


def max_(
    dialect: "SQLDialectBase",
    expr: Union[str, "BaseExpression"],
    is_distinct: bool = False,
    alias: Optional[str] = None,
) -> "MaxFunction":
    """
    Creates a MAX aggregate node.

    Usage rules:
    - To generate MAX(column), pass a Column object: max_(dialect, Column(dialect, "column_name"))
    - To generate MAX(?), pass a literal value: max_(dialect, "literal_value")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to find maximum of. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        is_distinct: Whether to use DISTINCT keyword
        alias: Optional alias for the result

    Returns:
        A :class:`MaxFunction` node.
    """
    if isinstance(expr, RowCountWildcard) or (isinstance(expr, str) and expr == "*"):
        raise ValueError(
            "MAX does not accept a row-count wildcard: the bare * counts "
            "rows, and COUNT is the only aggregate whose contract admits it."
        )
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    return _named(MaxFunction(dialect, target_expr, distinct=is_distinct), alias)


__all__ = [
    "AggregateFunction",
    "CountFunction",
    "SumFunction",
    "AvgFunction",
    "MinFunction",
    "MaxFunction",
    "count",
    "sum_",
    "avg",
    "min_",
    "max_",
]
