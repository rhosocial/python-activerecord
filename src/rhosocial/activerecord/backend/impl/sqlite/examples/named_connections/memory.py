# src/rhosocial/activerecord/backend/impl/sqlite/examples/named_connections/memory.py
"""In-memory database connection examples."""

from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteInMemoryConfig


def memory_db():
    """Default in-memory SQLite database connection.

    This connection creates a fresh in-memory database for each connection.
    Data is lost when the connection is closed.

    Returns:
        SQLiteInMemoryConfig: In-memory database configuration.
    """
    return SQLiteInMemoryConfig()


def memory_db_persistent():
    """Persistent in-memory database with shared cache.

    Uses a named shared cache so multiple connections can
    access the same in-memory database.

    Returns:
        SQLiteInMemoryConfig: In-memory database with shared cache.
    """
    return SQLiteInMemoryConfig(cache_name="persistent_db")