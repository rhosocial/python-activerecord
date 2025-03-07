"""
Database backend abstraction layer for Python ORMs.

This module provides a generic interface for database operations, with support for:
- Multiple database backends (SQLite, MySQL, PostgreSQL)
- Type mapping and conversion
- Transaction management
- SQL dialect handling
- Connection pooling
"""

# Core interfaces and base classes
from .base import StorageBackend
from .dialect import (
    DatabaseType,
    TypeMapper,
    ValueMapper,
    TypeMapping,
    SQLDialectBase,
    SQLExpressionBase,
)

# Type definitions and configuration
from .typing import (
    ConnectionConfig,
    QueryResult,
    DatabaseValue,
    PythonValue,
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
    'DatabaseType',
    'TypeMapper',
    'ValueMapper',
    'TypeMapping',

    # Types and configs
    'ConnectionConfig',
    'QueryResult',
    'DatabaseValue',
    'PythonValue',

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

__version__ = '0.3.0'