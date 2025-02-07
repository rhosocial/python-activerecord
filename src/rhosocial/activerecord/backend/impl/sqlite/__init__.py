"""
SQLite backend implementation for the Python ORM.

This module provides a SQLite-specific implementation including:
- SQLite backend with connection management and query execution
- Type mapping and value conversion
- Transaction management with savepoint support
- SQLite dialect and expression handling
- SQLite-specific type definitions and mappings
"""

from .backend import SQLiteBackend
from .dialect import (
    SQLiteDialect,
    SQLiteExpression,
    SQLiteTypeMapper,
    SQLiteValueMapper,
)
from .transaction import SQLiteTransactionManager
from .types import (
    SQLiteTypes,
    SQLiteColumnType,
    SQLITE_TYPE_MAPPINGS,
)

__all__ = [
    # Backend
    'SQLiteBackend',

    # Dialect related
    'SQLiteDialect',
    'SQLiteExpression',
    'SQLiteTypeMapper',
    'SQLiteValueMapper',

    # Transaction
    'SQLiteTransactionManager',

    # Types
    'SQLiteTypes',
    'SQLiteColumnType',
    'SQLITE_TYPE_MAPPINGS',
]