# src/rhosocial/activerecord/backend/expression/introspection.py
"""
Database introspection expression classes.

This module defines expression classes that collect parameters for
introspection queries. Expressions separate parameter collection from
SQL generation:
- Expressions collect parameters (table_name, schema, options, etc.)
- Dialect's format_* methods generate SQL from expression parameters
- Backends execute SQL and parse results

Expression classes inherit from BaseExpression and implement to_sql(),
delegating SQL generation to the dialect's corresponding format_* method.

Every statement collects all of its parameters at construction. There is no
fluent API: a statement is asked once, with everything it needs, and is never
edited afterwards. Constructing the final question in one call is what makes
the parameters readable to IDE introspection, static analysis and MCP service
integration -- a chain of setters hides them behind the last call.
"""

from typing import Optional, TYPE_CHECKING

from .bases import BaseExpression

if TYPE_CHECKING:
    from ..dialect import SQLDialectBase


class IntrospectionExpression(BaseExpression):
    """Base class for introspection expressions.

    All introspection expressions inherit from this class. An introspection
    expression holds a dialect reference and the parameters of one catalogue
    question, and delegates SQL generation to the corresponding dialect via
    the to_sql() method.

    Args:
        dialect: The SQL dialect to use for SQL generation.
        schema: Optional schema name for the query, collected here with the
            rest of the parameters.

    Example:
        >>> expr = TableListQueryStatement(dialect, schema='public')
        >>> sql, params = expr.to_sql()
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        schema: Optional[str] = None,
    ):
        """Initialize the introspection expression.

        Args:
            dialect: The SQL dialect to use for SQL generation.
            schema: Optional schema name. Defaults to None.
        """
        super().__init__(dialect)
        self.schema: Optional[str] = schema


class DatabaseInfoQueryStatement(IntrospectionExpression):
    """Expression for database information queries.

    Database info queries typically don't need parameters beyond schema,
    but this class is provided for consistency and extensibility.

    Args:
        dialect: The SQL dialect to use for SQL generation.
        schema: Optional schema name. Defaults to None.

    Example:
        >>> expr = DatabaseInfoQueryStatement(dialect)
        >>> sql, params = expr.to_sql()
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_database_info_query_statement"


class TableListQueryStatement(IntrospectionExpression):
    """Expression for table list queries.

    Collects parameters for listing tables in a database. Supports filtering
    by table type, inclusion of views and system tables.

    Args:
        dialect: The SQL dialect to use for SQL generation.
        schema: Optional schema name. Defaults to None.
        include_views: Whether to include views in the result. Defaults to True.
        include_system: Whether to include system tables. Defaults to False.
        table_type: Optional table type filter (e.g., 'TABLE', 'VIEW').
            Defaults to None (no filter).

    Example:
        >>> expr = TableListQueryStatement(dialect, schema='public',
        ...     include_views=True, include_system=False)
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        schema: Optional[str] = None,
        include_views: bool = True,
        include_system: bool = False,
        table_type: Optional[str] = None,
    ):
        """Initialize the table list expression.

        Args:
            dialect: The SQL dialect to use for SQL generation.
            schema: Optional schema name. Defaults to None.
            include_views: Whether to include views. Defaults to True.
            include_system: Whether to include system tables. Defaults to False.
            table_type: Optional table type filter. Defaults to None.
        """
        super().__init__(dialect, schema)
        self.include_views: bool = include_views
        self.include_system: bool = include_system
        self.table_type: Optional[str] = table_type


    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_table_list_query_statement"


class UnusedIndexesQueryStatement(IntrospectionExpression):
    """Expression for listing indexes the engine reports as never used.

    No parameters beyond the schema every other catalogue question carries: an
    unused index is a fact about a whole database, not about one table, so
    narrowing it by table would be the caller's job on the way back and would
    only invite a dialect to render a filter it cannot honour consistently.

    Example:
        >>> expr = UnusedIndexesQueryStatement(dialect, schema='public')
        >>> sql, params = expr.to_sql()
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_unused_indexes_query_statement"


class TableUsageStatsQueryStatement(IntrospectionExpression):
    """Expression for per-table usage counters.

    Answers for every table in one query, as the counters themselves are the
    answer: a single-table form would invite a caller to loop the catalogue
    one table at a time, and statistics collectors price their first query
    far above their next.

    Example:
        >>> expr = TableUsageStatsQueryStatement(dialect, schema='public')
        >>> sql, params = expr.to_sql()
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_table_usage_stats_query_statement"


class RuntimeMetricsQueryStatement(IntrospectionExpression):
    """Expression for the engine's live runtime measurements.

    No parameters beyond the schema: runtime facts describe the *server*, not
    one object in it, so narrowing by table would invite a dialect to render a
    filter that does not apply to what is being measured.

    Example:
        >>> expr = RuntimeMetricsQueryStatement(dialect, schema='public')
        >>> sql, params = expr.to_sql()
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_runtime_metrics_query_statement"


class IndexUsageStatsQueryStatement(IntrospectionExpression):
    """Expression for per-index use counters across a schema.

    One query for the schema, for the same reason as the usage-stats family:
    a per-index form would invite a caller to loop the catalogue one index at
    a time, and use counters are cheap to ask for all at once and expensive
    to ask for one.

    Example:
        >>> expr = IndexUsageStatsQueryStatement(dialect, schema='public')
        >>> sql, params = expr.to_sql()
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_index_usage_stats_query_statement"


class ObjectDependencyQueryStatement(IntrospectionExpression):
    """Expression for the object dependency graph.

    ``object_name`` narrows to one object's dependants when the caller names
    it -- the "what breaks if I drop this" question -- and is omitted for the
    whole graph, which is a different and much larger answer.

    Example:
        >>> expr = ObjectDependencyQueryStatement(dialect, schema='public')
        >>> sql, params = expr.to_sql()
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_object_dependency_query_statement"


class DDLStatementQueryStatement(IntrospectionExpression):
    """Expression for the DDL that recreates one object.

    ``object_name`` is required: unlike the other families, this answers for
    exactly one object, because a DDL text is large and the question is always
    about a specific thing. ``object_type`` names what kind it is when the
    caller knows (table, view, index), and is omitted when it does not, in
    which case the dialect searches the kinds it can retrieve.

    Example:
        >>> expr = DDLStatementQueryStatement(
        ...     dialect, table_name='orders', schema='public'
        ... )
        >>> sql, params = expr.to_sql()
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_ddl_statement_query_statement"


class TableInfoQueryStatement(IntrospectionExpression):
    """Expression for single table information queries.

    Collects parameters for querying detailed information about a specific
    table, including columns, indexes, and foreign keys.

    Args:
        dialect: The SQL dialect to use for SQL generation.
        table_name: The name of the table to query.
        schema: Optional schema name. Defaults to None.
        include_columns: Whether to include column information. Defaults to True.
        include_indexes: Whether to include index information. Defaults to True.
        include_foreign_keys: Whether to include foreign key info. Defaults to True.

    Example:
        >>> expr = TableInfoQueryStatement(dialect, 'users', schema='public')
        >>> sql, params = expr.to_sql()
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table_name: str,
        schema: Optional[str] = None,
        include_columns: bool = True,
        include_indexes: bool = True,
        include_foreign_keys: bool = True,
    ):
        """Initialize the table info expression.

        Args:
            dialect: The SQL dialect to use for SQL generation.
            table_name: The name of the table to query.
            schema: Optional schema name. Defaults to None.
            include_columns: Whether to include column information. Defaults to True.
            include_indexes: Whether to include index information. Defaults to True.
            include_foreign_keys: Whether to include foreign key info. Defaults to True.
        """
        super().__init__(dialect, schema)
        self.table_name = table_name
        self.include_columns: bool = include_columns
        self.include_indexes: bool = include_indexes
        self.include_foreign_keys: bool = include_foreign_keys


    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_table_info_query_statement"


class ColumnInfoQueryStatement(IntrospectionExpression):
    """Expression for column information queries.

    Collects parameters for querying column information for a table.

    Args:
        dialect: The SQL dialect to use for SQL generation.
        table_name: The name of the table to query columns for.
        schema: Optional schema name. Defaults to None.
        include_hidden: Whether to include hidden columns. Defaults to False.

    Example:
        >>> expr = ColumnInfoQueryStatement(dialect, 'users', schema='public')
        >>> sql, params = expr.to_sql()
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table_name: str,
        schema: Optional[str] = None,
        include_hidden: bool = False,
    ):
        """Initialize the column info expression.

        Args:
            dialect: The SQL dialect to use for SQL generation.
            table_name: The name of the table to query columns for.
            schema: Optional schema name. Defaults to None.
            include_hidden: Whether to include hidden columns. Defaults to False.
        """
        super().__init__(dialect, schema)
        self.table_name = table_name
        self.include_hidden: bool = include_hidden


    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_column_info_query_statement"


class IndexInfoQueryStatement(IntrospectionExpression):
    """Expression for index information queries.

    Collects parameters for querying index information for a table.

    Args:
        dialect: The SQL dialect to use for SQL generation.
        table_name: The name of the table to query indexes for.
        schema: Optional schema name. Defaults to None.

    Example:
        >>> expr = IndexInfoQueryStatement(dialect, 'users', schema='public')
        >>> sql, params = expr.to_sql()
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table_name: str,
        schema: Optional[str] = None,
    ):
        """Initialize the index info expression.

        Args:
            dialect: The SQL dialect to use for SQL generation.
            table_name: The name of the table to query indexes for.
            schema: Optional schema name. Defaults to None.
        """
        super().__init__(dialect, schema)
        self.table_name = table_name


    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_index_info_query_statement"


class ForeignKeyQueryStatement(IntrospectionExpression):
    """Expression for foreign key information queries.

    Collects parameters for querying foreign key information for a table.

    Args:
        dialect: The SQL dialect to use for SQL generation.
        table_name: The name of the table to query foreign keys for.
        schema: Optional schema name. Defaults to None.

    Example:
        >>> expr = ForeignKeyQueryStatement(dialect, 'posts', schema='public')
        >>> sql, params = expr.to_sql()
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table_name: str,
        schema: Optional[str] = None,
    ):
        """Initialize the foreign key expression.

        Args:
            dialect: The SQL dialect to use for SQL generation.
            table_name: The name of the table to query foreign keys for.
            schema: Optional schema name. Defaults to None.
        """
        super().__init__(dialect, schema)
        self.table_name = table_name


    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_foreign_key_query_statement"


class ViewListQueryStatement(IntrospectionExpression):
    """Expression for view list queries.

    Collects parameters for listing views in a database.

    Args:
        dialect: The SQL dialect to use for SQL generation.
        schema: Optional schema name. Defaults to None.
        include_system: Whether to include system views. Defaults to False.

    Example:
        >>> expr = ViewListQueryStatement(dialect, schema='public')
        >>> sql, params = expr.to_sql()
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        schema: Optional[str] = None,
        include_system: bool = False,
    ):
        """Initialize the view list expression.

        Args:
            dialect: The SQL dialect to use for SQL generation.
            schema: Optional schema name. Defaults to None.
            include_system: Whether to include system views. Defaults to False.
        """
        super().__init__(dialect, schema)
        self.include_system: bool = include_system


    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_view_list_query_statement"


class ViewInfoQueryStatement(IntrospectionExpression):
    """Expression for single view information queries.

    Collects parameters for querying detailed information about a specific
    view, including its columns and definition.

    Args:
        dialect: The SQL dialect to use for SQL generation.
        view_name: The name of the view to query.
        schema: Optional schema name. Defaults to None.
        include_columns: Whether to include column information. Defaults to True.

    Example:
        >>> expr = ViewInfoQueryStatement(dialect, 'user_view', schema='public')
        >>> sql, params = expr.to_sql()
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        view_name: str,
        schema: Optional[str] = None,
        include_columns: bool = True,
    ):
        """Initialize the view info expression.

        Args:
            dialect: The SQL dialect to use for SQL generation.
            view_name: The name of the view to query.
            schema: Optional schema name. Defaults to None.
            include_columns: Whether to include column information. Defaults to True.
        """
        super().__init__(dialect, schema)
        self.view_name = view_name
        self.include_columns: bool = include_columns


    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_view_info_query_statement"


class TriggerListQueryStatement(IntrospectionExpression):
    """Expression for trigger list queries.

    Collects parameters for listing triggers in a database, optionally
    filtered by table.

    Args:
        dialect: The SQL dialect to use for SQL generation.
        schema: Optional schema name. Defaults to None.
        table_name: Optional table name to filter triggers. Defaults to None.

    Example:
        >>> # List all triggers
        >>> expr = TriggerListQueryStatement(dialect)
        >>> # List triggers for a specific table
        >>> expr = TriggerListQueryStatement(dialect, table_name='users')
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        schema: Optional[str] = None,
        table_name: Optional[str] = None,
    ):
        """Initialize the trigger list expression.

        Args:
            dialect: The SQL dialect to use for SQL generation.
            schema: Optional schema name. Defaults to None.
            table_name: Optional table name to filter triggers. Defaults to None.
        """
        super().__init__(dialect, schema)
        self.table_name: Optional[str] = table_name


    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_trigger_list_query_statement"


class TriggerInfoQueryStatement(IntrospectionExpression):
    """Expression for single trigger information queries.

    Collects parameters for querying detailed information about a specific
    trigger, including its definition and associated table.

    Args:
        dialect: The SQL dialect to use for SQL generation.
        trigger_name: The name of the trigger to query.
        schema: Optional schema name. Defaults to None.
        table_name: Optional associated table name. Defaults to None.

    Example:
        >>> expr = TriggerInfoQueryStatement(dialect, 'my_trigger', table_name='users')
        >>> sql, params = expr.to_sql()
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        trigger_name: str,
        schema: Optional[str] = None,
        table_name: Optional[str] = None,
    ):
        """Initialize the trigger info expression.

        Args:
            dialect: The SQL dialect to use for SQL generation.
            trigger_name: The name of the trigger to query.
            schema: Optional schema name. Defaults to None.
            table_name: Optional associated table name. Defaults to None.
        """
        super().__init__(dialect, schema)
        self.trigger_name = trigger_name
        self.table_name: Optional[str] = table_name


    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_trigger_info_query_statement"
