# src/rhosocial/activerecord/backend/expression/functions/function_call.py
from typing import Optional, TYPE_CHECKING, Union

from ..bases.bases import BaseExpression, SQLPredicate, SQLValue
from ..bases.coerce import value_expression
from ..bases.mixins import (
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    ResultTypeMixin,
    StringPatternPredicateMixin,
    TypeCastingMixin,
)

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase
    from ..functions.advanced_functions import WindowSpecification


class FunctionCall(
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    StringPatternPredicateMixin,
    TypeCastingMixin,
    ResultTypeMixin,
    SQLValue,
):
    """Represents a SQL function call, scalar or aggregate, such as LOWER, CONCAT, COUNT, SUM.

    One node covers both because the grammar is one grammar: ``NAME(args)``
    gains ``DISTINCT``, a ``FILTER (WHERE ...)`` clause, an ``OVER (...)``
    window clause and an alias, in that order. What distinguishes an aggregate
    is a fact about the call, not a shape of the SQL, and it is stated at
    construction time by the aggregate factories (``is_aggregate=True``)
    rather than inferred from the name. That fact is read only by RETURNING
    validation, which must refuse an aggregate because a RETURNING clause is
    evaluated per row; it is not a type and says nothing about what the call
    yields.

    The typed result is said by the wrapper the factories return, not by this
    node.

    Carries :class:`ResultTypeMixin` because this is the node that does *not*
    know what it yields. Most functions state their own result by returning the
    matching value class; the ones that cannot -- ``NULLIF`` and the
    ``COALESCE``-shaped family -- come back as this, and the caller says what
    they produce with ``.as_text()`` and friends.

    When niladic=True and no arguments are provided, the function call
    generates SQL without parentheses (e.g., CURRENT_TIMESTAMP instead of
    CURRENT_TIMESTAMP()). Per SQL:2003, certain value functions are niladic
    and must not use parentheses when invoked without arguments.

    When a niladic function has arguments (e.g., CURRENT_TIMESTAMP(6)),
    parentheses are included as normal.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_function_call"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        func_name: str,
        *args: "BaseExpression",
        is_distinct: bool = False,
        alias: Optional[str] = None,
        niladic: bool = False,
        filter_predicate: Optional["SQLPredicate"] = None,
        window_spec: Optional[Union["WindowSpecification", str]] = None,
        is_aggregate: bool = False,
    ):
        super().__init__(dialect)
        self.func_name = func_name
        self.args = [value_expression(dialect, arg) for arg in args]
        self.is_distinct = is_distinct
        self.alias = alias
        self.niladic = niladic
        self.filter_predicate = filter_predicate
        self.window_spec = window_spec
        self.is_aggregate = is_aggregate

    def filter(self, predicate: "SQLPredicate") -> "FunctionCall":
        """Apply a ``FILTER (WHERE ...)`` clause to this call.

        A second call AND-combines with the filter already attached, so
        ``call.filter(a).filter(b)`` states both conditions. Returns this
        node, which is what the fluent chain continues on; note that a typed
        wrapper around this node forwards the call and hands the node back,
        so the result is untyped -- filtering does not re-type anything.
        """
        if self.filter_predicate:
            self.filter_predicate = self.filter_predicate & predicate
        else:
            self.filter_predicate = predicate
        return self

    def over(self, window_spec: Union["WindowSpecification", str]) -> "FunctionCall":
        """Attach an ``OVER (...)`` clause to this call.

        The working replacement for assigning ``window_spec`` on the object:
        a typed wrapper stores an assignment on itself while rendering reads
        the node it holds, so the assignment is a silent no-op there. This
        method lives on the node, where the renderer looks. Returns this
        node, so the fluent chain continues on it.

        *window_spec* is an inline :class:`WindowSpecification` or the name
        of a window defined elsewhere in the query, which renders as an
        identifier.
        """
        self.window_spec = window_spec
        return self
