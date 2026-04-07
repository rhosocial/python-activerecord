# src/rhosocial/activerecord/backend/impl/sqlite/__init__.py
"""
SQLite backend implementation for ActiveRecord.

This module provides a complete SQLite backend implementation for the ActiveRecord ORM,
including connection management, dialect support, type adapters, and query execution.

Async components (AsyncSQLiteBackend, AsyncSQLiteTransactionManager) are loaded lazily
to avoid requiring aiosqlite for users who only need synchronous operations.
Install the async extra to use:
    pip install rhosocial-activerecord[async]
"""

from .backend.sync import SQLiteBackend
from .config import SQLiteConnectionConfig
from .dialect import SQLiteDialect
from .adapters import SQLiteBlobAdapter, SQLiteJSONAdapter, SQLiteUUIDAdapter
from .transaction import SQLiteTransactionManager
from .protocols import SQLiteExtensionSupport, SQLitePragmaSupport
from .mixins import FTS5Mixin, SQLitePragmaMixin, SQLiteExtensionMixin

# EXPLAIN result types
from .explain import (
    SQLiteExplainRow,
    SQLiteExplainQueryPlanRow,
    SQLiteExplainResult,
    SQLiteExplainQueryPlanResult,
)

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
    "SQLiteBackend",
    "AsyncSQLiteBackend",
    "SQLiteConnectionConfig",
    "SQLiteDialect",
    "SQLiteBlobAdapter",
    "SQLiteJSONAdapter",
    "SQLiteUUIDAdapter",
    "SQLiteTransactionManager",
    "AsyncSQLiteTransactionManager",
    # SQLite-specific protocols and mixins
    "SQLiteExtensionSupport",
    "SQLitePragmaSupport",
    "FTS5Mixin",
    "SQLitePragmaMixin",
    "SQLiteExtensionMixin",
    # EXPLAIN result types
    "SQLiteExplainRow",
    "SQLiteExplainQueryPlanRow",
    "SQLiteExplainResult",
    "SQLiteExplainQueryPlanResult",
    # Extension framework
    "ExtensionType",
    "SQLiteExtensionInfo",
    "SQLiteExtensionProtocol",
    "SQLiteExtensionBase",
    "SQLiteExtensionRegistry",
    "get_registry",
    "reset_registry",
    "KNOWN_EXTENSIONS",
    # Extension implementations
    "FTS5Extension",
    "get_fts5_extension",
    "FTS3Extension",
    "FTS4Extension",
    "get_fts3_extension",
    "get_fts4_extension",
    "JSON1Extension",
    "get_json1_extension",
    "RTreeExtension",
    "get_rtree_extension",
    "GeopolyExtension",
    "get_geopoly_extension",
    # Pragma framework
    "PragmaCategory",
    "PragmaInfo",
    "PragmaProtocol",
    "PragmaBase",
    "ALL_PRAGMAS",
    "get_pragma_info",
    "get_all_pragma_infos",
    "get_pragma_names",
    "get_pragmas_by_category",
    # SQLite-specific functions
    "substr",
    "instr",
    "printf",
    "unicode",
    "hex",
    "unhex",
    "zeroblob",
    "randomblob",
    "soundex",
    "group_concat",
    "total",
    "date_func",
    "time_func",
    "datetime_func",
    "julianday",
    "strftime_func",
    "typeof",
    "quote",
    "random_func",
    "abs_sql",
    "sign",
    "last_insert_rowid",
    "changes",
    "trim_sqlite",
    "ltrim",
    "rtrim",
    "iif",
]


def __getattr__(name: str):
    """Lazily load async components to avoid forcing aiosqlite dependency.

    This allows users to import SQLiteBackend and other sync components without
    having aiosqlite installed. Only when async components are actually accessed
    will aiosqlite be required.

    Lazily loaded components:
    - AsyncSQLiteBackend: Async SQLite backend implementation
    - AsyncSQLiteTransactionManager: Async transaction manager

    Raises:
        ImportError: If aiosqlite is not installed when accessing async components.
        AttributeError: If the requested attribute doesn't exist.
    """
    _lazy_imports = {
        "AsyncSQLiteBackend": (".backend.async_backend", "AsyncSQLiteBackend"),
        "AsyncSQLiteTransactionManager": (".async_transaction", "AsyncSQLiteTransactionManager"),
    }

    if name in _lazy_imports:
        module_path, class_name = _lazy_imports[name]
        try:
            import importlib

            module = importlib.import_module(module_path, __name__)
            return getattr(module, class_name)
        except ImportError as e:
            raise ImportError(
                f"{name} requires 'aiosqlite' package. "
                f"Install it with: pip install rhosocial-activerecord[async] "
                f"or pip install aiosqlite"
            ) from e

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
