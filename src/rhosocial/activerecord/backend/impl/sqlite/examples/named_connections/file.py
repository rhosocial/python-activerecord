# src/rhosocial/activerecord/backend/impl/sqlite/examples/named_connections/file.py
"""File-based database connection examples.

This module provides functions that return SQLite connection configurations
for file-based databases. File databases persist data between connections.
"""

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
import os
import tempfile

from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig


def _temp_file(suffix: str = ".sqlite") -> str:
    """Create a temporary file path."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    return path


def file_db(delete_on_close: bool = True):
    """Default file-based SQLite database connection.

    Creates a temporary file that is deleted when the connection closes.

    Args:
        delete_on_close: Whether to delete the file when connection closes.

    Returns:
        SQLiteConnectionConfig: File-based database configuration.
    """
    return SQLiteConnectionConfig(
        database=_temp_file(),
        delete_on_close=delete_on_close,
    )


def file_db_wal():
    """File-based SQLite database with Write-Ahead Logging.

    WAL mode provides better concurrency for read operations
    and is recommended for most workloads.

    Returns:
        SQLiteConnectionConfig: WAL-mode database configuration.
    """
    return SQLiteConnectionConfig(
        database=_temp_file(),
        delete_on_close=True,
        pragmas={
            "journal_mode": "WAL",
            "synchronous": "NORMAL",
        },
    )


def file_db_rollback():
    """File-based SQLite database with rollback journal.

    Default journal mode. Use this for compatibility
    or when WAL is not supported.

    Returns:
        SQLiteConnectionConfig: Rollback journal database configuration.
    """
    return SQLiteConnectionConfig(
        database=_temp_file(),
        delete_on_close=True,
        pragmas={
            "journal_mode": "DELETE",
            "synchronous": "FULL",
        },
    )


def file_db_readonly(db_path: str):
    """Read-only file-based SQLite database.

    Opens the database in read-only mode. The file
    must already exist.

    Args:
        db_path: Path to existing database file.

    Returns:
        SQLiteConnectionConfig: Read-only database configuration.
    """
    return SQLiteConnectionConfig(
        database=db_path,
        delete_on_close=False,
        pragmas={
            "query_only": "ON",
        },
    )


# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
if __name__ == "__main__":
    from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

    print("=" * 60)
    print("File-Based SQLite Connection Examples")
    print("=" * 60)

    # Example 1: Default file database
    print("\n1. Default File Database")
    print("-" * 40)
    config1 = file_db()
    print(f"   config type: {type(config1).__name__}")
    print(f"   database: {config1.database}")
    print(f"   delete_on_close: {config1.delete_on_close}")

    backend1 = SQLiteBackend(config1)
    backend1.connect()
    backend1.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
    backend1.execute("INSERT INTO users (name) VALUES ('Alice')")
    print("   Created table and inserted row successfully")
    backend1.disconnect()

    # Example 2: WAL mode (recommended)
    print("\n2. WAL Mode (Write-Ahead Logging)")
    print("-" * 40)
    config2 = file_db_wal()
    print(f"   config type: {type(config2).__name__}")
    print(f"   database: {config2.database}")
    print(f"   pragmas: {config2.pragmas}")

    backend2 = SQLiteBackend(config2)
    backend2.connect()
    backend2.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
    print("   Database created with WAL mode")
    backend2.disconnect()

    # Example 3: Rollback journal (default)
    print("\n3. Rollback Journal (Default)")
    print("-" * 40)
    config3 = file_db_rollback()
    print(f"   config type: {type(config3).__name__}")
    print(f"   database: {config3.database}")
    print(f"   pragmas: {config3.pragmas}")

    backend3 = SQLiteBackend(config3)
    backend3.connect()
    backend3.execute("CREATE TABLE test2 (id INTEGER PRIMARY KEY)")
    print("   Database created with rollback journal mode")
    backend3.disconnect()

    # Example 4: Read-only mode
    print("\n4. Read-Only Mode")
    print("-" * 40)
    # First create a database with data (don't delete on close)
    tmp = SQLiteConnectionConfig(database=_temp_file(), delete_on_close=False)
    backend_tmp = SQLiteBackend(tmp)
    backend_tmp.connect()
    backend_tmp.execute("CREATE TABLE data (value TEXT)")
    backend_tmp.execute("INSERT INTO data VALUES ('secret')")
    db_path = tmp.database
    print(f"   Created test database at: {db_path}")
    backend_tmp.disconnect()

    # Now open read-only
    config4 = file_db_readonly(db_path)
    print(f"   config type: {type(config4).__name__}")
    print(f"   pragmas: {config4.pragmas}")

    backend4 = SQLiteBackend(config4)
    backend4.connect()
    result = backend4.execute("SELECT * FROM data")
    print(f"   Read data from read-only database: {result.data}")

    # Try to write - should fail or be blocked
    try:
        backend4.execute("INSERT INTO data VALUES ('blocked')")
        print("   Write attempt: ALLOWED (query_only may not work)")
    except Exception as e:
        print(f"   Write attempt: BLOCKED - {type(e).__name__}")
    backend4.disconnect()

    # Cleanup
    os.unlink(db_path)

    print("\n" + "=" * 60)
    print("Usage Notes:")
    print("  - file_db: Default temp file, deleted on close")
    print("  - file_db_wal: Better concurrency, recommended")
    print("  - file_db_rollback: Legacy mode, full sync")
    print("  - file_db_readonly: Prevent accidental writes")
    print("=" * 60)