# src/rhosocial/activerecord/backend/impl/sqlite/backend/__init__.py
"""Sqlite backend implementations.

Every backend keeps both classes in this package: the sync class in
``backend.py`` and the async class in ``async_backend.py``. The async class is
re-exported here too, but resolved on first access, because it needs the
``aiosqlite`` package that the ``rhosocial-activerecord[async]`` extra installs.
"""

from .backend import SQLiteBackend

__all__ = [
    "SQLiteBackend",
    "AsyncSQLiteBackend",
]


def __getattr__(name: str):
    """Resolve the async class on first access.

    Raises:
        ImportError: if aiosqlite is missing, naming the extra that provides it.
        AttributeError: for any other name.
    """
    if name == "AsyncSQLiteBackend":
        try:
            from .async_backend import AsyncSQLiteBackend as backend
        except ImportError as e:
            raise ImportError(
                "AsyncSQLiteBackend requires the 'aiosqlite' package. "
                "Install it with: pip install rhosocial-activerecord[async] or pip install aiosqlite"
            ) from e
        return backend
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
