# src/rhosocial/activerecord/backend/expression/statements/ddl_view.py
"""View DDL statement expressions."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING

from ..bases import BaseExpression

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


@dataclass
class ColumnAlias:
    """Represents a column alias in a view definition."""

    name: str  # Column name
    alias: Optional[str] = None  # Optional alias for the column


class ViewAlgorithm(Enum):
    """Algorithm types for MySQL-style view creation."""

    UNDEFINED = "UNDEFINED"
    MERGE = "MERGE"
    TEMPTABLE = "TEMPTABLE"


class ViewCheckOption(Enum):
    """Check options for view constraints."""

    NONE = "NONE"
    LOCAL = "LOCAL"
    CASCADED = "CASCADED"


@dataclass
class ViewOptions:
    """Options for view creation, supporting various database-specific features."""

    algorithm: Optional[ViewAlgorithm] = None  # MySQL-specific
    definer: Optional[str] = None  # MySQL-specific (user@host)
    security: Optional[str] = None  # SQL SECURITY (DEFINER, INVOKER)
    schemabinding: bool = False  # SQL Server-specific
    encryption: bool = False  # SQL Server-specific
    materialized: bool = False  # PostgreSQL-like (for materialized views)
    recursive: bool = False  # For recursive CTE-based views
    force: bool = False  # Oracle-specific (create even if base tables don't exist)
    read_only: bool = False  # Oracle-specific
    check_option: Optional[ViewCheckOption] = None  # WITH CHECK OPTION variants
    dialect_options: Optional[Dict[str, Any]] = None  # Database-specific options


class CreateViewExpression(BaseExpression):
    """
    Represents a CREATE VIEW statement supporting full SQL standard features and extensions.

    Views are virtual tables based on the result-set of a SELECT statement. They can be queried
    like regular tables but don't store data themselves. Views provide a way to simplify complex
    queries, enforce security, and abstract schema changes.

    Examples:
        # Basic view creation
        basic_view = CreateViewExpression(
            dialect,
            view_name="customer_info",
            query=QueryExpression(
                dialect,
                select=[Column(dialect, "id"), Column(dialect, "name"), Column(dialect, "email")],
                from_=TableExpression(dialect, "customers")
            )
        )

        # View with column aliases
        aliased_view = CreateViewExpression(
            dialect,
            view_name="user_summary",
            query=QueryExpression(
                dialect,
                select=[
                    Column(dialect, "user_id").alias("id"),
                    FunctionCall(dialect, "COUNT", Column(dialect, "order_id")).alias("total_orders")
                ],
                from_=TableExpression(dialect, "orders"),
                group_by=[Column(dialect, "user_id")]
            ),
            column_aliases=["id", "total_orders"]
        )

        # MySQL-style view with algorithm
        mysql_view = CreateViewExpression(
            dialect,
            view_name="optimized_view",
            query=some_query,
            options=ViewOptions(algorithm=ViewAlgorithm.MERGE)
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        view_name: str,
        query: "QueryExpression",
        column_aliases: Optional[List[Union[str, ColumnAlias]]] = None,
        replace: bool = False,  # CREATE OR REPLACE
        temporary: bool = False,  # CREATE TEMPORARY VIEW (some DBs)
        options: Optional[ViewOptions] = None,
    ):
        super().__init__(dialect)
        self.view_name = view_name
        self.query = query
        self.column_aliases = column_aliases or []
        self.replace = replace  # Whether to use CREATE OR REPLACE semantics
        self.temporary = temporary  # Whether to create a temporary view
        self.options = options or ViewOptions()

    def to_sql(self) -> "SQLQueryAndParams":
        """Delegates SQL generation for the CREATE VIEW statement to the configured dialect."""
        return self.dialect.format_create_view_statement(self)


class DropViewExpression(BaseExpression):
    """
    Represents a DROP VIEW statement supporting standard and extended features.

    This class handles view deletion with options for different database systems.

    Examples:
        # Basic view drop
        drop_view = DropViewExpression(dialect, view_name="old_view")

        # Drop with IF EXISTS
        drop_safe = DropViewExpression(
            dialect,
            view_name="possibly_missing_view",
            if_exists=True
        )

        # Cascade drop (drops dependent objects)
        drop_cascade = DropViewExpression(
            dialect,
            view_name="master_view",
            cascade=True
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        view_name: str,
        if_exists: bool = False,  # DROP VIEW IF EXISTS
        cascade: bool = False,
    ):  # DROP VIEW ... CASCADE (drops dependent objects)
        super().__init__(dialect)
        self.view_name = view_name
        self.if_exists = if_exists
        self.cascade = cascade

    def to_sql(self) -> "SQLQueryAndParams":
        """Delegates SQL generation for the DROP VIEW statement to the configured dialect."""
        return self.dialect.format_drop_view_statement(self)


class CreateMaterializedViewExpression(BaseExpression):
    """
    Represents a CREATE MATERIALIZED VIEW statement.

    Materialized views are database objects that contain the results of a query.
    Unlike regular views, materialized views store data physically and can be
    refreshed to update their contents. They are useful for precomputing and
    caching complex query results.

    Support varies by database:
    - PostgreSQL: Full support with storage options
    - Oracle: Full support with refresh options
    - SQL Server: Uses indexed views (different syntax)
    - MySQL: Not supported (uses different mechanisms)
    - SQLite: Not supported

    Examples:
        # Basic materialized view
        create_mv = CreateMaterializedViewExpression(
            dialect,
            view_name="user_order_summary",
            query=QueryExpression(
                dialect,
                select=[
                    Column(dialect, "user_id"),
                    FunctionCall(dialect, "COUNT", Column(dialect, "order_id"))
                ],
                from_=TableExpression(dialect, "orders"),
                group_by_having=GroupByHavingClause(
                    dialect,
                    group_by=[Column(dialect, "user_id")]
                )
            )
        )

        # Materialized view with storage options
        create_mv = CreateMaterializedViewExpression(
            dialect,
            view_name="sales_summary",
            query=sales_query,
            tablespace="slow_storage",
            with_data=True  # Populate immediately
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        view_name: str,
        query: "QueryExpression",
        column_aliases: Optional[List[str]] = None,
        tablespace: Optional[str] = None,
        with_data: bool = True,  # Whether to populate immediately
        storage_options: Optional[Dict[str, Any]] = None,
        *,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.view_name = view_name
        self.query = query
        self.column_aliases = column_aliases or []
        self.tablespace = tablespace
        self.with_data = with_data
        self.storage_options = storage_options or {}
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> "SQLQueryAndParams":
        """Delegates SQL generation for CREATE MATERIALIZED VIEW to the dialect."""
        return self.dialect.format_create_materialized_view_statement(self)


class DropMaterializedViewExpression(BaseExpression):
    """
    Represents a DROP MATERIALIZED VIEW statement.

    Examples:
        # Basic drop
        drop_mv = DropMaterializedViewExpression(
            dialect,
            view_name="old_summary"
        )

        # Drop with IF EXISTS
        drop_mv = DropMaterializedViewExpression(
            dialect,
            view_name="possibly_missing",
            if_exists=True
        )

        # Cascade drop
        drop_mv = DropMaterializedViewExpression(
            dialect,
            view_name="parent_view",
            cascade=True
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        view_name: str,
        if_exists: bool = False,
        cascade: bool = False,
        *,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.view_name = view_name
        self.if_exists = if_exists
        self.cascade = cascade
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> "SQLQueryAndParams":
        """Delegates SQL generation for DROP MATERIALIZED VIEW to the dialect."""
        return self.dialect.format_drop_materialized_view_statement(self)


class RefreshMaterializedViewExpression(BaseExpression):
    """
    Represents a REFRESH MATERIALIZED VIEW statement.

    This statement updates the contents of a materialized view by re-executing
    its defining query. Different databases offer different refresh strategies.

    Examples:
        # Basic refresh
        refresh_mv = RefreshMaterializedViewExpression(
            dialect,
            view_name="sales_summary"
        )

        # Refresh with concurrent option (PostgreSQL)
        refresh_mv = RefreshMaterializedViewExpression(
            dialect,
            view_name="user_stats",
            concurrent=True
        )

        # Refresh without data (PostgreSQL)
        refresh_mv = RefreshMaterializedViewExpression(
            dialect,
            view_name="empty_view",
            with_data=False
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        view_name: str,
        concurrent: bool = False,  # Refresh concurrently (PostgreSQL)
        with_data: Optional[bool] = None,  # WITH DATA or WITH NO DATA
        *,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.view_name = view_name
        self.concurrent = concurrent
        self.with_data = with_data
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> "SQLQueryAndParams":
        """Delegates SQL generation for REFRESH MATERIALIZED VIEW to the dialect."""
        return self.dialect.format_refresh_materialized_view_statement(self)
