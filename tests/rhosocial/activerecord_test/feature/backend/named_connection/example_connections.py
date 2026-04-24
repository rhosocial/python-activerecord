# tests/rhosocial/activerecord_test/feature/backend/named_connection/example_connections.py
"""
Example named connections for testing.

This module contains sample connection definitions for testing
the named connection functionality.

SQLite connections distinguish between file-based and in-memory databases.
"""
import tempfile
import os

from rhosocial.activerecord.backend.impl.sqlite.config import (
    SQLiteConnectionConfig,
    SQLiteInMemoryConfig,
)


def memory_db():
    """In-memory SQLite database connection."""
    return SQLiteInMemoryConfig()


def file_db(delete_on_close: bool = True):
    """File-based SQLite database connection.

    Creates a temporary file for the database.
    """
    fd, db_path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    if isinstance(delete_on_close, str):
        delete_on_close = delete_on_close.lower() not in ("false", "0", "no")
    return SQLiteConnectionConfig(
        database=db_path,
        delete_on_close=delete_on_close,
    )


def file_db_with_pragmas(journal_mode: str = "WAL"):
    """File-based SQLite connection with custom PRAGMA settings."""
    fd, db_path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    return SQLiteConnectionConfig(
        database=db_path,
        delete_on_close=True,
        pragmas={
            "foreign_keys": "ON",
            "journal_mode": journal_mode,
            "synchronous": "FULL",
        },
    )


def file_db_with_timeout(timeout: float = 5.0):
    """File-based SQLite connection with custom timeout setting."""
    if isinstance(timeout, str):
        timeout = float(timeout)
    fd, db_path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    return SQLiteConnectionConfig(
        database=db_path,
        delete_on_close=True,
        timeout=timeout,
    )
