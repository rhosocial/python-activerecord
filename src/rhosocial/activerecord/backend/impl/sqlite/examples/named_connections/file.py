# src/rhosocial/activerecord/backend/impl/sqlite/examples/named_connections/file.py
"""File-based database connection examples."""

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


def file_db_readonly():
    """Read-only file-based SQLite database.

    Opens the database in read-only mode. The file
    must already exist.

    Returns:
        SQLiteConnectionConfig: Read-only database configuration.
    """
    return SQLiteConnectionConfig(
        database=_temp_file(),
        delete_on_close=True,
        pragmas={
            "query_only": "ON",
        },
    )