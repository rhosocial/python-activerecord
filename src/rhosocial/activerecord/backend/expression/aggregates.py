# src/rhosocial/activerecord/backend/expression_/aggregates.py
"""
Expressions related to SQL aggregation, including aggregate function calls
and the base class for expressions that support filtering.
"""
from typing import Optional, Tuple, TYPE_CHECKING, List

from . import bases
from . import mixins

if TYPE_CHECKING:
    from .bases import SQLPredicate
    from ..dialect import SQLDialectBase


class AggregatableExpression(mixins.ArithmeticMixin, mixins.ComparisonMixin, bases.SQLValueExpression):
    """
    An abstract base class for expressions that can be aggregated and
    can have a FILTER (WHERE ...) clause attached.
    Inherits comparison and arithmetic capabilities from mixins.
    """
    def __init__(self, dialect: "SQLDialectBase"):
        super().__init__(dialect)
        self._filter_predicate: Optional["SQLPredicate"] = None

    def filter(self, predicate: "SQLPredicate") -> 'AggregatableExpression':
        """
        Applies a FILTER (WHERE ...) clause to the aggregate expression.
        If a filter already exists, it will be combined with the new one using AND.
        """
        if self._filter_predicate:
            self._filter_predicate = self._filter_predicate & predicate
        else:
            self._filter_predicate = predicate
        return self


class AggregateFunctionCall(AggregatableExpression):
    """
    Represents a call to a SQL aggregate function, such as COUNT, SUM, AVG.
    This class supports attaching a FILTER clause.
    """
    def __init__(self, dialect: "SQLDialectBase", func_name: str, *args, is_distinct: bool = False, alias: Optional[str] = None):
        super().__init__(dialect)
        self.func_name = func_name
        self.args = list(args)
        self.is_distinct = is_distinct
        self.alias = alias

    def to_sql(self) -> Tuple[str, tuple]:
        """
        Generates the SQL string and parameters for this aggregate function call,
        including any attached FILTER clause.
        """
        args_sql = []
        args_params = []
        for arg in self.args:
            arg_sql_part, arg_params_tuple = arg.to_sql()
            args_sql.append(arg_sql_part)
            args_params.append(arg_params_tuple)

        filter_sql, filter_params = None, None
        if self._filter_predicate:
            filter_sql, filter_params = self._filter_predicate.to_sql()

        return self.dialect.format_function_call(
            self.func_name,
            args_sql,
            args_params,
            self.is_distinct,
            self.alias,
            filter_sql=filter_sql,
            filter_params=filter_params
        )
