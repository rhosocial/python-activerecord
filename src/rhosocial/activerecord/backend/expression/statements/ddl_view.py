# src/rhosocial/activerecord/backend/expression/statements/ddl_view.py
"""View DDL statement expressions."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING

from ..bases import BaseExpression
from ..objects import MaterializedView, View

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase
    from .dql import QueryStatement


@dataclass
class ColumnAlias:
    """Represents a column alias in a view definition."""

    name: str  # Column name
    alias: Optional[str] = None  # Optional alias for the column


class ViewAlgorithm(str, Enum):
    """Algorithm types for MySQL-style view creation."""

    #: A member *is* the word it carries; see ``SortDirection.__str__``.
    __str__ = str.__str__

    UNDEFINED = "UNDEFINED"
    MERGE = "MERGE"
    TEMPTABLE = "TEMPTABLE"


class ViewCheckOption(str, Enum):
    """Check options for view constraints."""

    #: A member *is* the word it carries; see ``SortDirection.__str__``.
    __str__ = str.__str__

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


class CreateViewStatement(BaseExpression):
    """
    Represents a CREATE VIEW statement supporting full SQL standard features and extensions.

    Views are virtual tables based on the result-set of a SELECT statement. They can be queried
    like regular tables but don't store data themselves. Views provide a way to simplify complex
    queries, enforce security, and abstract schema changes.

    Examples:
        # Basic view creation
        basic_view = CreateViewStatement(
            dialect,
            view=View(dialect, "customer_info"),
            query=QueryStatement(
                dialect,
                select=[Column(dialect, "id"), Column(dialect, "name"), Column(dialect, "email")],
                from_=NamedRelationRef(dialect, Table(dialect, "customers"))
            )
        )

        # View with column aliases
        aliased_view = CreateViewStatement(
            dialect,
            view=View(dialect, "user_summary"),
            query=QueryStatement(
                dialect,
                select=[
                    Column(dialect, "user_id").alias("id"),
                    FunctionCall(dialect, "COUNT", Column(dialect, "order_id")).alias("total_orders")
                ],
                from_=NamedRelationRef(dialect, Table(dialect, "orders")),
                group_by=[Column(dialect, "user_id")]
            ),
            column_aliases=["id", "total_orders"]
        )

        # MySQL-style view with algorithm
        mysql_view = CreateViewStatement(
            dialect,
            view=View(dialect, "optimized_view"),
            query=some_query,
            options=ViewOptions(algorithm=ViewAlgorithm.MERGE)
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        view: "View",
        query: "QueryStatement",
        column_aliases: Optional[List[Union[str, ColumnAlias]]] = None,
        replace: bool = False,  # CREATE OR REPLACE
        temporary: bool = False,  # CREATE TEMPORARY VIEW (some DBs)
        if_not_exists: bool = False,  # CREATE VIEW IF NOT EXISTS
        options: Optional[ViewOptions] = None,
    ):
        super().__init__(dialect)
        self.view = view
        self.query = query
        self.column_aliases = column_aliases or []
        self.replace = replace  # Whether to use CREATE OR REPLACE semantics
        self.temporary = temporary  # Whether to create a temporary view
        self.if_not_exists = if_not_exists  # Whether to use IF NOT EXISTS
        self.options = options or ViewOptions()

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_create_view_statement"


class DropViewStatement(BaseExpression):
    """
    Represents a DROP VIEW statement supporting standard and extended features.

    This class handles view deletion with options for different database systems.

    Examples:
        # Basic view drop
        drop_view = DropViewStatement(dialect, view=View(dialect, "old_view"))

        # Drop with IF EXISTS
        drop_safe = DropViewStatement(
            dialect,
            view=View(dialect, "possibly_missing_view"),
            if_exists=True
        )

        # Cascade drop (drops dependent objects)
        drop_cascade = DropViewStatement(
            dialect,
            view=View(dialect, "master_view"),
            cascade=True
        )

        # Restrict drop (refuses if objects depend on the view)
        drop_restrict = DropViewStatement(
            dialect,
            view=View(dialect, "master_view"),
            restrict=True
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        view: "View",
        if_exists: bool = False,  # DROP VIEW IF EXISTS
        cascade: bool = False,
        restrict: bool = False,
    ):  # DROP VIEW ... CASCADE | RESTRICT (dependent-object handling)
        super().__init__(dialect)
        self.require_exclusive_options(cascade, restrict, "cascade", "restrict")
        self.view = view
        self.if_exists = if_exists
        self.cascade = cascade
        self.restrict = restrict

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_drop_view_statement"


class CreateMaterializedViewStatement(BaseExpression):
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
        create_mv = CreateMaterializedViewStatement(
            dialect,
            view=MaterializedView(dialect, "user_order_summary"),
            query=QueryStatement(
                dialect,
                select=[
                    Column(dialect, "user_id"),
                    FunctionCall(dialect, "COUNT", Column(dialect, "order_id"))
                ],
                from_=NamedRelationRef(dialect, Table(dialect, "orders")),
                group_by_having=GroupByHavingClause(
                    dialect,
                    group_by=[Column(dialect, "user_id")]
                )
            )
        )

        # Materialized view with storage options
        create_mv = CreateMaterializedViewStatement(
            dialect,
            view=MaterializedView(dialect, "sales_summary"),
            query=sales_query,
            tablespace="slow_storage",
            with_data=True  # Populate immediately
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        view: "MaterializedView",
        query: "QueryStatement",
        column_aliases: Optional[List[str]] = None,
        tablespace: Optional[str] = None,
        with_data: bool = False,  # Whether to populate immediately
        no_data: bool = False,  # Whether to leave the view unpopulated
        storage_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.require_exclusive_options(with_data, no_data, "with_data", "no_data")
        self.view = view
        self.query = query
        self.column_aliases = column_aliases or []
        self.tablespace = tablespace
        self.with_data = with_data
        self.no_data = no_data
        self.storage_options = storage_options or {}

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_create_materialized_view_statement"


class DropMaterializedViewStatement(BaseExpression):
    """
    Represents a DROP MATERIALIZED VIEW statement.

    Examples:
        # Basic drop
        drop_mv = DropMaterializedViewStatement(
            dialect,
            view=MaterializedView(dialect, "old_summary")
        )

        # Drop with IF EXISTS
        drop_mv = DropMaterializedViewStatement(
            dialect,
            view=MaterializedView(dialect, "possibly_missing"),
            if_exists=True
        )

        # Cascade drop
        drop_mv = DropMaterializedViewStatement(
            dialect,
            view=MaterializedView(dialect, "parent_view"),
            cascade=True
        )

        # Restrict drop
        drop_mv = DropMaterializedViewStatement(
            dialect,
            view=MaterializedView(dialect, "parent_view"),
            restrict=True
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        view: "MaterializedView",
        if_exists: bool = False,
        cascade: bool = False,
        restrict: bool = False,
    ):
        super().__init__(dialect)
        self.require_exclusive_options(cascade, restrict, "cascade", "restrict")
        self.view = view
        self.if_exists = if_exists
        self.cascade = cascade
        self.restrict = restrict

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_drop_materialized_view_statement"


class RefreshMaterializedViewStatement(BaseExpression):
    """
    Represents a REFRESH MATERIALIZED VIEW statement.

    This statement updates the contents of a materialized view by re-executing
    its defining query. Different databases offer different refresh strategies.

    Examples:
        # Basic refresh
        refresh_mv = RefreshMaterializedViewStatement(
            dialect,
            view=MaterializedView(dialect, "sales_summary")
        )

        # Refresh with concurrent option (PostgreSQL)
        refresh_mv = RefreshMaterializedViewStatement(
            dialect,
            view=MaterializedView(dialect, "user_stats"),
            concurrent=True
        )

        # Refresh without data (PostgreSQL)
        refresh_mv = RefreshMaterializedViewStatement(
            dialect,
            view=MaterializedView(dialect, "empty_view"),
            no_data=True
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        view: "MaterializedView",
        concurrent: bool = False,  # Refresh concurrently (PostgreSQL)
        with_data: bool = False,  # WITH DATA
        no_data: bool = False,  # WITH NO DATA
    ):
        super().__init__(dialect)
        self.require_exclusive_options(with_data, no_data, "with_data", "no_data")
        self.view = view
        self.concurrent = concurrent
        self.with_data = with_data
        self.no_data = no_data

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_refresh_materialized_view_statement"
