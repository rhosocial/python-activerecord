# src/rhosocial/activerecord/backend/introspection/types.py
"""
Database introspection data structures.

This module defines dataclasses for representing database metadata
in a database-agnostic way, enabling unified introspection across
different database backends.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum


class IntrospectionScope(Enum):
    """Introspection scope enumeration."""

    DATABASE = "database"
    SCHEMA = "schema"
    TABLE = "table"
    COLUMN = "column"
    INDEX = "index"
    FOREIGN_KEY = "foreign_key"
    VIEW = "view"
    TRIGGER = "trigger"
    SEQUENCE = "sequence"


class TableType(Enum):
    """Table type enumeration."""

    BASE_TABLE = "BASE_TABLE"
    VIEW = "VIEW"
    SYSTEM_TABLE = "SYSTEM_TABLE"
    TEMPORARY = "TEMPORARY"
    EXTERNAL = "EXTERNAL"


class ColumnNullable(Enum):
    """Column nullability."""

    NULLABLE = "NULLABLE"
    NOT_NULL = "NOT_NULL"
    UNKNOWN = "UNKNOWN"


class IndexType(Enum):
    """Index type enumeration."""

    BTREE = "BTREE"
    HASH = "HASH"
    GIN = "GIN"
    GIST = "GIST"
    FULLTEXT = "FULLTEXT"
    SPATIAL = "SPATIAL"
    UNKNOWN = "UNKNOWN"


class ReferentialAction(Enum):
    """Foreign key referential action."""

    CASCADE = "CASCADE"
    RESTRICT = "RESTRICT"
    SET_NULL = "SET NULL"
    SET_DEFAULT = "SET DEFAULT"
    NO_ACTION = "NO ACTION"


@dataclass
class DatabaseInfo:
    """Database information."""

    name: str
    version: str
    version_tuple: Tuple[int, int, int]
    vendor: str
    encoding: Optional[str] = None
    collation: Optional[str] = None
    timezone: Optional[str] = None
    size_bytes: Optional[int] = None
    table_count: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IndexColumnInfo:
    """Index column information."""

    name: str
    ordinal_position: int = 0
    is_descending: bool = False
    is_nulls_first: Optional[bool] = None


@dataclass
class ColumnInfo:
    """Column information."""

    name: str
    table_name: str
    schema: Optional[str] = None
    ordinal_position: int = 0
    data_type: str = ""
    data_type_full: Optional[str] = None
    nullable: ColumnNullable = ColumnNullable.UNKNOWN
    default_value: Optional[str] = None
    is_primary_key: bool = False
    is_unique: bool = False
    is_auto_increment: bool = False
    is_generated: bool = False
    generated_expression: Optional[str] = None
    comment: Optional[str] = None
    character_maximum_length: Optional[int] = None
    numeric_precision: Optional[int] = None
    numeric_scale: Optional[int] = None
    datetime_precision: Optional[int] = None
    charset: Optional[str] = None
    collation: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IndexInfo:
    """Index information."""

    name: str
    table_name: str
    schema: Optional[str] = None
    is_unique: bool = False
    is_primary: bool = False
    index_type: IndexType = IndexType.UNKNOWN
    columns: List[IndexColumnInfo] = field(default_factory=list)
    filter_condition: Optional[str] = None
    comment: Optional[str] = None
    size_bytes: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ForeignKeyInfo:
    """Foreign key information."""

    name: str
    table_name: str
    schema: Optional[str] = None
    columns: List[str] = field(default_factory=list)
    referenced_table: str = ""
    referenced_schema: Optional[str] = None
    referenced_columns: List[str] = field(default_factory=list)
    on_update: ReferentialAction = ReferentialAction.NO_ACTION
    on_delete: ReferentialAction = ReferentialAction.NO_ACTION
    deferrable: Optional[bool] = None
    deferred: Optional[bool] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ViewInfo:
    """View information."""

    name: str
    schema: Optional[str] = None
    definition: Optional[str] = None
    is_updatable: Optional[bool] = None
    is_insertable: Optional[bool] = None
    check_option: Optional[str] = None
    comment: Optional[str] = None
    columns: List[ColumnInfo] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TriggerInfo:
    """Trigger information."""

    name: str
    table_name: str
    schema: Optional[str] = None
    timing: str = ""
    events: List[str] = field(default_factory=list)
    level: str = "ROW"
    condition: Optional[str] = None
    definition: Optional[str] = None
    status: str = "ENABLED"
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TableInfo:
    """Table information."""

    name: str
    schema: Optional[str] = None
    table_type: TableType = TableType.BASE_TABLE
    comment: Optional[str] = None
    row_count: Optional[int] = None
    size_bytes: Optional[int] = None
    auto_increment: Optional[int] = None
    create_time: Optional[str] = None
    update_time: Optional[str] = None
    columns: List[ColumnInfo] = field(default_factory=list)
    indexes: List[IndexInfo] = field(default_factory=list)
    foreign_keys: List[ForeignKeyInfo] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)
