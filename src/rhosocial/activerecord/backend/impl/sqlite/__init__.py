# src/rhosocial/activerecord/backend/impl/sqlite/__init__.py
"""
SQLite backend implementation for ActiveRecord.

This module provides a complete SQLite backend implementation for the ActiveRecord ORM,
including connection management, dialect support, type adapters, and query execution.
"""

from .backend import SQLiteBackend
from .config import SQLiteConnectionConfig
from .dialect import SQLiteDialect
from .adapters import (
    SQLiteBlobAdapter,
    SQLiteJSONAdapter,
    SQLiteUUIDAdapter
)

__all__ = [
    'SQLiteBackend',
    'SQLiteConnectionConfig', 
    'SQLiteDialect',
    'SQLiteBlobAdapter',
    'SQLiteJSONAdapter',
    'SQLiteUUIDAdapter',
]