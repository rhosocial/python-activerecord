# src/rhosocial/activerecord/backend/impl/sqlite/__init__.py
"""
SQLite backend implementation for rhosocial-activerecord.

This package contains the concrete implementation of the storage backend
for SQLite, including the backend class, dialect, and specific type adapters.
"""
from .adapters import (
    SQLiteBlobAdapter,
    SQLiteJSONAdapter,
    SQLiteUUIDAdapter,
)
from .backend import SQLiteBackend
from .config import SQLiteConnectionConfig
from .dialect import SQLiteDialect

__all__ = [
    "SQLiteBackend",
    "SQLiteDialect",
    "SQLiteConnectionConfig",
    "SQLiteBlobAdapter",
    "SQLiteJSONAdapter",
    "SQLiteUUIDAdapter",
]