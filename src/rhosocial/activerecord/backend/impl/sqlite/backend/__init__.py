# src/rhosocial/activerecord/backend/impl/sqlite/backend/__init__.py
"""
SQLite backend implementations.

This module provides both synchronous and asynchronous SQLite backend implementations.

Async components (AsyncSQLiteBackend) are loaded lazily to avoid requiring aiosqlite
for users who only need synchronous operations. Install the async extra to use:
    pip install rhosocial-activerecord[async]
"""

from .sync import SQLiteBackend
from .common import SQLiteBackendMixin, DEFAULT_PRAGMAS

__all__ = [
    "SQLiteBackend",
    "AsyncSQLiteBackend",  # Lazily loaded via __getattr__
    "SQLiteBackendMixin",
    "DEFAULT_PRAGMAS",
]


def __getattr__(name: str):
    """Lazily load AsyncSQLiteBackend to avoid forcing aiosqlite dependency.

    This allows users to import SQLiteBackend without having aiosqlite installed.
    Only when AsyncSQLiteBackend is actually accessed will aiosqlite be required.

    Raises:
        ImportError: If aiosqlite is not installed when accessing AsyncSQLiteBackend.
        AttributeError: If the requested attribute doesn't exist.
    """
    if name == "AsyncSQLiteBackend":
        try:
            from .async_backend import AsyncSQLiteBackend as backend

            return backend
        except ImportError as e:
            raise ImportError(
                "AsyncSQLiteBackend requires 'aiosqlite' package. "
                "Install it with: pip install rhosocial-activerecord[async] "
                "or pip install aiosqlite"
            ) from e
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
