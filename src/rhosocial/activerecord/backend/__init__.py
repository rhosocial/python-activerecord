"""
Database backend abstraction layer for Python ORMs.

This module provides a generic interface for database operations, with support for:
- Multiple database backends (SQLite, MySQL, PostgreSQL, etc.)
- Type mapping and conversion
- Transaction management
- SQL dialect handling
- Connection pooling
"""

__version__ = "0.6.0"

# Core interfaces and base classes
from .base import StorageBackend
from .dialect import (
    TypeMapping,
    SQLDialectBase,
    SQLExpressionBase, ReturningOptions,
)

# Type definitions and configuration
from .typing import (
    ConnectionConfig,
    QueryResult,
    DatabaseValue,
    PythonValue,
    DatabaseType,
)

# Error types
from .errors import (
    DatabaseError,
    ConnectionError,
    TransactionError,
    QueryError,
    ValidationError,
    LockError,
    DeadlockError,
    IntegrityError,
    TypeConversionError,
    OperationalError,
    RecordNotFound,
)

# Helper functions
from .helpers import (
    convert_datetime,
    parse_datetime,
    safe_json_dumps,
    safe_json_loads,
    array_converter,
    measure_time,
)

# Transaction
from .transaction import (
    TransactionManager,
    IsolationLevel,
)

__all__ = [
    # Base classes
    'StorageBackend',
    # Dialect related
    'TypeMapping',

    # Types and configs
    'ConnectionConfig',
    'QueryResult',
    'DatabaseValue',
    'PythonValue',
    'DatabaseType',

    # Errors
    'DatabaseError',
    'ConnectionError',
    'TransactionError',
    'QueryError',
    'ValidationError',
    'LockError',
    'DeadlockError',
    'IntegrityError',
    'TypeConversionError',
    'OperationalError',
    'RecordNotFound',

    # Helper functions
    'convert_datetime',
    'parse_datetime',
    'safe_json_dumps',
    'safe_json_loads',
    'array_converter',
    'measure_time',

    # Expression
    'SQLDialectBase',
    'SQLExpressionBase',

    # Transaction
    'TransactionManager',
    'IsolationLevel',
]
