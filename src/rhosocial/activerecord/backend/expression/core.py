# src/rhosocial/activerecord/backend/expression/core.py
"""
Core SQL expression components like columns, literals, function calls, and subqueries.
"""
from typing import Any, Tuple, Optional, Dict, TYPE_CHECKING, Union

from . import bases
from . import mixins

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase


class Literal(mixins.ArithmeticMixin, mixins.ComparisonMixin, mixins.StringMixin, bases.SQLValueExpression):
    """Represents a literal value in a SQL query."""
    def __init__(self, dialect: "SQLDialectBase", value: Any):
        super().__init__(dialect)
        self.value = value

    def to_sql(self) -> Tuple[str, tuple]:
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

    def to_sql(self) -> Tuple[str, tuple]:
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

    def to_sql(self) -> Tuple[str, tuple]:
        formatted_args_sql = [arg.to_sql()[0] for arg in self.args]
        args_params = [arg.to_sql()[1] for arg in self.args]
        return self.dialect.format_function_call(
            self.func_name, formatted_args_sql, args_params, self.is_distinct, self.alias,
            filter_sql=None, filter_params=None
        )


class Subquery(mixins.AliasableMixin, mixins.ArithmeticMixin, mixins.ComparisonMixin, bases.SQLValueExpression):
    """Represents a subquery in a SQL expression."""
    def __init__(self, dialect: "SQLDialectBase",
                 query_input: Union[str, "bases.BaseExpression", "Subquery"],
                 query_params: Optional[Tuple[Any, ...]] = None,
                 alias: Optional[str] = None):
        super().__init__(dialect)
        self.alias = alias  # Store alias as an instance attribute
        # Handle different input types
        if isinstance(query_input, str):
            # If input is a string, use it directly with provided params
            self.query_sql = query_input
            self.query_params = query_params or ()
        elif isinstance(query_input, Subquery):
            # If input is already a Subquery, copy its attributes
            self.query_sql = query_input.query_sql
            self.query_params = query_input.query_params
            self.alias = query_input.alias or alias
        elif hasattr(query_input, 'to_sql'):
            # If input is a BaseExpression, call its to_sql method
            self.query_sql, self.query_params = query_input.to_sql()
        else:
            # Default: treat as string
            self.query_sql = str(query_input)
            self.query_params = query_params or ()

    def to_sql(self) -> Tuple[str, tuple]:
        subquery_sql = f"({self.query_sql})"
        if self.alias:
            return self.dialect.format_subquery(subquery_sql, self.query_params, self.alias)
        return subquery_sql, self.query_params


class TableExpression(bases.BaseExpression):
    """Represents a table or view in a SQL query, optionally with an alias."""
    def __init__(self, dialect: "SQLDialectBase", name: str, alias: Optional[str] = None,
                 temporal_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect)
        self.name = name
        self.alias = alias
        self.temporal_options = temporal_options or {}

    def to_sql(self) -> Tuple[str, tuple]:
        table_sql, params = self.dialect.format_table(self.name, self.alias)
        if self.temporal_options:
            result = self.dialect.format_temporal_options(self.temporal_options)
            if result is not None:
                temporal_sql, temporal_params = result
                table_sql = f"{table_sql} {temporal_sql}"
                params += temporal_params
        return table_sql, params


class WildcardExpression(bases.SQLValueExpression):
    """Represents a wildcard expression (SELECT *) in a SQL query."""
    def __init__(self, dialect: "SQLDialectBase", table: Optional[str] = None):
        super().__init__(dialect)
        self.table = table  # Optional table qualifier for SELECT table.*

    def to_sql(self) -> Tuple[str, tuple]:
        return self.dialect.format_wildcard(self.table)
