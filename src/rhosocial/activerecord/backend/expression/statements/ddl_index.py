# src/rhosocial/activerecord/backend/expression/statements/ddl_index.py
"""Index DDL statement expressions."""

from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING

from ..bases import BaseExpression, SQLPredicate, SQLQueryAndParams

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


class CreateIndexExpression(BaseExpression):
    """
    Represents a CREATE INDEX statement for standalone index creation.

    Note: This is for creating indexes on existing tables. For inline
    index definitions during table creation, use CreateTableExpression
    with the indexes parameter.

    Examples:
        # Basic index
        create_idx = CreateIndexExpression(
            dialect,
            index_name="idx_users_email",
            table_name="users",
            columns=["email"]
        )

        # Unique index
        create_idx = CreateIndexExpression(
            dialect,
            index_name="idx_users_username",
            table_name="users",
            columns=["username"],
            unique=True
        )

        # Composite index
        create_idx = CreateIndexExpression(
            dialect,
            index_name="idx_orders_user_date",
            table_name="orders",
            columns=["user_id", "created_at"]
        )

        # Partial index (PostgreSQL)
        create_idx = CreateIndexExpression(
            dialect,
            index_name="idx_active_users",
            table_name="users",
            columns=["email"],
            where=Column(dialect, "status") == Literal(dialect, "active")
        )

        # Index with specific type
        create_idx = CreateIndexExpression(
            dialect,
            index_name="idx_users_name_hash",
            table_name="users",
            columns=["name"],
            index_type="HASH"
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        index_name: str,
        table_name: str,
        columns: List[Union[str, "BaseExpression"]],
        unique: bool = False,
        if_not_exists: bool = False,
        index_type: Optional[str] = None,
        where: Optional["SQLPredicate"] = None,
        include: Optional[List[str]] = None,
        tablespace: Optional[str] = None,
        concurrent: bool = False,
        *,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.index_name = index_name
        self.table_name = table_name
        self.columns = columns
        self.unique = unique
        self.if_not_exists = if_not_exists
        self.index_type = index_type
        self.where = where
        self.include = include
        self.tablespace = tablespace
        self.concurrent = concurrent
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_create_index_statement(self)


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
            table_name="orders"
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        index_name: str,
        table_name: Optional[str] = None,
        if_exists: bool = False,
        *,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.index_name = index_name
        self.table_name = table_name
        self.if_exists = if_exists
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_drop_index_statement(self)


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
            table_name="articles",
            columns=["title", "content"]
        )

        # FULLTEXT index with parser (MySQL)
        create_ft = CreateFulltextIndexExpression(
            dialect,
            index_name="idx_documents_body",
            table_name="documents",
            columns=["body"],
            parser="ngram"
        )

        # FULLTEXT index with IF NOT EXISTS
        create_ft = CreateFulltextIndexExpression(
            dialect,
            index_name="idx_posts_content",
            table_name="posts",
            columns=["content"],
            if_not_exists=True
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        index_name: str,
        table_name: str,
        columns: List[str],
        parser: Optional[str] = None,
        if_not_exists: bool = False,
        *,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.index_name = index_name
        self.table_name = table_name
        self.columns = columns
        self.parser = parser
        self.if_not_exists = if_not_exists
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_create_fulltext_index_statement(self)


class DropFulltextIndexExpression(BaseExpression):
    """
    Represents a DROP FULLTEXT INDEX statement.

    Examples:
        # Basic drop
        drop_ft = DropFulltextIndexExpression(
            dialect,
            index_name="idx_articles_content",
            table_name="articles"
        )

        # Drop with IF EXISTS
        drop_ft = DropFulltextIndexExpression(
            dialect,
            index_name="idx_old_fulltext",
            table_name="old_table",
            if_exists=True
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        index_name: str,
        table_name: str,
        if_exists: bool = False,
        *,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.index_name = index_name
        self.table_name = table_name
        self.if_exists = if_exists
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_drop_fulltext_index_statement(self)
