# src/rhosocial/activerecord/backend/schema.py
"""
Defines types related to database schema, such as column and data types.

This file is intended for data structures used in DDL (Data Definition Language)
operations and schema management.
"""
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, Union, Callable, Optional


@dataclass
class TypeMapping:
    """
    Defines type mapping rules between a generic DatabaseType and a specific
    database implementation's SQL type.

    This class is primarily used for **DDL (Data Definition Language) generation**,
     such as defining column types in `CREATE TABLE` statements. It allows
     the ORM to translate abstract model types into the precise, database-specific
     syntax required for schema creation without needing runtime database introspection.

    It is distinct from the runtime type adaptation system (`SQLTypeAdapter`),
    which handles conversion of Python values to/from SQL values for DML operations.
    """
    db_type: str
    format_func: Optional[Callable[[str, Dict[str, Any]], str]] = None

ColumnTypes = Dict[str, Union["DatabaseType", str, Any]]


class DatabaseType(Enum):
    """
    Unified database type definitions across various database systems.

    This enum provides a standard set of database column types that can be
    mapped to specific implementations in each database backend.
    """

    # --- Standard numeric types ---
    TINYINT = auto()  # Small integer (usually 1 byte)
    SMALLINT = auto()  # Small integer (usually 2 bytes)
    INTEGER = auto()  # Standard integer (usually 4 bytes)
    BIGINT = auto()  # Large integer (usually 8 bytes)
    FLOAT = auto()  # Single-precision floating point
    DOUBLE = auto()  # Double-precision floating point
    DECIMAL = auto()  # Fixed-precision decimal number
    NUMERIC = auto()  # Generic numeric type
    REAL = auto()  # Real number type

    # --- Standard string types ---
    CHAR = auto()  # Fixed-length character string
    VARCHAR = auto()  # Variable-length character string with limit
    TEXT = auto()  # Variable-length character string without limit
    TINYTEXT = auto()  # Very small text (max 255 chars)
    MEDIUMTEXT = auto()  # Medium-sized text
    LONGTEXT = auto()  # Large text

    # --- Standard date and time types ---
    DATE = auto()  # Date only (year, month, day)
    TIME = auto()  # Time only (hour, minute, second)
    DATETIME = auto()  # Date and time without timezone
    TIMESTAMP = auto()  # Date and time with timezone
    INTERVAL = auto()  # Time interval

    # --- Standard binary types ---
    BLOB = auto()  # Binary large object
    TINYBLOB = auto()  # Small binary object
    MEDIUMBLOB = auto()  # Medium binary object
    LONGBLOB = auto()  # Large binary object
    BYTEA = auto()  # Binary data

    # --- Standard boolean type ---
    BOOLEAN = auto()  # Boolean (true/false)

    # --- Common extended types ---
    UUID = auto()  # Universally unique identifier

    # --- JSON types ---
    JSON = auto()  # JSON document
    JSONB = auto()  # Binary JSON

    # --- Array types ---
    ARRAY = auto()  # Array of values

    # --- XML type ---
    XML = auto()  # XML document

    # --- Key-value type ---
    HSTORE = auto()  # Key-value store

    # --- Network address types ---
    INET = auto()  # IPv4 or IPv6 host address
    CIDR = auto()  # IPv4 or IPv6 network address
    MACADDR = auto()  # MAC address
    MACADDR8 = auto()  # MAC address (EUI-64 format)

    # --- Geometric types ---
    POINT = auto()  # Point on a plane (x,y)
    LINE = auto()  # Infinite line
    LSEG = auto()  # Line segment
    BOX = auto()  # Rectangular box
    PATH = auto()  # Closed and open paths
    POLYGON = auto()  # Polygon (similar to closed path)
    CIRCLE = auto()  # Circle
    GEOMETRY = auto()  # Generic geometry type
    GEOGRAPHY = auto()  # Geographic data type

    # --- Range types ---
    INT4RANGE = auto()  # Range of integers
    INT8RANGE = auto()  # Range of bigints
    NUMRANGE = auto()  # Range of numerics
    TSRANGE = auto()  # Range of timestamps without time zone
    TSTZRANGE = auto()  # Range of timestamps with time zone
    DATERANGE = auto()  # Range of dates

    # --- Full text search types ---
    TSVECTOR = auto()  # Text search document
    TSQUERY = auto()  # Text search query

    # --- Money type ---
    MONEY = auto()  # Currency amount

    # --- Bit string types ---
    BIT = auto()  # Fixed-length bit string
    VARBIT = auto()  # Variable-length bit string

    # --- Enumeration and set types ---
    ENUM = auto()  # Enumeration of string values
    SET = auto()  # Set of string values

    # --- Large object types ---
    CLOB = auto()  # Character large object
    NCLOB = auto()  # National character large object

    # --- Unicode types ---
    NCHAR = auto()  # Unicode fixed-length character data
    NVARCHAR = auto()  # Unicode variable-length character data
    NTEXT = auto()  # Unicode variable-length character data

    # --- Row identifier types ---
    ROWID = auto()  # Physical row address
    UROWID = auto()  # Universal row id

    # --- Hierarchical type ---
    HIERARCHYID = auto()  # Tree hierarchy position

    # --- Extensible custom type ---
    CUSTOM = auto()  # For database-specific types not covered above


class StatementType(Enum):
    """Explicitly defines the type of SQL statement."""
    # General categories
    DQL = auto()  # Data Query Language
    DML = auto()  # Data Manipulation Language
    DDL = auto()  # Data Definition Language
    TCL = auto()  # Transaction Control Language
    OTHER = auto() # Other or unknown types

    # Specific DQL/DML statements
    SELECT = auto()
    INSERT = auto()
    UPDATE = auto()
    DELETE = auto()
    TRUNCATE = auto()
    MERGE = auto()

    # Procedure/Function related
    CALL = auto()
    EXECUTE = auto()

    # Explain statement type
    EXPLAIN = auto()
