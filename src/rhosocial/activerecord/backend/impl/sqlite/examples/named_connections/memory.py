# src/rhosocial/activerecord/backend/impl/sqlite/examples/named_connections/memory.py
"""In-memory database connection examples.

This module provides functions that return SQLite connection configurations
for in-memory databases. In-memory databases are fast but temporary - data
is lost when the connection closes.
"""

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
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
    return SQLiteInMemoryConfig(database="file:persistent_db?mode=memory&cache=shared")


# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
if __name__ == "__main__":
    from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

    print("=" * 60)
    print("In-Memory SQLite Connection Examples")
    print("=" * 60)

    # Example 1: Default in-memory database
    print("\n1. Default In-Memory Database")
    print("-" * 40)
    config1 = memory_db()
    print(f"   config type: {type(config1).__name__}")
    print(f"   database: {config1.database}")
    print(f"   pragmas: {config1.pragmas}")

    # Connect and test
    backend1 = SQLiteBackend(config1)
    backend1.connect()
    backend1.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
    backend1.execute("INSERT INTO test (id) VALUES (1)")
    result = backend1.execute("SELECT * FROM test")
    print(f"   Created table and inserted row: {result.data}")
    backend1.disconnect()

    # Example 2: Persistent in-memory database (shared cache)
    print("\n2. Persistent In-Memory Database (Shared Cache)")
    print("-" * 40)
    config2 = memory_db_persistent()
    print(f"   config type: {type(config2).__name__}")
    print(f"   database: {config2.database}")
    print(f"   pragmas: {config2.pragmas}")

    # Connect with persistent cache - data survives across connections
    backend2a = SQLiteBackend(config2)
    backend2a.connect()
    backend2a.execute("CREATE TABLE IF NOT EXISTS persistent (id INTEGER PRIMARY KEY, data TEXT)")
    backend2a.execute("INSERT INTO persistent (data) VALUES ('first connection')")
    result2a = backend2a.execute("SELECT * FROM persistent")
    print(f"   First connection wrote: {result2a.data}")

    # Second connection to same cache can see the data
    backend2b = SQLiteBackend(config2)
    backend2b.connect()
    result2b = backend2b.execute("SELECT * FROM persistent")
    print(f"   Second connection read: {result2b.data}")
    backend2b.disconnect()
    backend2a.disconnect()

    print("\n" + "=" * 60)
    print("Usage Notes:")
    print("  - Default memory_db: fresh database each connection")
    print("  - memory_db_persistent: shared cache retains data")
    print("  - Use for testing, caching, or temporary data")
    print("=" * 60)

    # Cleanup: remove temp files created by URI-based shared cache
    import os
    cache_file = "persistent_db"
    if os.path.exists(cache_file):
        os.unlink(cache_file)
        print(f"\n[Cleanup] Removed temp file: {cache_file}")