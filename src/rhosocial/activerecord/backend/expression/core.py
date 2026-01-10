# src/rhosocial/activerecord/backend/expression/core.py
"""
Core SQL expression components like columns, literals, function calls, and subqueries.
"""
from typing import Any, Tuple, Optional, Dict, TYPE_CHECKING, Union

from . import bases
from . import mixins

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase
    from .bases import SQLQueryAndParams




class Literal(mixins.ArithmeticMixin, mixins.ComparisonMixin, mixins.StringMixin, bases.SQLValueExpression):
    """Represents a literal value in a SQL query."""
    def __init__(self, dialect: "SQLDialectBase", value: Any):
        super().__init__(dialect)
        self.value = value

    def to_sql(self) -> 'bases.SQLQueryAndParams':
        # Always return a single placeholder and the value itself.
        # It's up to higher-level expressions (like InPredicate or ValuesExpression)
        # to decide if this value needs to be expanded or formatted differently.
        return self.dialect.get_parameter_placeholder(), (self.value,)

    def __repr__(self) -> str:
        return f"Literal({self.value!r})"


class Column(mixins.AliasableMixin, mixins.ArithmeticMixin, mixins.ComparisonMixin, mixins.StringMixin, bases.SQLValueExpression):
    """Represents a column in a SQL query."""
    def __init__(self, dialect: "SQLDialectBase", name: str, table: Optional[str] = None, alias: Optional[str] = None):
        super().__init__(dialect)
        self.name = name
        self.table = table
        self.alias = alias

    def to_sql(self) -> 'bases.SQLQueryAndParams':
        return self.dialect.format_column(self.name, self.table, self.alias)


class FunctionCall(mixins.AliasableMixin, mixins.ArithmeticMixin, mixins.ComparisonMixin, mixins.StringMixin, bases.SQLValueExpression):
    """Represents a scalar SQL function call, such as LOWER, CONCAT, etc."""
    def __init__(self, dialect: "SQLDialectBase", func_name: str, *args: "bases.BaseExpression",
                 is_distinct: bool = False, alias: Optional[str] = None):
        super().__init__(dialect)
        self.func_name = func_name
        self.args = list(args)
        self.is_distinct = is_distinct
        self.alias = alias

    def to_sql(self) -> 'bases.SQLQueryAndParams':
        formatted_args_sql = [arg.to_sql()[0] for arg in self.args]
        args_params = [arg.to_sql()[1] for arg in self.args]
        return self.dialect.format_function_call(
            self.func_name, formatted_args_sql, args_params, self.is_distinct, self.alias,
            filter_sql=None, filter_params=None
        )


class Subquery(mixins.AliasableMixin, mixins.ArithmeticMixin, mixins.ComparisonMixin, bases.SQLValueExpression):
    """Represents a subquery in a SQL expression."""
    def __init__(self, dialect: "SQLDialectBase",
                 query_input: Union[str, "bases.SQLQueryAndParams", "bases.BaseExpression", "Subquery"],
                 query_params: Optional[Tuple[Any, ...]] = None,
                 alias: Optional[str] = None):
        super().__init__(dialect)
        self.alias = alias  # Store alias as an instance attribute

        # Handle backward compatibility: if query_input is not a tuple but query_params is provided,
        # treat query_input as a string and query_params as the parameters
        if query_params is not None and not isinstance(query_input, tuple):
            # Old-style call: Subquery(dialect, query_string, query_params, alias)
            self.query_sql = query_input
            self.query_params = query_params or ()
        else:
            # New-style call or other cases
            query = query_input
            if isinstance(query, str):
                # If input is a string, use it directly with empty params
                self.query_sql = query
                self.query_params = ()
            elif bases.is_sql_query_and_params(query):
                # If input is a SQLQueryAndParams (str, tuple), extract SQL and params
                sql_str, params = query
                # If params is None, use an empty tuple
                self.query_params = params if params is not None else ()
                self.query_sql = sql_str
            elif isinstance(query, Subquery):
                # If input is already a Subquery, copy its attributes
                self.query_sql = query.query_sql
                self.query_params = query.query_params
                self.alias = query.alias or alias
            elif isinstance(query, bases.BaseExpression):
                # If input is a BaseExpression, call its to_sql method
                self.query_sql, self.query_params = query.to_sql()
            else:
                # Default: treat as string
                self.query_sql = str(query)
                self.query_params = ()

    def to_sql(self) -> 'bases.SQLQueryAndParams':
        subquery_sql = f"({self.query_sql})"
        if self.alias:
            return self.dialect.format_subquery(subquery_sql, self.query_params, self.alias)
        return subquery_sql, self.query_params


class TableExpression(mixins.AliasableMixin, bases.BaseExpression):
    """Represents a table or view in a SQL query, optionally with an alias."""
    def __init__(self, dialect: "SQLDialectBase", name: str, alias: Optional[str] = None,
                 temporal_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect)
        self.name = name
        self.alias = alias
        self.temporal_options = temporal_options or {}

    def to_sql(self) -> 'bases.SQLQueryAndParams':
        table_sql, params = self.dialect.format_table(self.name, self.alias)
        if self.temporal_options:
            result = self.dialect.format_temporal_options(self.temporal_options)
            if result is not None:
                temporal_sql, temporal_params = result
                table_sql = f"{table_sql} {temporal_sql}"
                params += temporal_params
        return table_sql, params


class WildcardExpression(bases.SQLValueExpression):
    """Represents a wildcard expression (SELECT *) in a SQL query.

    Important: When constructing queries that include wildcards (SELECT *),
    use WildcardExpression instead of Literal("*") to avoid treating the
    wildcard as a parameter value. Using Literal("*") will incorrectly
    include the '*' character in the parameter tuple rather than as part
    of the SQL query itself.

    Examples:
        # Correct usage:
        select=[WildcardExpression(dialect)]
        # Results in: SELECT * FROM ...

        # Incorrect usage:
        select=[Literal(dialect, "*")]
        # Results in: SELECT ? FROM ... with params ('*',)
    """
    def __init__(self, dialect: "SQLDialectBase", table: Optional[str] = None):
        super().__init__(dialect)
        self.table = table  # Optional table qualifier for SELECT table.*

    def to_sql(self) -> 'bases.SQLQueryAndParams':
        return self.dialect.format_wildcard(self.table)
