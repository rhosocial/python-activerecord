# src/rhosocial/activerecord/backend/impl/sqlite/__init__.py
"""
SQLite backend implementation for ActiveRecord.

This module provides a complete SQLite backend implementation for the ActiveRecord ORM,
including connection management, dialect support, type adapters, and query execution.
"""

from .backend.sync import SQLiteBackend
from .backend.async_backend import AsyncSQLiteBackend
from .config import SQLiteConnectionConfig
from .dialect import SQLiteDialect
from .adapters import (
    SQLiteBlobAdapter,
    SQLiteJSONAdapter,
    SQLiteUUIDAdapter
)
from .transaction import (
    SQLiteTransactionManager,
    AsyncSQLiteTransactionManager,
    SQLiteTransactionMixin
)

# SQLite-specific function factories
from .functions import (
    substr,
    instr,
    printf,
    unicode,
    hex,
    unhex,
    zeroblob,
    randomblob,
    soundex,
    group_concat,
    total,
    date_func,
    time_func,
    datetime_func,
    julianday,
    strftime_func,
    typeof,
    quote,
    random_func,
    abs_sql,
    sign,
    last_insert_rowid,
    changes,
    trim_sqlite,
    ltrim,
    rtrim,
    iif,
)

__all__ = [
    'SQLiteBackend',
    'AsyncSQLiteBackend',
    'SQLiteConnectionConfig',
    'SQLiteDialect',
    'SQLiteBlobAdapter',
    'SQLiteJSONAdapter',
    'SQLiteUUIDAdapter',
    'SQLiteTransactionManager',
    'AsyncSQLiteTransactionManager',
    'SQLiteTransactionMixin',
    # SQLite-specific functions
    'substr',
    'instr',
    'printf',
    'unicode',
    'hex',
    'unhex',
    'zeroblob',
    'randomblob',
    'soundex',
    'group_concat',
    'total',
    'date_func',
    'time_func',
    'datetime_func',
    'julianday',
    'strftime_func',
    'typeof',
    'quote',
    'random_func',
    'abs_sql',
    'sign',
    'last_insert_rowid',
    'changes',
    'trim_sqlite',
    'ltrim',
    'rtrim',
    'iif',
]