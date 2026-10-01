# src/rhosocial/activerecord/backend/expression/aggregates.py
"""
Expressions related to SQL aggregation, including aggregate function calls
and the base class for expressions that support filtering.
"""

from typing import Optional, TYPE_CHECKING

from .bases import SQLQueryAndParams, SQLValueExpression
from .mixins import (
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    StringPatternPredicateMixin,
    TypeCastingMixin,
)

if TYPE_CHECKING:  # pragma: no cover
    from .bases import SQLPredicate
    from ..dialect import SQLDialectBase


class AggregateFunctionCall(
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    StringPatternPredicateMixin,
    TypeCastingMixin,
    SQLValueExpression,
):
    """
    Represents a call to a SQL aggregate function, such as COUNT, SUM, AVG.
    This class supports attaching a FILTER clause.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_function_call"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        func_name: str,
        *args,
        is_distinct: bool = False,
        alias: Optional[str] = None,
        filter_predicate: Optional["SQLPredicate"] = None,
        family: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.func_name = func_name
        self.args = list(args)
        self.is_distinct = is_distinct
        self.alias = alias
        self.filter_predicate: Optional["SQLPredicate"] = filter_predicate
        # get_params() resolves a constructor parameter to `_name` or `name`,
        # so the value has to live under the private spelling even when it is
        # None. The parameter is in the signature either way.
        self._family = family
        if family is not None:
            # One class serves every aggregate, and they do not agree on what
            # they answer with: COUNT is a count, MIN keeps the input's family,
            # AVG widens a whole number to a fraction. Declaring it per
            # instance is what lets the class stay shared.
            self.VALUE_FAMILY = family

    def filter(self, predicate: "SQLPredicate") -> "AggregateFunctionCall":
        """
        Applies a FILTER (WHERE ...) clause to the aggregate expression.
        If a filter already exists, it will be combined with the new one using AND.
        """
        if self.filter_predicate:
            self.filter_predicate = self.filter_predicate & predicate
        else:
            self.filter_predicate = predicate
        return self
