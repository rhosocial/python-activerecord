# src/rhosocial/activerecord/backend/expression/statements/ddl_index.py
"""Index DDL statement expressions."""

from typing import List, Optional, Union, TYPE_CHECKING

from ..bases import BaseExpression, SQLPredicate
from ..core import TableExpression

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


class CreateIndexExpression(BaseExpression):
    """
    Represents a CREATE INDEX statement for standalone index creation.

    Note: This is for creating indexes on existing tables. For inline
    index definitions during table creation, use CreateTableExpression
    with the indexes parameter.

    The index and the table it is built on live in namespaces that are
    chosen independently. ``schema_name`` qualifies the index;
    ``table`` qualifies the table. Passing a bare string as ``table``
    leaves the table unqualified even when ``schema_name`` is set.

    Examples:
        # Basic index
        create_idx = CreateIndexExpression(
            dialect,
            index_name="idx_users_email",
            table=TableExpression(dialect, "users"),
            columns=["email"]
        )

        # Index and table in the same namespace
        create_idx = CreateIndexExpression(
            dialect,
            index_name="idx_users_email",
            table=TableExpression(dialect, "users", schema_name="app"),
            columns=["email"],
            schema_name="app"
        )

        # Index in one namespace, table in another
        create_idx = CreateIndexExpression(
            dialect,
            index_name="idx_shared",
            table=TableExpression(dialect, "orders", schema_name="sales"),
            columns=["user_id"],
            schema_name="app"
        )

        # Unique index
        create_idx = CreateIndexExpression(
            dialect,
            index_name="idx_users_username",
            table=TableExpression(dialect, "users"),
            columns=["username"],
            unique=True
        )

        # Composite index
        create_idx = CreateIndexExpression(
            dialect,
            index_name="idx_orders_user_date",
            table=TableExpression(dialect, "orders"),
            columns=["user_id", "created_at"]
        )

        # Partial index (PostgreSQL)
        create_idx = CreateIndexExpression(
            dialect,
            index_name="idx_active_users",
            table=TableExpression(dialect, "users"),
            columns=["email"],
            where=Column(dialect, "status") == Literal(dialect, "active")
        )

        # Index with specific type
        create_idx = CreateIndexExpression(
            dialect,
            index_name="idx_users_name_hash",
            table=TableExpression(dialect, "users"),
            columns=["name"],
            index_type="HASH"
        )
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_create_index_statement"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        index_name: str,
        table: "TableExpression",
        columns: List[Union[str, "BaseExpression"]],
        unique: bool = False,
        if_not_exists: bool = False,
        index_type: Optional[str] = None,
        where: Optional["SQLPredicate"] = None,
        include: Optional[List[str]] = None,
        tablespace: Optional[str] = None,
        concurrent: bool = False,
        schema_name: Optional[str] = None,
    ):
        """
        Args:
            table: The table the index is built on, carrying its own
                namespace. A bare string is refused rather than wrapped: wrapping it builds
                    an unnamed reference, so a caller who meant to qualify the
                    index gets an unqualified table and no error.
                Independent of ``schema_name``, which qualifies the
                index itself.
            schema_name: Namespace to qualify the index with, e.g. ``app``.
                None leaves the index name unqualified. An empty string
                raises ValueError, and a dialect with no namespace raises
                UnsupportedFeatureError.
        """
        super().__init__(dialect)
        self.index_name = index_name
        self.schema_name = schema_name
        if not isinstance(table, TableExpression):
            raise TypeError(f"table must be a TableExpression, got {type(table).__name__}")
        self.table = table
        self.columns = columns
        self.unique = unique
        self.if_not_exists = if_not_exists
        self.index_type = index_type
        self.where = where
        self.include = include
        self.tablespace = tablespace
        self.concurrent = concurrent


class DropIndexExpression(BaseExpression):
    """
    Represents a DROP INDEX statement.

    Examples:
        # Basic drop
        drop_idx = DropIndexExpression(
            dialect,
            index_name="idx_users_email"
        )

        # Drop with IF EXISTS
        drop_idx = DropIndexExpression(
            dialect,
            index_name="idx_old_index",
            if_exists=True
        )

        # Drop with table context (some databases require this)
        drop_idx = DropIndexExpression(
            dialect,
            index_name="idx_orders_status",
            table=TableExpression(dialect, "orders")
        )

        # Index and table resolved independently
        drop_idx = DropIndexExpression(
            dialect,
            index_name="idx_shared",
            table=TableExpression(dialect, "orders", schema_name="sales"),
            schema_name="app"
        )
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_drop_index_statement"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        index_name: str,
        table: Optional["TableExpression"] = None,
        if_exists: bool = False,
        concurrent: bool = False,
        schema_name: Optional[str] = None,
    ):
        """
        Args:
            table: The table carrying the index, carrying its own namespace.
                None omits the ``ON`` clause. A bare string is refused rather than wrapped: wrapping it builds
                    an unnamed reference, so a caller who meant to qualify the
                    index gets an unqualified table and no error.
                Independent of ``schema_name``, which qualifies the index.
            schema_name: Namespace to qualify the index with, e.g. ``app``.
                None leaves the index name unqualified. An empty string
                raises ValueError, and a dialect with no namespace raises
                UnsupportedFeatureError.
        """
        super().__init__(dialect)
        self.index_name = index_name
        self.schema_name = schema_name
        if table is not None and not isinstance(table, TableExpression):
            raise TypeError(f"table must be a TableExpression, got {type(table).__name__}")
        self.table = table
        self.if_exists = if_exists
        self.concurrent = concurrent


class CreateFulltextIndexExpression(BaseExpression):
    """
    Represents a CREATE FULLTEXT INDEX statement.

    FULLTEXT indexes are specialized indexes for full-text search capabilities.
    Support varies by database:
    - MySQL: Full support with MATCH ... AGAINST syntax
    - PostgreSQL: Uses GIN/GIST indexes with to_tsvector
    - SQLite: Requires FTS5 extension
    - SQL Server: Uses CONTAINS and FREETEXT predicates

    Examples:
        # Basic FULLTEXT index
        create_ft = CreateFulltextIndexExpression(
            dialect,
            index_name="idx_articles_content",
            table=TableExpression(dialect, "articles"),
            columns=["title", "content"]
        )

        # FULLTEXT index with parser (MySQL)
        create_ft = CreateFulltextIndexExpression(
            dialect,
            index_name="idx_documents_body",
            table=TableExpression(dialect, "documents"),
            columns=["body"],
            parser="ngram"
        )

        # FULLTEXT index with IF NOT EXISTS
        create_ft = CreateFulltextIndexExpression(
            dialect,
            index_name="idx_posts_content",
            table=TableExpression(dialect, "posts"),
            columns=["content"],
            if_not_exists=True
        )
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_create_fulltext_index_statement"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        index_name: str,
        table: "TableExpression",
        columns: List[str],
        parser: Optional[str] = None,
        if_not_exists: bool = False,
        schema_name: Optional[str] = None,
    ):
        """
        Args:
            table: The table the fulltext index is built on, carrying its
                own namespace. A bare string is refused rather than wrapped: wrapping it builds
                    an unnamed reference, so a caller who meant to qualify the
                    index gets an unqualified table and no error. This is independent of ``schema_name``, which
                qualifies the index itself.
            schema_name: Namespace to qualify the full-text index with, e.g.
                ``app``. None leaves the name unqualified. An empty string
                raises ValueError, and a dialect with no namespace raises
                UnsupportedFeatureError.
        """
        super().__init__(dialect)
        self.index_name = index_name
        self.schema_name = schema_name
        if not isinstance(table, TableExpression):
            raise TypeError(f"table must be a TableExpression, got {type(table).__name__}")
        self.table = table
        self.columns = columns
        self.parser = parser
        self.if_not_exists = if_not_exists


class DropFulltextIndexExpression(BaseExpression):
    """
    Represents a DROP FULLTEXT INDEX statement.

    Examples:
        # Basic drop
        drop_ft = DropFulltextIndexExpression(
            dialect,
            index_name="idx_articles_content",
            table=TableExpression(dialect, "articles")
        )

        # Drop with IF EXISTS
        drop_ft = DropFulltextIndexExpression(
            dialect,
            index_name="idx_old_fulltext",
            table=TableExpression(dialect, "old_table"),
            if_exists=True
        )
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_drop_fulltext_index_statement"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        index_name: str,
        table: "TableExpression",
        if_exists: bool = False,
        schema_name: Optional[str] = None,
    ):
        """
        Args:
            table: The table carrying the index, carrying its own namespace.
                A bare string is refused rather than wrapped: wrapping it builds
                    an unnamed reference, so a caller who meant to qualify the
                    index gets an unqualified table and no error.
                Independent of ``schema_name``, which qualifies the
                index.
            schema_name: Namespace to qualify the full-text index with, e.g.
                ``app``. None leaves the name unqualified. An empty string
                raises ValueError, and a dialect with no namespace raises
                UnsupportedFeatureError.
        """
        super().__init__(dialect)
        self.index_name = index_name
        self.schema_name = schema_name
        if not isinstance(table, TableExpression):
            raise TypeError(f"table must be a TableExpression, got {type(table).__name__}")
        self.table = table
        self.if_exists = if_exists
