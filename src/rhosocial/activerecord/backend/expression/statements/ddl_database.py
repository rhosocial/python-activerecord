# src/rhosocial/activerecord/backend/expression/statements/ddl_database.py
"""DATABASE DDL statement expressions."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, TYPE_CHECKING

from ..bases import BaseExpression

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


class AlterDatabaseAction(Enum):
    """Actions for ALTER DATABASE statements."""

    RENAME_TO = "RENAME TO"
    OWNER_TO = "OWNER TO"
    SET_PROPERTY = "SET"
    UNSET_PROPERTY = "UNSET"
    CHARACTER_SET = "CHARACTER SET"
    COLLATION = "COLLATION"
    SWAP_WITH = "SWAP WITH"
    ENABLE_REPLICATION = "ENABLE REPLICATION"
    DISABLE_REPLICATION = "DISABLE REPLICATION"
    ENABLE_FAILOVER = "ENABLE FAILOVER"
    DISABLE_FAILOVER = "DISABLE FAILOVER"


class CreateDatabaseExpression(BaseExpression):
    """Represents a CREATE DATABASE statement.

    Supports common parameters across multiple database backends.
    Backend-specific features (CLONE, TRANSIENT, ENGINE, etc.)
    should be passed via ``dialect_options``.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_create_database_statement"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        database_name: str,
        if_not_exists: bool = False,
        owner: Optional[str] = None,
        encoding: Optional[str] = None,
        collation: Optional[str] = None,
        tablespace: Optional[str] = None,
        template: Optional[str] = None,
        connection_limit: Optional[int] = None,
        comment: Optional[str] = None,
        or_replace: bool = False,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.database_name = database_name
        self.if_not_exists = if_not_exists
        self.owner = owner
        self.encoding = encoding
        self.collation = collation
        self.tablespace = tablespace
        self.template = template
        self.connection_limit = connection_limit
        self.comment = comment
        self.or_replace = or_replace
        self.dialect_options = dialect_options or {}


class DropDatabaseExpression(BaseExpression):
    """Represents a DROP DATABASE statement.

    Supports common parameters across multiple database backends.
    Backend-specific features (SYNC, PURGE, etc.)
    should be passed via ``dialect_options``.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_drop_database_statement"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        database_name: str,
        if_exists: bool = False,
        force: bool = False,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.database_name = database_name
        self.if_exists = if_exists
        self.force = force
        self.dialect_options = dialect_options or {}


class AlterDatabaseExpression(BaseExpression):
    """Represents an ALTER DATABASE statement.

    Uses an action-based pattern similar to ALTER TABLE.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_alter_database_statement"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        database_name: str,
        action: AlterDatabaseAction,
        target: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        if_exists: bool = False,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.database_name = database_name
        self.action = action
        self.target = target
        self.properties = properties or {}
        self.if_exists = if_exists
        self.dialect_options = dialect_options or {}


__all__ = [
    "AlterDatabaseAction",
    "CreateDatabaseExpression",
    "DropDatabaseExpression",
    "AlterDatabaseExpression",
]
