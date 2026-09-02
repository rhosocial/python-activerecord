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
            index="idx_users_email",
            table="users",
            columns=["email"]
        )

        # Unique index
        create_idx = CreateIndexExpression(
            dialect,
            index="idx_users_username",
            table="users",
            columns=["username"],
            unique=True
        )

        # Composite index
        create_idx = CreateIndexExpression(
            dialect,
            index="idx_orders_user_date",
            table="orders",
            columns=["user_id", "created_at"]
        )

        # Partial index (PostgreSQL)
        create_idx = CreateIndexExpression(
            dialect,
            index="idx_active_users",
            table="users",
            columns=["email"],
            where=Column(dialect, "status") == Literal(dialect, "active")
        )

        # Index with specific type
        create_idx = CreateIndexExpression(
            dialect,
            index="idx_users_name_hash",
            table="users",
            columns=["name"],
            index_type="HASH"
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        index: str,
        table: str,
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
        self.index = index
        self.table = table
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
            index="idx_users_email"
        )

        # Drop with IF EXISTS
        drop_idx = DropIndexExpression(
            dialect,
            index="idx_old_index",
            if_exists=True
        )

        # Drop with table context (some databases require this)
        drop_idx = DropIndexExpression(
            dialect,
            index="idx_orders_status",
            table="orders"
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        index: str,
        table: Optional[str] = None,
        if_exists: bool = False,
        *,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.index = index
        self.table = table
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
            index="idx_articles_content",
            table="articles",
            columns=["title", "content"]
        )

        # FULLTEXT index with parser (MySQL)
        create_ft = CreateFulltextIndexExpression(
            dialect,
            index="idx_documents_body",
            table="documents",
            columns=["body"],
            parser="ngram"
        )

        # FULLTEXT index with IF NOT EXISTS
        create_ft = CreateFulltextIndexExpression(
            dialect,
            index="idx_posts_content",
            table="posts",
            columns=["content"],
            if_not_exists=True
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        index: str,
        table: str,
        columns: List[str],
        parser: Optional[str] = None,
        if_not_exists: bool = False,
        *,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.index = index
        self.table = table
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
            index="idx_articles_content",
            table="articles"
        )

        # Drop with IF EXISTS
        drop_ft = DropFulltextIndexExpression(
            dialect,
            index="idx_old_fulltext",
            table="old_table",
            if_exists=True
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        index: str,
        table: str,
        if_exists: bool = False,
        *,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.index = index
        self.table = table
        self.if_exists = if_exists
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_drop_fulltext_index_statement(self)
