# src/rhosocial/activerecord/backend/impl/sqlite/backend/__init__.py
"""SQLite backend implementations.

This module provides the synchronous SQLite backend implementation. The async
counterpart lives in ``impl.sqlite.backend.async_backend``; every backend follows that
layout, so the sync class is always at ``impl.<backend>.backend`` and the async
class at ``impl.<backend>.async_backend``.
"""

from .backend import SQLiteBackend
from .common import SQLiteBackendMixin, DEFAULT_PRAGMAS

__all__ = [
    "SQLiteBackend",
    "SQLiteBackendMixin",
    "DEFAULT_PRAGMAS",
]
