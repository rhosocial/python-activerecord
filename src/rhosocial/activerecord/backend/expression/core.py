# src/rhosocial/activerecord/backend/expression/core.py
"""
Core SQL expression components like columns, literals, function calls, and subqueries.
"""

from typing import Any, Tuple, Optional, Dict, TYPE_CHECKING, Union

from .bases import BaseExpression, SQLQueryAndParams, SQLValueExpression, is_sql_query_and_params
from .mixins import (
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    StringMixin,
    TypeCastingMixin,
)

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase


class Literal(
    ArithmeticMixin,
    ComparisonMixin,
    StringMixin,
    TypeCastingMixin,
    SQLValueExpression,
):
    """Represents a literal value in a SQL query."""

    def __init__(self, dialect: "SQLDialectBase", value: Any):
        super().__init__(dialect)
        self.value = value

    def to_sql(self) -> "SQLQueryAndParams":
        sql = self.dialect.get_parameter_placeholder()
        params = (self.value,)

        # Apply type casts if any
        for target_type in self._cast_types:
            sql, params = self.dialect.format_cast_expression(sql, target_type, params, None)

        return sql, params

    def __repr__(self) -> str:
        return f"Literal({self.value!r})"


class Column(
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    StringMixin,
    TypeCastingMixin,
    SQLValueExpression,
):
    """Represents a column in a SQL query."""

    def __init__(self, dialect: "SQLDialectBase", name: str, table: Optional[str] = None, alias: Optional[str] = None):
        super().__init__(dialect)
        self.name = name
        self.table = table
        self.alias = alias

    def to_sql(self) -> "SQLQueryAndParams":
        # Generate base column SQL
        if self.table:
            sql = f"{self.dialect.format_identifier(self.table)}.{self.dialect.format_identifier(self.name)}"
        else:
            sql = self.dialect.format_identifier(self.name)
        params = ()

        # Apply type casts if any
        for target_type in self._cast_types:
            sql, params = self.dialect.format_cast_expression(sql, target_type, params, None)

        # Apply alias if any (after type casts)
        if self.alias:
            sql = f"{sql} AS {self.dialect.format_identifier(self.alias)}"

        return sql, params


class FunctionCall(
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    StringMixin,
    TypeCastingMixin,
    SQLValueExpression,
):
    """Represents a scalar SQL function call, such as LOWER, CONCAT, etc.

    When niladic=True and no arguments are provided, the function call
    generates SQL without parentheses (e.g., CURRENT_TIMESTAMP instead of
    CURRENT_TIMESTAMP()). Per SQL:2003, certain value functions are niladic
    and must not use parentheses when invoked without arguments.

    When a niladic function has arguments (e.g., CURRENT_TIMESTAMP(6)),
    parentheses are included as normal.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        func_name: str,
        *args: "BaseExpression",
        is_distinct: bool = False,
        alias: Optional[str] = None,
        niladic: bool = False,
    ):
        super().__init__(dialect)
        self.func_name = func_name
        self.args = list(args)
        self.is_distinct = is_distinct
        self.alias = alias
        self.niladic = niladic

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_function_call(self)


class Subquery(AliasableMixin, ArithmeticMixin, ComparisonMixin, SQLValueExpression):
    """Represents a subquery in a SQL expression."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        query_input: Union[str, "SQLQueryAndParams", "BaseExpression", "Subquery"],
        query_params: Optional[Tuple[Any, ...]] = None,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.alias = alias

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
            elif is_sql_query_and_params(query):
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
            elif isinstance(query, BaseExpression):
                # If input is a BaseExpression, call its to_sql method
                self.query_sql, self.query_params = query.to_sql()
            else:
                # Default: treat as string
                self.query_sql = str(query)
                self.query_params = ()

    def to_sql(self) -> "SQLQueryAndParams":
        sql = f"({self.query_sql})"
        params = self.query_params

        # Apply type casts if any
        for target_type in self._cast_types:
            sql, params = self.dialect.format_cast_expression(sql, target_type, params, None)

        # Apply alias if any (after type casts)
        if self.alias:
            sql = f"{sql} AS {self.dialect.format_identifier(self.alias)}"

        return sql, params


class TableExpression(AliasableMixin, BaseExpression):
    """Represents a table or view in a SQL query, optionally with schema and alias.

    Supports SQL standard schema-qualified table names (schema_name.table_name).
    All major databases support this syntax.

    Args:
        dialect: The SQL dialect to use for formatting
        name: The table or view name
        schema_name: Optional schema/database name qualifier (SQL standard)
        alias: Optional table alias
        temporal_options: Optional temporal table options (e.g., FOR SYSTEM_TIME)

    Examples:
        # Simple table reference
        TableExpression(dialect, "users")
        # -> users

        # Schema-qualified table
        TableExpression(dialect, "users", schema_name="public")
        # -> public.users

        # With alias
        TableExpression(dialect, "users", alias="u")
        # -> users AS u

        # Schema-qualified with alias
        TableExpression(dialect, "users", schema_name="public", alias="u")
        # -> public.users AS u
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: str,
        schema_name: Optional[str] = None,
        alias: Optional[str] = None,
        temporal_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.name = name
        self.schema_name = schema_name
        self.alias = alias
        self.temporal_options = temporal_options or {}

    def to_sql(self) -> "SQLQueryAndParams":
        table_sql, params = self.dialect.format_table(self.name, self.alias, self.schema_name)
        if self.temporal_options:
            result = self.dialect.format_temporal_options(self.temporal_options)
            if result is not None:
                temporal_sql, temporal_params = result
                table_sql = f"{table_sql} {temporal_sql}"
                params += temporal_params
        return table_sql, params


class WildcardExpression(SQLValueExpression):
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

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_wildcard(self.table)
