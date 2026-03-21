# src/rhosocial/activerecord/backend/expression/aggregates.py
"""
Expressions related to SQL aggregation, including aggregate function calls
and the base class for expressions that support filtering.
"""

from typing import Optional, TYPE_CHECKING

from . import bases
from . import mixins

if TYPE_CHECKING:  # pragma: no cover
    from .bases import SQLPredicate
    from ..dialect import SQLDialectBase


class AggregateFunctionCall(
    mixins.AliasableMixin,
    mixins.ArithmeticMixin,
    mixins.ComparisonMixin,
    mixins.TypeCastingMixin,
    bases.SQLValueExpression,
):
    """
    Represents a call to a SQL aggregate function, such as COUNT, SUM, AVG.
    This class supports attaching a FILTER clause.
    """

    def __init__(
        self, dialect: "SQLDialectBase", func_name: str, *args, is_distinct: bool = False, alias: Optional[str] = None
    ):
        super().__init__(dialect)
        self.func_name = func_name
        self.args = list(args)
        self.is_distinct = is_distinct
        self.alias = alias
        self._filter_predicate: Optional["SQLPredicate"] = None

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

    def to_sql(self) -> "bases.SQLQueryAndParams":
        """
        Generates the SQL string and parameters for this aggregate function call,
        including any attached FILTER clause.
        """
        return self.dialect.format_function_call(self, self._filter_predicate)
