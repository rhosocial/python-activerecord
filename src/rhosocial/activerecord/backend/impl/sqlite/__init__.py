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
    SQLiteTransactionMixin
)
from .async_transaction import AsyncSQLiteTransactionManager
from .protocols import SQLiteExtensionSupport, SQLitePragmaSupport
from .mixins import FTS5Mixin, SQLitePragmaMixin, SQLiteExtensionMixin

# Extension framework
from .extension import (
    ExtensionType,
    SQLiteExtensionInfo,
    SQLiteExtensionProtocol,
    SQLiteExtensionBase,
    SQLiteExtensionRegistry,
    get_registry,
    reset_registry,
    KNOWN_EXTENSIONS,
)

# Extension implementations
from .extension.extensions import (
    FTS5Extension,
    get_fts5_extension,
    FTS3Extension,
    FTS4Extension,
    get_fts3_extension,
    get_fts4_extension,
    JSON1Extension,
    get_json1_extension,
    RTreeExtension,
    get_rtree_extension,
    GeopolyExtension,
    get_geopoly_extension,
)

# Pragma framework
from .pragma import (
    PragmaCategory,
    PragmaInfo,
    PragmaProtocol,
    PragmaBase,
    SQLitePragmaSupport as PragmaSQLitePragmaSupport,
    ALL_PRAGMAS,
    get_pragma_info,
    get_all_pragma_infos,
    get_pragma_names,
    get_pragmas_by_category,
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
    # SQLite-specific protocols and mixins
    'SQLiteExtensionSupport',
    'SQLitePragmaSupport',
    'FTS5Mixin',
    'SQLitePragmaMixin',
    'SQLiteExtensionMixin',
    # Extension framework
    'ExtensionType',
    'SQLiteExtensionInfo',
    'SQLiteExtensionProtocol',
    'SQLiteExtensionBase',
    'SQLiteExtensionRegistry',
    'get_registry',
    'reset_registry',
    'KNOWN_EXTENSIONS',
    # Extension implementations
    'FTS5Extension',
    'get_fts5_extension',
    'FTS3Extension',
    'FTS4Extension',
    'get_fts3_extension',
    'get_fts4_extension',
    'JSON1Extension',
    'get_json1_extension',
    'RTreeExtension',
    'get_rtree_extension',
    'GeopolyExtension',
    'get_geopoly_extension',
    # Pragma framework
    'PragmaCategory',
    'PragmaInfo',
    'PragmaProtocol',
    'PragmaBase',
    'ALL_PRAGMAS',
    'get_pragma_info',
    'get_all_pragma_infos',
    'get_pragma_names',
    'get_pragmas_by_category',
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
