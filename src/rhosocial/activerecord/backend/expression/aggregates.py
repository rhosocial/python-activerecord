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
    TypeCastingMixin,
)

if TYPE_CHECKING:  # pragma: no cover
    from .bases import SQLPredicate
    from ..dialect import SQLDialectBase


class AggregateFunctionCall(
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    TypeCastingMixin,
    SQLValueExpression,
):
    """
    Represents a call to a SQL aggregate function, such as COUNT, SUM, AVG.
    This class supports attaching a FILTER clause.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        func_name: str,
        *args,
        is_distinct: bool = False,
        alias: Optional[str] = None,
        filter_predicate: Optional["SQLPredicate"] = None,
    ):
        super().__init__(dialect)
        self.func_name = func_name
        self.args = list(args)
        self.is_distinct = is_distinct
        self.alias = alias
        self._filter_predicate: Optional["SQLPredicate"] = filter_predicate

    def filter(self, predicate: "SQLPredicate") -> "AggregateFunctionCall":
        """
        Applies a FILTER (WHERE ...) clause to the aggregate expression.
        If a filter already exists, it will be combined with the new one using AND.
        """
        if self._filter_predicate:
            self._filter_predicate = self._filter_predicate & predicate
        else:
            self._filter_predicate = predicate
        return self

    def to_sql(self) -> "SQLQueryAndParams":
        """
        Generates the SQL string and parameters for this aggregate function call,
        including any attached FILTER clause.
        """
        return self.dialect.format_function_call(self, self._filter_predicate)

    def get_params(self) -> dict:
        """
        Returns a dict of parameters for serialization, including filter predicate.

        Note: The filter parameter is set via fluent API (filter()) rather than
        __init__, so it must be explicitly included here for serialization.
        """
        params = super().get_params()
        if self._filter_predicate is not None:
            params["filter_predicate"] = self._filter_predicate
        return params
