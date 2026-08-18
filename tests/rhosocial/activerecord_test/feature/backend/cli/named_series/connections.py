# tests/rhosocial/activerecord_test/feature/backend/cli/named_series/connections.py
"""Named connection fixtures for the deep named-series test."""

from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig


def mem_db(database: str = ":memory:"):
    """In-memory SQLite connection (default)."""
    return SQLiteConnectionConfig(database=database)


def file_db(database: str = "/tmp/named_series_test.db"):
    """File-based SQLite connection."""
    return SQLiteConnectionConfig(database=database)


def file_db_override(database: str = "/tmp/named_series_override.db", timeout: float = 3.0):
    """File-based SQLite connection with a custom timeout."""
    return SQLiteConnectionConfig(database=database, timeout=timeout)
