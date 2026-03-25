# src/rhosocial/activerecord/backend/introspection/expressions.py
"""
Introspection expression classes.

This module defines expression classes that collect parameters for
introspection queries. Expressions are passed to dialect's format_* methods
to generate database-specific SQL statements.

The expression pattern separates parameter collection from SQL generation:
- Expressions collect parameters (table_name, schema, options, etc.)
- Dialects generate SQL from expression parameters
- Backends execute SQL and parse results
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class IntrospectionExpression:
    """Base class for introspection expressions.

    Introspection expressions collect parameters for database introspection
    queries. They do not generate SQL directly - that's the dialect's job.

    The _params dictionary stores all parameters that will be passed to
    the dialect's format_* methods.
    """

    _params: Dict[str, Any] = field(default_factory=dict)

    def get_param(self, key: str, default: Any = None) -> Any:
        """Get a single parameter value.

        Args:
            key: Parameter name.
            default: Default value if parameter not found.

        Returns:
            Parameter value or default.
        """
        return self._params.get(key, default)

    def set_param(self, key: str, value: Any) -> None:
        """Set a single parameter value.

        Args:
            key: Parameter name.
            value: Parameter value.
        """
        self._params[key] = value

    def get_params(self) -> Dict[str, Any]:
        """Get all parameters as a dictionary.

        Returns:
            Copy of all parameters.
        """
        return self._params.copy()


@dataclass
class DatabaseInfoExpression(IntrospectionExpression):
    """Expression for database information queries.

    Database info queries typically don't need parameters,
    but this class is provided for consistency and future extensibility.
    """

    pass


@dataclass
class TableListExpression(IntrospectionExpression):
    """Expression for table list queries.

    Collects parameters for listing tables in a database.

    Attributes:
        include_views: Whether to include views in the result.
        include_system: Whether to include system tables.
        schema: Optional schema name to filter tables.
        table_type: Optional table type filter (e.g., 'BASE TABLE', 'VIEW').
    """

    include_views: bool = True
    include_system: bool = False
    schema: Optional[str] = None
    table_type: Optional[str] = None

    def __post_init__(self):
        """Populate params dictionary after initialization."""
        self._params["include_views"] = self.include_views
        self._params["include_system"] = self.include_system
        self._params["schema"] = self.schema
        self._params["table_type"] = self.table_type


@dataclass
class TableInfoExpression(IntrospectionExpression):
    """Expression for single table information queries.

    Collects parameters for querying detailed information about a specific table.

    Attributes:
        table_name: Name of the table to introspect.
        schema: Optional schema name.
        include_columns: Whether to include column information.
        include_indexes: Whether to include index information.
        include_foreign_keys: Whether to include foreign key information.
    """

    table_name: str = ""
    schema: Optional[str] = None
    include_columns: bool = True
    include_indexes: bool = True
    include_foreign_keys: bool = True

    def __post_init__(self):
        """Populate params dictionary after initialization."""
        self._params["table_name"] = self.table_name
        self._params["schema"] = self.schema
        self._params["include_columns"] = self.include_columns
        self._params["include_indexes"] = self.include_indexes
        self._params["include_foreign_keys"] = self.include_foreign_keys


@dataclass
class ColumnInfoExpression(IntrospectionExpression):
    """Expression for column information queries.

    Collects parameters for querying column information for a table.

    Attributes:
        table_name: Name of the table.
        include_hidden: Whether to include hidden columns (e.g., SQLite's hidden columns).
        schema: Optional schema name.
    """

    table_name: str = ""
    include_hidden: bool = False
    schema: Optional[str] = None

    def __post_init__(self):
        """Populate params dictionary after initialization."""
        self._params["table_name"] = self.table_name
        self._params["include_hidden"] = self.include_hidden
        self._params["schema"] = self.schema


@dataclass
class IndexInfoExpression(IntrospectionExpression):
    """Expression for index information queries.

    Collects parameters for querying index information for a table.

    Attributes:
        table_name: Name of the table.
        schema: Optional schema name.
    """

    table_name: str = ""
    schema: Optional[str] = None

    def __post_init__(self):
        """Populate params dictionary after initialization."""
        self._params["table_name"] = self.table_name
        self._params["schema"] = self.schema


@dataclass
class ForeignKeyExpression(IntrospectionExpression):
    """Expression for foreign key information queries.

    Collects parameters for querying foreign key information for a table.

    Attributes:
        table_name: Name of the table.
        schema: Optional schema name.
    """

    table_name: str = ""
    schema: Optional[str] = None

    def __post_init__(self):
        """Populate params dictionary after initialization."""
        self._params["table_name"] = self.table_name
        self._params["schema"] = self.schema


@dataclass
class ViewListExpression(IntrospectionExpression):
    """Expression for view list queries.

    Collects parameters for listing views in a database.

    Attributes:
        include_system: Whether to include system views.
        schema: Optional schema name to filter views.
    """

    include_system: bool = False
    schema: Optional[str] = None

    def __post_init__(self):
        """Populate params dictionary after initialization."""
        self._params["include_system"] = self.include_system
        self._params["schema"] = self.schema


@dataclass
class ViewInfoExpression(IntrospectionExpression):
    """Expression for single view information queries.

    Collects parameters for querying detailed information about a specific view.

    Attributes:
        view_name: Name of the view to introspect.
        schema: Optional schema name.
        include_columns: Whether to include column information.
    """

    view_name: str = ""
    schema: Optional[str] = None
    include_columns: bool = True

    def __post_init__(self):
        """Populate params dictionary after initialization."""
        self._params["view_name"] = self.view_name
        self._params["schema"] = self.schema
        self._params["include_columns"] = self.include_columns


@dataclass
class TriggerListExpression(IntrospectionExpression):
    """Expression for trigger list queries.

    Collects parameters for listing triggers in a database.

    Attributes:
        table_name: Optional table name to filter triggers.
        schema: Optional schema name.
    """

    table_name: Optional[str] = None
    schema: Optional[str] = None

    def __post_init__(self):
        """Populate params dictionary after initialization."""
        self._params["table_name"] = self.table_name
        self._params["schema"] = self.schema


@dataclass
class TriggerInfoExpression(IntrospectionExpression):
    """Expression for single trigger information queries.

    Collects parameters for querying detailed information about a specific trigger.

    Attributes:
        trigger_name: Name of the trigger to introspect.
        schema: Optional schema name.
    """

    trigger_name: str = ""
    schema: Optional[str] = None

    def __post_init__(self):
        """Populate params dictionary after initialization."""
        self._params["trigger_name"] = self.trigger_name
        self._params["schema"] = self.schema
