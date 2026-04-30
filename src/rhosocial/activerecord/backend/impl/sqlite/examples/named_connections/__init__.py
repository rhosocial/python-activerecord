# src/rhosocial/activerecord/backend/impl/sqlite/examples/named_connections/__init__.py
"""Named connection examples for SQLite backend.

This module provides example named connection configurations
that can be used with the named connection system.

Examples:
    >>> from rhosocial.activerecord.backend.impl.sqlite.examples.named_connections import memory_db
    >>> config = memory_db()
"""

__all__ = ["memory_db", "file_db", "file_db_wal", "file_db_rollback"]

from rhosocial.activerecord.backend.impl.sqlite.examples.named_connections.memory import memory_db
from rhosocial.activerecord.backend.impl.sqlite.examples.named_connections.file import file_db, file_db_wal, file_db_rollback