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
    """

    def __init__(self, dialect: "SQLDialectBase"):
        super().__init__(dialect)
        self._schema: Optional[str] = None

    def schema(self, name: str) -> "IntrospectionExpression":
        """Set the schema name."""
        self._schema = name
        return self

    def get_params(self) -> Dict[str, Any]:
        """Get all parameters.

        Subclasses should override this method to return specific parameters.

        Returns:
            Dictionary containing all parameters.
        """
        params: Dict[str, Any] = {}
        if self._schema is not None:
            params["schema"] = self._schema
        return params

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL. Subclasses must implement this method."""
        raise NotImplementedError("Subclasses must implement to_sql() method")


class DatabaseInfoExpression(IntrospectionExpression):
    """Expression for database information queries.

    Database info queries typically don't need parameters,
    but this class is provided for consistency and extensibility.
    """

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL, delegating to dialect's format_database_info_query method."""
        return self._dialect.format_database_info_query(self)


class TableListExpression(IntrospectionExpression):
    """Expression for table list queries.

    Collects parameters for listing tables in a database.
    """

    def __init__(self, dialect: "SQLDialectBase"):
        super().__init__(dialect)
        self._include_views: bool = True
        self._include_system: bool = False
        self._table_type: Optional[str] = None

    def include_views(self, value: bool = True) -> "TableListExpression":
        """Whether to include views."""
        self._include_views = value
        return self

    def include_system(self, value: bool = True) -> "TableListExpression":
        """Whether to include system tables."""
        self._include_system = value
        return self

    def table_type(self, ttype: str) -> "TableListExpression":
        """Filter by table type."""
        self._table_type = ttype
        return self

    def get_params(self) -> Dict[str, Any]:
        """Get all parameters."""
        params = super().get_params()
        params["include_views"] = self._include_views
        params["include_system"] = self._include_system
        if self._table_type is not None:
            params["table_type"] = self._table_type
        return params

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL, delegating to dialect's format_table_list_query method."""
        return self._dialect.format_table_list_query(self)


class TableInfoExpression(IntrospectionExpression):
    """Expression for single table information queries.

    Collects parameters for querying detailed information about a specific table.
    """

    def __init__(self, dialect: "SQLDialectBase", table_name: str):
        super().__init__(dialect)
        self._table_name = table_name
        self._include_columns: bool = True
        self._include_indexes: bool = True
        self._include_foreign_keys: bool = True

    def table_name(self, name: str) -> "TableInfoExpression":
        """Set the table name."""
        self._table_name = name
        return self

    def include_columns(self, value: bool = True) -> "TableInfoExpression":
        """Whether to include column information."""
        self._include_columns = value
        return self

    def include_indexes(self, value: bool = True) -> "TableInfoExpression":
        """Whether to include index information."""
        self._include_indexes = value
        return self

    def include_foreign_keys(self, value: bool = True) -> "TableInfoExpression":
        """Whether to include foreign key information."""
        self._include_foreign_keys = value
        return self

    def get_params(self) -> Dict[str, Any]:
        """Get all parameters."""
        params = super().get_params()
        params["table_name"] = self._table_name
        params["include_columns"] = self._include_columns
        params["include_indexes"] = self._include_indexes
        params["include_foreign_keys"] = self._include_foreign_keys
        return params

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL, delegating to dialect's format_table_info_query method."""
        return self._dialect.format_table_info_query(self)


class ColumnInfoExpression(IntrospectionExpression):
    """Expression for column information queries.

    Collects parameters for querying column information for a table.
    """

    def __init__(self, dialect: "SQLDialectBase", table_name: str):
        super().__init__(dialect)
        self._table_name = table_name
        self._include_hidden: bool = False

    def table_name(self, name: str) -> "ColumnInfoExpression":
        """Set the table name."""
        self._table_name = name
        return self

    def include_hidden(self, value: bool = True) -> "ColumnInfoExpression":
        """Whether to include hidden columns."""
        self._include_hidden = value
        return self

    def get_params(self) -> Dict[str, Any]:
        """Get all parameters."""
        params = super().get_params()
        params["table_name"] = self._table_name
        params["include_hidden"] = self._include_hidden
        return params

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL, delegating to dialect's format_column_info_query method."""
        return self._dialect.format_column_info_query(self)


class IndexInfoExpression(IntrospectionExpression):
    """Expression for index information queries.

    Collects parameters for querying index information for a table.
    """

    def __init__(self, dialect: "SQLDialectBase", table_name: str):
        super().__init__(dialect)
        self._table_name = table_name

    def table_name(self, name: str) -> "IndexInfoExpression":
        """Set the table name."""
        self._table_name = name
        return self

    def get_params(self) -> Dict[str, Any]:
        """Get all parameters."""
        params = super().get_params()
        params["table_name"] = self._table_name
        return params

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL, delegating to dialect's format_index_info_query method."""
        return self._dialect.format_index_info_query(self)


class ForeignKeyExpression(IntrospectionExpression):
    """Expression for foreign key information queries.

    Collects parameters for querying foreign key information for a table.
    """

    def __init__(self, dialect: "SQLDialectBase", table_name: str):
        super().__init__(dialect)
        self._table_name = table_name

    def table_name(self, name: str) -> "ForeignKeyExpression":
        """Set the table name."""
        self._table_name = name
        return self

    def get_params(self) -> Dict[str, Any]:
        """Get all parameters."""
        params = super().get_params()
        params["table_name"] = self._table_name
        return params

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL, delegating to dialect's format_foreign_key_query method."""
        return self._dialect.format_foreign_key_query(self)


class ViewListExpression(IntrospectionExpression):
    """Expression for view list queries.

    Collects parameters for listing views in a database.
    """

    def __init__(self, dialect: "SQLDialectBase"):
        super().__init__(dialect)
        self._include_system: bool = False

    def include_system(self, value: bool = True) -> "ViewListExpression":
        """Whether to include system views."""
        self._include_system = value
        return self

    def get_params(self) -> Dict[str, Any]:
        """Get all parameters."""
        params = super().get_params()
        params["include_system"] = self._include_system
        return params

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL, delegating to dialect's format_view_list_query method."""
        return self._dialect.format_view_list_query(self)


class ViewInfoExpression(IntrospectionExpression):
    """Expression for single view information queries.

    Collects parameters for querying detailed information about a specific view.
    """

    def __init__(self, dialect: "SQLDialectBase", view_name: str):
        super().__init__(dialect)
        self._view_name = view_name
        self._include_columns: bool = True

    def view_name(self, name: str) -> "ViewInfoExpression":
        """Set the view name."""
        self._view_name = name
        return self

    def include_columns(self, value: bool = True) -> "ViewInfoExpression":
        """Whether to include column information."""
        self._include_columns = value
        return self

    def get_params(self) -> Dict[str, Any]:
        """Get all parameters."""
        params = super().get_params()
        params["view_name"] = self._view_name
        params["include_columns"] = self._include_columns
        return params

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL, delegating to dialect's format_view_info_query method."""
        return self._dialect.format_view_info_query(self)


class TriggerListExpression(IntrospectionExpression):
    """Expression for trigger list queries.

    Collects parameters for listing triggers in a database.
    """

    def __init__(self, dialect: "SQLDialectBase"):
        super().__init__(dialect)
        self._table_name: Optional[str] = None

    def for_table(self, table_name: str) -> "TriggerListExpression":
        """Filter triggers for a specific table."""
        self._table_name = table_name
        return self

    def get_params(self) -> Dict[str, Any]:
        """Get all parameters."""
        params = super().get_params()
        if self._table_name is not None:
            params["table_name"] = self._table_name
        return params

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL, delegating to dialect's format_trigger_list_query method."""
        return self._dialect.format_trigger_list_query(self)


class TriggerInfoExpression(IntrospectionExpression):
    """Expression for single trigger information queries.

    Collects parameters for querying detailed information about a specific trigger.
    """

    def __init__(self, dialect: "SQLDialectBase", trigger_name: str):
        super().__init__(dialect)
        self._trigger_name = trigger_name
        self._table_name: Optional[str] = None

    def trigger_name(self, name: str) -> "TriggerInfoExpression":
        """Set the trigger name."""
        self._trigger_name = name
        return self

    def for_table(self, table_name: str) -> "TriggerInfoExpression":
        """Set the associated table name."""
        self._table_name = table_name
        return self

    def get_params(self) -> Dict[str, Any]:
        """Get all parameters."""
        params = super().get_params()
        params["trigger_name"] = self._trigger_name
        if self._table_name is not None:
            params["table_name"] = self._table_name
        return params

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL, delegating to dialect's format_trigger_info_query method."""
        return self._dialect.format_trigger_info_query(self)
