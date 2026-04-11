# src/rhosocial/activerecord/backend/expression/statements/ddl_table.py
"""Table DDL statement expressions and related types."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union, TYPE_CHECKING

from ..bases import BaseExpression, SQLPredicate, SQLQueryAndParams
from ..core import TableExpression

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase
    from .dql import QueryExpression


class ColumnConstraintType(Enum):
    """Types of column constraints."""

    PRIMARY_KEY = "PRIMARY KEY"
    NOT_NULL = "NOT NULL"
    NULL = "NULL"  # Explicitly allow NULL (usually redundant but sometimes needed for clarity)
    UNIQUE = "UNIQUE"
    CHECK = "CHECK"
    FOREIGN_KEY = "FOREIGN KEY"
    DEFAULT = "DEFAULT"


@dataclass
class ColumnConstraint:
    """Represents a column constraint (PRIMARY KEY, NOT NULL, UNIQUE, etc.)"""

    constraint_type: ColumnConstraintType
    name: Optional[str] = None  # Optional constraint name
    check_condition: Optional["SQLPredicate"] = None  # For CHECK constraints
    foreign_key_reference: Optional[Tuple[str, List[str]]] = None  # (referenced_table, referenced_columns)
    default_value: Any = None  # For DEFAULT constraints
    is_auto_increment: bool = False  # For AUTO_INCREMENT/IDENTITY columns
    # FK referential actions for column-level foreign key constraints
    on_delete: Optional["ReferentialAction"] = None  # ON DELETE action
    on_update: Optional["ReferentialAction"] = None  # ON UPDATE action
    # SQL standard constraint deferral (PostgreSQL)
    deferrable: Optional[bool] = None  # DEFERRABLE / NOT DEFERRABLE (None = omit)
    initially_deferred: Optional[bool] = None  # INITIALLY DEFERRED / INITIALLY IMMEDIATE (None = omit)
    dialect_options: Optional[Dict[str, Any]] = None  # Database-specific options


class GeneratedColumnType(Enum):
    """Types of generated columns (computed columns)."""

    STORED = "STORED"  # Stored on disk, can be indexed
    VIRTUAL = "VIRTUAL"  # Computed on read, not stored


@dataclass
class ColumnDefinition:
    """Represents a column's definition within a CREATE/ALTER TABLE statement."""

    name: str
    data_type: str  # e.g. "VARCHAR(255)", "INTEGER", "DECIMAL(10,2)", "CHARACTER VARYING(255)"
    constraints: List[ColumnConstraint] = field(default_factory=list)  # Column constraints
    comment: Optional[str] = None  # Column comment
    dialect_options: Optional[Dict[str, Any]] = None  # Database-specific options
    # Generated column support (SQLite 3.31.0+, PostgreSQL, MySQL)
    generated_expression: Optional["BaseExpression"] = None  # Expression for generated column
    generated_type: Optional[GeneratedColumnType] = None  # STORED or VIRTUAL


class TableConstraintType(Enum):
    """Types of table constraints supported by SQL."""

    PRIMARY_KEY = "PRIMARY KEY"
    UNIQUE = "UNIQUE"
    FOREIGN_KEY = "FOREIGN KEY"
    CHECK = "CHECK"
    EXCLUDE = "EXCLUDE"


class ReferentialAction(Enum):
    """Actions for referential integrity constraints."""

    CASCADE = "CASCADE"
    RESTRICT = "RESTRICT"
    SET_NULL = "SET NULL"
    SET_DEFAULT = "SET DEFAULT"
    NO_ACTION = "NO ACTION"


class ConstraintValidation(Enum):
    """Constraint validation status (PostgreSQL specific).

    Used in AddTableConstraint.dialect_options['validation'] to control
    whether PostgreSQL validates existing data against the constraint.

    - VALIDATE: Validate all existing data (default behavior)
    - NOVALIDATE: Add constraint without validating existing data (NOT VALID)
    """

    VALIDATE = "VALIDATE"
    NOVALIDATE = "NOT VALID"


@dataclass
class TableConstraint:
    """Represents a table-level constraint."""

    constraint_type: TableConstraintType
    name: Optional[str] = None  # Optional constraint name
    columns: Optional[List[str]] = None  # For PK, UK constraints
    check_condition: Optional["SQLPredicate"] = None  # For CHECK constraints
    foreign_key_table: Optional[str] = None  # For FK constraints
    foreign_key_columns: Optional[List[str]] = None  # For FK constraints
    # SQL standard constraint deferral (PostgreSQL)
    deferrable: Optional[bool] = None  # DEFERRABLE / NOT DEFERRABLE (None = omit)
    initially_deferred: Optional[bool] = None  # INITIALLY DEFERRED / INITIALLY IMMEDIATE (None = omit)
    dialect_options: Optional[Dict[str, Any]] = None  # Database-specific options


@dataclass
class ForeignKeyConstraint(TableConstraint):
    """Specialized table constraint for foreign keys with additional options."""

    constraint_type: TableConstraintType = TableConstraintType.FOREIGN_KEY
    on_delete: ReferentialAction = ReferentialAction.NO_ACTION
    on_update: ReferentialAction = ReferentialAction.NO_ACTION
    match_type: Optional[str] = None  # "SIMPLE", "PARTIAL", "FULL" for foreign key matching


@dataclass
class IndexDefinition:
    """Represents an index definition for a table."""

    name: str
    columns: List[str]  # List of column names to index
    unique: bool = False  # Whether the index enforces uniqueness
    type: Optional[str] = None  # Index type: BTREE, HASH, GIN, etc.
    partial_condition: Optional["SQLPredicate"] = None  # For partial indexes (PostgreSQL)
    include_columns: Optional[List[str]] = None  # Included columns (non-key columns in index, SQL Server/PostgreSQL)
    dialect_options: Optional[Dict[str, Any]] = None  # Database-specific options


class CreateTableExpression(BaseExpression):
    """Represents a comprehensive CREATE TABLE statement supporting full SQL standard features."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table_name: Union[str, "TableExpression"],
        columns: List[ColumnDefinition],  # List of column definitions with constraints
        indexes: Optional[List[IndexDefinition]] = None,  # Table indexes
        table_constraints: Optional[List[TableConstraint]] = None,  # Table-level constraints
        temporary: bool = False,  # TEMPORARY table flag
        if_not_exists: bool = False,  # IF NOT EXISTS flag
        inherits: Optional[List[str]] = None,  # PostgreSQL INHERITS clause
        tablespace: Optional[str] = None,  # Table tablespace (PostgreSQL/Oracle)
        storage_options: Optional[
            Dict[str, Any]
        ] = None,  # Storage parameters (PostgreSQL WITH options, MySQL ENGINE options)
        partition_by: Optional[
            Tuple[str, List[str]]
        ] = None,  # Partitioning specification (partition_type, partition_columns)
        as_query: Optional["QueryExpression"] = None,  # Create table AS query result
        *,  # Force keyword arguments
        dialect_options: Optional[Dict[str, Any]] = None,
    ):  # Dialect-specific options
        super().__init__(dialect)
        # Validate and normalize table_name
        if isinstance(table_name, str):
            self.table = TableExpression(dialect, table_name)
        elif isinstance(table_name, TableExpression):
            self.table = table_name
        else:
            raise TypeError(f"table_name must be str or TableExpression, got {type(table_name).__name__}")
        self.columns = columns  # List of column definitions with embedded constraints
        self.indexes = indexes or []  # List of indexes to create
        self.table_constraints = table_constraints or []  # List of table-level constraints
        self.temporary = temporary  # Temporary table flag
        self.if_not_exists = if_not_exists  # IF NOT EXISTS flag
        self.inherits = inherits or []  # Tables to inherit from (PostgreSQL-specific)
        self.tablespace = tablespace  # Tablespace specification
        self.storage_options = storage_options or {}  # Storage-related options
        self.partition_by = partition_by  # Partitioning specification
        self.as_query = as_query  # Query to base table on (for CREATE TABLE AS)
        self.dialect_options = dialect_options or {}  # Dialect-specific options

    @property
    def table_name(self) -> str:
        """Get the table name (for backward compatibility)."""
        return self.table.name

    def to_sql(self) -> "SQLQueryAndParams":
        """Delegates SQL generation for the CREATE TABLE statement to the configured dialect."""
        return self.dialect.format_create_table_statement(self)


class DropTableExpression(BaseExpression):
    """Represents a DROP TABLE statement conforming to SQL standard.

    SQL Standard Syntax:
        DROP TABLE [IF EXISTS] <table_name> [CASCADE | RESTRICT]

    The CASCADE/RESTRICT options control dependent object handling:
    - CASCADE: Automatically drops dependent objects (views, foreign keys)
    - RESTRICT: Refuses to drop if dependencies exist (default in SQL standard)

    Database-specific behavior:
    - PostgreSQL: Full CASCADE/RESTRICT support
    - MySQL: Keywords accepted but ignored (for portability)
    - SQLite: CASCADE/RESTRICT not supported (ignored)
    - Oracle: Uses CASCADE CONSTRAINTS instead of CASCADE
    - SQL Server: No CASCADE/RESTRICT (must drop FK constraints manually)

    Args:
        dialect: The SQL dialect to use for formatting
        table_name: The table name (string) or TableExpression object
        if_exists: Add IF EXISTS clause to avoid error if table doesn't exist
        cascade: Optional cascade behavior:
            - None: Omit from SQL (use database default)
            - True: Generate CASCADE (or equivalent for dialect)
            - False: Generate RESTRICT (or equivalent for dialect)
        dialect_options: Database-specific options (e.g., MySQL TEMPORARY, Oracle PURGE)

    Examples:
        # Simple drop
        DropTableExpression(dialect, "users")
        # -> DROP TABLE users

        # With IF EXISTS
        DropTableExpression(dialect, "users", if_exists=True)
        # -> DROP TABLE IF EXISTS users

        # With CASCADE
        DropTableExpression(dialect, "users", cascade=True)
        # -> DROP TABLE users CASCADE

        # With schema-qualified table
        DropTableExpression(dialect, TableExpression(dialect, "users", schema_name="public"))
        # -> DROP TABLE public.users
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table_name: Union[str, "TableExpression"],
        if_exists: bool = False,
        cascade: Optional[bool] = None,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        # Validate and normalize table_name
        if isinstance(table_name, str):
            self.table = TableExpression(dialect, table_name)
        elif isinstance(table_name, TableExpression):
            self.table = table_name
        else:
            raise TypeError(f"table_name must be str or TableExpression, got {type(table_name).__name__}")
        self.if_exists = if_exists
        self.cascade = cascade
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> "SQLQueryAndParams":
        """Delegates SQL generation for the DROP TABLE statement to the configured dialect."""
        return self.dialect.format_drop_table_statement(self)
