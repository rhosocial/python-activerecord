# src/rhosocial/activerecord/backend/expression/statements/ddl_comment.py
"""Standalone ``COMMENT ON`` DDL statement expressions.

``COMMENT ON`` is a **standalone statement** that annotates an existing schema
object; it is deliberately distinct from the inline comment *clauses* of
``CREATE TABLE`` (:class:`~.ddl_table.ColumnCommentClause` /
:class:`~.ddl_table.TableCommentClause`).  The two are not interchangeable:

* inline clauses belong to the CREATE TABLE grammar and are only available on
  dialects that support them (MySQL / MariaDB / ClickHouse / Snowflake /
  BigQuery);
* the standalone statement annotates objects after creation and is the only
  comment mechanism on PostgreSQL / Oracle / Firebird / Snowflake.
"""

from enum import Enum
from typing import Optional, TYPE_CHECKING, Union

from ..bases import BaseExpression

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


class CommentObjectType(Enum):
    """Database object kinds a standalone ``COMMENT ON`` may target.

    The enum value is the SQL keyword sequence (``TABLE`` / ``COLUMN`` /
    ``MATERIALIZED VIEW`` / …).  Backends with additional object kinds (e.g.
    Firebird's ``GENERATOR`` / ``DOMAIN``) may subclass this enum; dialect
    formatters accept either the enum or its string value.
    """

    TABLE = "TABLE"
    COLUMN = "COLUMN"
    VIEW = "VIEW"
    MATERIALIZED_VIEW = "MATERIALIZED VIEW"
    INDEX = "INDEX"
    SCHEMA = "SCHEMA"
    DATABASE = "DATABASE"
    SEQUENCE = "SEQUENCE"
    FUNCTION = "FUNCTION"
    PROCEDURE = "PROCEDURE"
    TRIGGER = "TRIGGER"
    TYPE = "TYPE"
    TABLESPACE = "TABLESPACE"


class CommentOnExpression(BaseExpression):
    """Standalone ``COMMENT ON <object> IS '<text>'`` statement.

    This is an independent DDL statement, deliberately distinct from the
    inline comment clauses of CREATE TABLE (``ColumnCommentClause`` /
    ``TableCommentClause``): it annotates an existing schema object and is the
    only comment mechanism on backends without inline comment grammar.

    ``object_name`` may be a dotted reference (``table.column`` for a column);
    ``schema`` optionally qualifies it.  ``comment=None`` renders the
    clear-comment form (``IS NULL``).
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_comment_statement"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        object_type: Union["CommentObjectType", str],
        object_name: str,
        comment: Optional[str] = None,
        schema: Optional[str] = None,
    ):
        super().__init__(dialect)
        if not isinstance(object_name, str) or not object_name.strip():
            raise ValueError("object_name must be a non-empty string")
        self.object_type = object_type
        self.object_name = object_name
        self.comment = comment
        self.schema = schema


__all__ = ["CommentObjectType", "CommentOnExpression"]
