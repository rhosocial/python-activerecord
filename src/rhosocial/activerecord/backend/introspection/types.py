# src/rhosocial/activerecord/backend/introspection/types.py
"""
Database introspection type definitions.

This module provides data structures and enumerations for database introspection.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any


class IntrospectionScope(Enum):
    """Scope of introspection operations."""
    DATABASE = "database"
    SCHEMA = "schema"
    TABLE = "table"
    COLUMN = "column"
    INDEX = "index"
    FOREIGN_KEY = "foreign_key"
    VIEW = "view"
    TRIGGER = "trigger"


class TableType(Enum):
    """Type of database table."""
    BASE_TABLE = "BASE TABLE"
    VIEW = "VIEW"
    SYSTEM_VIEW = "SYSTEM VIEW"
    TEMPORARY = "TEMPORARY"


class ColumnNullable(Enum):
    """Column nullability."""
    YES = "YES"
    NO = "NO"


class IndexType(Enum):
    """Type of database index."""
    BTREE = "BTREE"
    HASH = "HASH"
    RTREE = "RTREE"
    FULLTEXT = "FULLTEXT"


class ReferentialAction(Enum):
    """Foreign key referential actions."""
    CASCADE = "CASCADE"
    RESTRICT = "RESTRICT"
    SET_NULL = "SET NULL"
    NO_ACTION = "NO ACTION"


@dataclass
class DatabaseInfo:
    """Database metadata information."""
    name: str
    charset: Optional[str] = None
    collation: Optional[str] = None
    version: Optional[str] = None
    size: Optional[int] = None
    table_count: Optional[int] = None


@dataclass
class TableInfo:
    """Table metadata information."""
    name: str
    schema: Optional[str] = None
    table_type: TableType = TableType.BASE_TABLE
    engine: Optional[str] = None
    row_count: Optional[int] = None
    data_size: Optional[int] = None
    index_size: Optional[int] = None
    create_time: Optional[str] = None
    update_time: Optional[str] = None
    comment: Optional[str] = None


@dataclass
class ColumnInfo:
    """Column metadata information."""
    name: str
    table_name: str
    position: int
    data_type: str
    nullable: ColumnNullable = ColumnNullable.YES
    default_value: Optional[str] = None
    is_primary: bool = False
    is_unique: bool = False
    auto_increment: bool = False
    comment: Optional[str] = None
    charset: Optional[str] = None
    collation: Optional[str] = None


@dataclass
class IndexColumnInfo:
    """Index column information."""
    name: str
    position: int
    is_ascending: bool = True
    sub_part: Optional[int] = None


@dataclass
class IndexInfo:
    """Index metadata information."""
    name: str
    table_name: str
    is_unique: bool = False
    is_primary: bool = False
    index_type: IndexType = IndexType.BTREE
    columns: List[IndexColumnInfo] = field(default_factory=list)
    comment: Optional[str] = None


@dataclass
class ForeignKeyInfo:
    """Foreign key metadata information."""
    name: str
    table_name: str
    columns: List[str] = field(default_factory=list)
    referenced_table: str
    referenced_columns: List[str] = field(default_factory=list)
    on_update: ReferentialAction = ReferentialAction.NO_ACTION
    on_delete: ReferentialAction = ReferentialAction.NO_ACTION


@dataclass
class ViewInfo:
    """View metadata information."""
    name: str
    schema: Optional[str] = None
    definition: Optional[str] = None
    check_option: Optional[str] = None
    is_updatable: Optional[bool] = None


@dataclass
class TriggerInfo:
    """Trigger metadata information."""
    name: str
    table_name: str
    event: str  # INSERT, UPDATE, DELETE
    timing: str  # BEFORE, AFTER
    statement: Optional[str] = None
    created: Optional[str] = None
