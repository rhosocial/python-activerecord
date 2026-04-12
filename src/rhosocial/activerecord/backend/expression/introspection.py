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

All expression classes support instantiation with complete parameters for
IDE introspection, static analysis, and MCP service integration. Parameters
can be provided at construction time or modified via fluent API methods.
"""

from typing import Any, Dict, Optional, TYPE_CHECKING

from .bases import BaseExpression, SQLQueryAndParams

if TYPE_CHECKING:
    from ..dialect import SQLDialectBase


class IntrospectionExpression(BaseExpression):
    """Base class for introspection expressions.

    All introspection expressions inherit from this class and provide
    fluent API for setting parameters. Introspection expressions hold
    a dialect reference and delegate SQL generation to the corresponding
    dialect via the to_sql() method.

    Args:
        dialect: The SQL dialect to use for SQL generation.
        schema: Optional schema name for the query. When provided at
            construction, the expression is immediately configured for
            the specified schema. Can also be set via the schema() method.

    Example:
        >>> expr = TableListExpression(dialect, schema='public')
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
        self._schema: Optional[str] = schema

    def schema(self, name: str) -> "IntrospectionExpression":
        """Set the schema name for the introspection query.

        This method provides a fluent API for setting the schema name.
        It can be chained with other configuration methods.

        Args:
            name: The schema name to query.

        Returns:
            Self for method chaining.

        Example:
            >>> expr = TableListExpression(dialect).schema('public')
        """
        self._schema = name
        return self

    def get_params(self) -> Dict[str, Any]:
        """Get all parameters collected by this expression.

        Subclasses should override this method to return specific parameters
        combined with the base parameters.

        Returns:
            Dictionary containing all parameters. Keys depend on the
            expression type and configuration.
        """
        params: Dict[str, Any] = {}
        if self._schema is not None:
            params["schema"] = self._schema
        return params

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL query and parameters.

        Subclasses must implement this method to delegate to the appropriate
        dialect format_* method.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            NotImplementedError: If not implemented by subclass.
        """
        raise NotImplementedError("Subclasses must implement to_sql() method")


class DatabaseInfoExpression(IntrospectionExpression):
    """Expression for database information queries.

    Database info queries typically don't need parameters beyond schema,
    but this class is provided for consistency and extensibility.

    Args:
        dialect: The SQL dialect to use for SQL generation.
        schema: Optional schema name. Defaults to None.

    Example:
        >>> expr = DatabaseInfoExpression(dialect)
        >>> sql, params = expr.to_sql()
    """

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL, delegating to dialect's format_database_info_query method.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return self._dialect.format_database_info_query(self)


class TableListExpression(IntrospectionExpression):
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
        >>> # All parameters at construction
        >>> expr = TableListExpression(dialect, schema='public',
        ...     include_views=True, include_system=False)
        >>> # Or using fluent API
        >>> expr = TableListExpression(dialect).include_views(False)
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
        self._include_views: bool = include_views
        self._include_system: bool = include_system
        self._table_type: Optional[str] = table_type

    def include_views(self, value: bool = True) -> "TableListExpression":
        """Set whether to include views in the result.

        Args:
            value: True to include views, False to exclude. Defaults to True.

        Returns:
            Self for method chaining.

        Example:
            >>> expr = TableListExpression(dialect).include_views(False)
        """
        self._include_views = value
        return self

    def include_system(self, value: bool = True) -> "TableListExpression":
        """Set whether to include system tables in the result.

        System tables are database metadata tables that are typically hidden
        from regular queries (e.g., sqlite_master in SQLite).

        Args:
            value: True to include system tables, False to exclude.
                Defaults to True.

        Returns:
            Self for method chaining.

        Example:
            >>> expr = TableListExpression(dialect).include_system(True)
        """
        self._include_system = value
        return self

    def table_type(self, ttype: str) -> "TableListExpression":
        """Filter results by a specific table type.

        Common table types include 'TABLE', 'VIEW', 'SYSTEM TABLE', etc.
        The exact values depend on the database backend.

        Args:
            ttype: The table type to filter by (e.g., 'TABLE', 'VIEW').

        Returns:
            Self for method chaining.

        Example:
            >>> expr = TableListExpression(dialect).table_type('TABLE')
        """
        self._table_type = ttype
        return self

    def get_params(self) -> Dict[str, Any]:
        """Get all parameters for this expression.

        Returns:
            Dictionary containing: schema (if set), include_views,
            include_system, and table_type (if set).
        """
        params = super().get_params()
        params["include_views"] = self._include_views
        params["include_system"] = self._include_system
        if self._table_type is not None:
            params["table_type"] = self._table_type
        return params

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL, delegating to dialect's format_table_list_query method.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return self._dialect.format_table_list_query(self)


class TableInfoExpression(IntrospectionExpression):
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
        >>> expr = TableInfoExpression(dialect, 'users', schema='public')
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
        self._table_name = table_name
        self._include_columns: bool = include_columns
        self._include_indexes: bool = include_indexes
        self._include_foreign_keys: bool = include_foreign_keys

    def table_name(self, name: str) -> "TableInfoExpression":
        """Set the table name to query.

        Args:
            name: The table name.

        Returns:
            Self for method chaining.

        Example:
            >>> expr = TableInfoExpression(dialect, 'old_table').table_name('new_table')
        """
        self._table_name = name
        return self

    def include_columns(self, value: bool = True) -> "TableInfoExpression":
        """Set whether to include column information.

        Column information includes column names, data types, nullability,
        default values, and other column attributes.

        Args:
            value: True to include column information, False to exclude.
                Defaults to True.

        Returns:
            Self for method chaining.

        Example:
            >>> expr = TableInfoExpression(dialect, 'users').include_columns(False)
        """
        self._include_columns = value
        return self

    def include_indexes(self, value: bool = True) -> "TableInfoExpression":
        """Set whether to include index information.

        Index information includes index names, columns, uniqueness,
        and other index attributes.

        Args:
            value: True to include index information, False to exclude.
                Defaults to True.

        Returns:
            Self for method chaining.

        Example:
            >>> expr = TableInfoExpression(dialect, 'users').include_indexes(False)
        """
        self._include_indexes = value
        return self

    def include_foreign_keys(self, value: bool = True) -> "TableInfoExpression":
        """Set whether to include foreign key information.

        Foreign key information includes constraint names, referenced
        tables, columns, and referential actions (ON DELETE, ON UPDATE).

        Args:
            value: True to include foreign key information, False to exclude.
                Defaults to True.

        Returns:
            Self for method chaining.

        Example:
            >>> expr = TableInfoExpression(dialect, 'users').include_foreign_keys(False)
        """
        self._include_foreign_keys = value
        return self

    def get_params(self) -> Dict[str, Any]:
        """Get all parameters for this expression.

        Returns:
            Dictionary containing: table_name, schema (if set),
            include_columns, include_indexes, and include_foreign_keys.
        """
        params = super().get_params()
        params["table_name"] = self._table_name
        params["include_columns"] = self._include_columns
        params["include_indexes"] = self._include_indexes
        params["include_foreign_keys"] = self._include_foreign_keys
        return params

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL, delegating to dialect's format_table_info_query method.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return self._dialect.format_table_info_query(self)


class ColumnInfoExpression(IntrospectionExpression):
    """Expression for column information queries.

    Collects parameters for querying column information for a table.

    Args:
        dialect: The SQL dialect to use for SQL generation.
        table_name: The name of the table to query columns for.
        schema: Optional schema name. Defaults to None.
        include_hidden: Whether to include hidden columns. Defaults to False.

    Example:
        >>> expr = ColumnInfoExpression(dialect, 'users', schema='public')
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
        self._table_name = table_name
        self._include_hidden: bool = include_hidden

    def table_name(self, name: str) -> "ColumnInfoExpression":
        """Set the table name to query columns for.

        Args:
            name: The table name.

        Returns:
            Self for method chaining.

        Example:
            >>> expr = ColumnInfoExpression(dialect, 'old').table_name('new')
        """
        self._table_name = name
        return self

    def include_hidden(self, value: bool = True) -> "ColumnInfoExpression":
        """Set whether to include hidden columns.

        Hidden columns are typically internal columns used by the database
        for specific purposes (e.g., SQLite's ROWID, generated columns).

        Args:
            value: True to include hidden columns, False to exclude.
                Defaults to True.

        Returns:
            Self for method chaining.

        Example:
            >>> expr = ColumnInfoExpression(dialect, 'users').include_hidden(True)
        """
        self._include_hidden = value
        return self

    def get_params(self) -> Dict[str, Any]:
        """Get all parameters for this expression.

        Returns:
            Dictionary containing: table_name, schema (if set),
            and include_hidden.
        """
        params = super().get_params()
        params["table_name"] = self._table_name
        params["include_hidden"] = self._include_hidden
        return params

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL, delegating to dialect's format_column_info_query method.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return self._dialect.format_column_info_query(self)


class IndexInfoExpression(IntrospectionExpression):
    """Expression for index information queries.

    Collects parameters for querying index information for a table.

    Args:
        dialect: The SQL dialect to use for SQL generation.
        table_name: The name of the table to query indexes for.
        schema: Optional schema name. Defaults to None.

    Example:
        >>> expr = IndexInfoExpression(dialect, 'users', schema='public')
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
        self._table_name = table_name

    def table_name(self, name: str) -> "IndexInfoExpression":
        """Set the table name to query indexes for.

        Args:
            name: The table name.

        Returns:
            Self for method chaining.

        Example:
            >>> expr = IndexInfoExpression(dialect, 'old').table_name('new')
        """
        self._table_name = name
        return self

    def get_params(self) -> Dict[str, Any]:
        """Get all parameters for this expression.

        Returns:
            Dictionary containing: table_name and schema (if set).
        """
        params = super().get_params()
        params["table_name"] = self._table_name
        return params

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL, delegating to dialect's format_index_info_query method.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return self._dialect.format_index_info_query(self)


class ForeignKeyExpression(IntrospectionExpression):
    """Expression for foreign key information queries.

    Collects parameters for querying foreign key information for a table.

    Args:
        dialect: The SQL dialect to use for SQL generation.
        table_name: The name of the table to query foreign keys for.
        schema: Optional schema name. Defaults to None.

    Example:
        >>> expr = ForeignKeyExpression(dialect, 'posts', schema='public')
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
        self._table_name = table_name

    def table_name(self, name: str) -> "ForeignKeyExpression":
        """Set the table name to query foreign keys for.

        Args:
            name: The table name.

        Returns:
            Self for method chaining.

        Example:
            >>> expr = ForeignKeyExpression(dialect, 'old').table_name('new')
        """
        self._table_name = name
        return self

    def get_params(self) -> Dict[str, Any]:
        """Get all parameters for this expression.

        Returns:
            Dictionary containing: table_name and schema (if set).
        """
        params = super().get_params()
        params["table_name"] = self._table_name
        return params

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL, delegating to dialect's format_foreign_key_query method.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return self._dialect.format_foreign_key_query(self)


class ViewListExpression(IntrospectionExpression):
    """Expression for view list queries.

    Collects parameters for listing views in a database.

    Args:
        dialect: The SQL dialect to use for SQL generation.
        schema: Optional schema name. Defaults to None.
        include_system: Whether to include system views. Defaults to False.

    Example:
        >>> expr = ViewListExpression(dialect, schema='public')
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
        self._include_system: bool = include_system

    def include_system(self, value: bool = True) -> "ViewListExpression":
        """Set whether to include system views.

        System views are database metadata views that are typically hidden
        from regular queries.

        Args:
            value: True to include system views, False to exclude.
                Defaults to True.

        Returns:
            Self for method chaining.

        Example:
            >>> expr = ViewListExpression(dialect).include_system(True)
        """
        self._include_system = value
        return self

    def get_params(self) -> Dict[str, Any]:
        """Get all parameters for this expression.

        Returns:
            Dictionary containing: schema (if set) and include_system.
        """
        params = super().get_params()
        params["include_system"] = self._include_system
        return params

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL, delegating to dialect's format_view_list_query method.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return self._dialect.format_view_list_query(self)


class ViewInfoExpression(IntrospectionExpression):
    """Expression for single view information queries.

    Collects parameters for querying detailed information about a specific
    view, including its columns and definition.

    Args:
        dialect: The SQL dialect to use for SQL generation.
        view_name: The name of the view to query.
        schema: Optional schema name. Defaults to None.
        include_columns: Whether to include column information. Defaults to True.

    Example:
        >>> expr = ViewInfoExpression(dialect, 'user_view', schema='public')
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
        self._view_name = view_name
        self._include_columns: bool = include_columns

    def view_name(self, name: str) -> "ViewInfoExpression":
        """Set the view name to query.

        Args:
            name: The view name.

        Returns:
            Self for method chaining.

        Example:
            >>> expr = ViewInfoExpression(dialect, 'old_view').view_name('new_view')
        """
        self._view_name = name
        return self

    def include_columns(self, value: bool = True) -> "ViewInfoExpression":
        """Set whether to include column information.

        Column information includes column names, data types, and other
        column attributes for the view's result set.

        Args:
            value: True to include column information, False to exclude.
                Defaults to True.

        Returns:
            Self for method chaining.

        Example:
            >>> expr = ViewInfoExpression(dialect, 'my_view').include_columns(False)
        """
        self._include_columns = value
        return self

    def get_params(self) -> Dict[str, Any]:
        """Get all parameters for this expression.

        Returns:
            Dictionary containing: view_name, schema (if set),
            and include_columns.
        """
        params = super().get_params()
        params["view_name"] = self._view_name
        params["include_columns"] = self._include_columns
        return params

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL, delegating to dialect's format_view_info_query method.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return self._dialect.format_view_info_query(self)


class TriggerListExpression(IntrospectionExpression):
    """Expression for trigger list queries.

    Collects parameters for listing triggers in a database, optionally
    filtered by table.

    Args:
        dialect: The SQL dialect to use for SQL generation.
        schema: Optional schema name. Defaults to None.
        table_name: Optional table name to filter triggers. Defaults to None.

    Example:
        >>> # List all triggers
        >>> expr = TriggerListExpression(dialect)
        >>> # List triggers for a specific table
        >>> expr = TriggerListExpression(dialect, table_name='users')
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
        self._table_name: Optional[str] = table_name

    def for_table(self, table_name: str) -> "TriggerListExpression":
        """Filter triggers for a specific table.

        Args:
            table_name: The table name to filter triggers by.

        Returns:
            Self for method chaining.

        Example:
            >>> expr = TriggerListExpression(dialect).for_table('users')
        """
        self._table_name = table_name
        return self

    def get_params(self) -> Dict[str, Any]:
        """Get all parameters for this expression.

        Returns:
            Dictionary containing: schema (if set) and table_name (if set).
        """
        params = super().get_params()
        if self._table_name is not None:
            params["table_name"] = self._table_name
        return params

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL, delegating to dialect's format_trigger_list_query method.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return self._dialect.format_trigger_list_query(self)


class TriggerInfoExpression(IntrospectionExpression):
    """Expression for single trigger information queries.

    Collects parameters for querying detailed information about a specific
    trigger, including its definition and associated table.

    Args:
        dialect: The SQL dialect to use for SQL generation.
        trigger_name: The name of the trigger to query.
        schema: Optional schema name. Defaults to None.
        table_name: Optional associated table name. Defaults to None.

    Example:
        >>> expr = TriggerInfoExpression(dialect, 'my_trigger', table_name='users')
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
        self._trigger_name = trigger_name
        self._table_name: Optional[str] = table_name

    def trigger_name(self, name: str) -> "TriggerInfoExpression":
        """Set the trigger name to query.

        Args:
            name: The trigger name.

        Returns:
            Self for method chaining.

        Example:
            >>> expr = TriggerInfoExpression(dialect, 'old').trigger_name('new')
        """
        self._trigger_name = name
        return self

    def for_table(self, table_name: str) -> "TriggerInfoExpression":
        """Set the associated table name.

        Some databases require the table name to uniquely identify a trigger,
        as trigger names may not be globally unique.

        Args:
            table_name: The associated table name.

        Returns:
            Self for method chaining.

        Example:
            >>> expr = TriggerInfoExpression(dialect, 'my_trigger').for_table('users')
        """
        self._table_name = table_name
        return self

    def get_params(self) -> Dict[str, Any]:
        """Get all parameters for this expression.

        Returns:
            Dictionary containing: trigger_name, schema (if set),
            and table_name (if set).
        """
        params = super().get_params()
        params["trigger_name"] = self._trigger_name
        if self._table_name is not None:
            params["table_name"] = self._table_name
        return params

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL, delegating to dialect's format_trigger_info_query method.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return self._dialect.format_trigger_info_query(self)
