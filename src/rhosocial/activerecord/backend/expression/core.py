# src/rhosocial/activerecord/backend/expression/core.py
"""
Core SQL expression components like columns, function calls, subqueries, and aliased expressions.
"""
from typing import Any, Tuple, Optional, Dict
from .base import SQLValueExpression, BaseExpression, SQLPredicate
from ..dialect import SQLDialectBase


class Column(SQLValueExpression):
    """Represents a column in a SQL query."""
    def __init__(self, dialect: SQLDialectBase, name: str, table: Optional[str] = None, alias: Optional[str] = None, filter_: Optional['SQLPredicate'] = None):
        """
        Initializes a Column SQL expression.

        Args:
            dialect: The SQL dialect instance to use for formatting this expression.
            name: The name of the column.
            table: Optional. The name of the table this column belongs to.
            alias: Optional. The alias for the column.
            filter_: Optional. A predicate for the FILTER (WHERE ...) clause.
        """
        super().__init__(dialect)
        self.name = name
        self.table = table
        self.alias = alias
        self.filter_ = filter_

    def to_sql(self) -> Tuple[str, tuple]:
        # Delegate to dialect for column formatting
        return self.dialect.format_column(self.name, self.table, self.alias)


class FunctionCall(SQLValueExpression):
    """Represents a SQL function call."""
    def __init__(self, dialect: SQLDialectBase, func_name: str, *args: BaseExpression, is_distinct: bool = False, alias: Optional[str] = None, filter_: Optional['SQLPredicate'] = None):
        """
        Initializes a SQL function call expression.

        Args:
            dialect: The SQL dialect instance to use for formatting this expression.
            func_name: The name of the SQL function.
            *args: Positional arguments for the function call (SQLExpression instances).
            is_distinct: If True, add DISTINCT keyword to arguments (e.g., COUNT(DISTINCT col)).
            alias: Optional. The alias for the function call result.
            filter_: Optional. A predicate for the FILTER (WHERE ...) clause.
        """
        super().__init__(dialect)
        self.func_name = func_name
        self.args = list(args)
        self.is_distinct = is_distinct
        self.alias = alias
        self.filter_ = filter_

    def to_sql(self) -> Tuple[str, tuple]:
        formatted_args_sql = []
        args_params = []
        for arg in self.args:
            arg_sql, arg_params_tuple = arg.to_sql()
            formatted_args_sql.append(arg_sql)
            args_params.append(arg_params_tuple)

        filter_sql, filter_params = None, None
        if self.filter_:
            # The "is not None" check is implicit.
            filter_sql, filter_params = self.filter_.to_sql()

        # Delegate to dialect for function call formatting
        return self.dialect.format_function_call(
            self.func_name,
            formatted_args_sql,
            args_params,
            self.is_distinct,
            self.alias,
            filter_sql=filter_sql,
            filter_params=filter_params
        )


class Subquery(SQLValueExpression):
    """Represents a subquery in a SQL expression."""
    def __init__(self, dialect: SQLDialectBase, query_sql: str, query_params: Tuple[Any, ...], alias: Optional[str] = None, filter_: Optional['SQLPredicate'] = None):
        """
        Initializes a Subquery SQL expression.

        Args:
            dialect: The SQL dialect instance to use for formatting this expression.
            query_sql: The raw SQL string of the subquery.
            query_params: A tuple of parameters associated with the subquery SQL.
            alias: The alias name for the subquery.
            filter_: Optional. A predicate for the FILTER (WHERE ...) clause.
        """
        super().__init__(dialect)
        self.query_sql = query_sql
        self.query_params = query_params
        self.alias = alias
        self.filter_ = filter_

    def to_sql(self) -> Tuple[str, tuple]:
        # Subquery is usually enclosed in parentheses
        subquery_sql = f"({self.query_sql})"
        if self.alias:  # Only add alias if provided
            return self.dialect.format_subquery(subquery_sql, self.query_params, self.alias)
        return subquery_sql, self.query_params


class TableExpression(SQLValueExpression):
    """Represents a table or view in a SQL query, optionally with an alias."""
    def __init__(self, dialect: SQLDialectBase, name: str, alias: Optional[str] = None, filter_: Optional['SQLPredicate'] = None, temporal_options: Optional[Dict[str, Any]] = None):
        """
        Initializes a Table SQL expression.

        Args:
            dialect: The SQL dialect instance to use for formatting this expression.
            name: The name of the table or view.
            alias: Optional. The alias for the table or view.
            filter_: Optional. A predicate for the FILTER (WHERE ...) clause.
            temporal_options: Optional. A dictionary of options for temporal queries.
        """
        super().__init__(dialect)
        self.name = name
        self.alias = alias
        self.filter_ = filter_
        self.temporal_options = temporal_options or {}

    def to_sql(self) -> Tuple[str, tuple]:
        # Delegate to dialect for table formatting, including its alias
        table_sql, params = self.dialect.format_table(self.name, self.alias)

        if self.temporal_options:
            temporal_sql, temporal_params = self.dialect.format_temporal_options(self.temporal_options)
            table_sql = f"{table_sql} {temporal_sql}"
            params += temporal_params
        
        return table_sql, params


