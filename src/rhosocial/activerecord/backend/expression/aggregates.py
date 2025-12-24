# src/rhosocial/activerecord/backend/expression/aggregates.py
"""
Expressions related to SQL aggregation, including aggregate function calls
and the base class for expressions that support filtering.
"""
from typing import Optional, Tuple, TYPE_CHECKING

from . import bases
from . import mixins
from . import operators  # Added this import

if TYPE_CHECKING:  # pragma: no cover
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
        # Handle arguments - special case for COUNT(*) to preserve the asterisk without parameters
        if self.func_name.upper() == "COUNT" and len(self.args) == 1 and \
           isinstance(self.args[0], operators.RawSQLExpression) and self.args[0].expression == "*":
            args_sql = ["*"]
            args_params = []
        else:
            args_sql = []
            args_params = []
            for arg in self.args:
                arg_sql, arg_params = arg.to_sql()
                args_sql.append(arg_sql)
                args_params.extend(arg_params)

        # Handle filter predicate if present
        filter_sql, filter_params = None, None
        if self._filter_predicate:
            filter_sql, filter_params = self._filter_predicate.to_sql()

        return self.dialect.format_function_call(
            self.func_name,
            args_sql,
            tuple(args_params),
            self.is_distinct,
            self.alias,
            filter_sql=filter_sql,
            filter_params=filter_params
        )
