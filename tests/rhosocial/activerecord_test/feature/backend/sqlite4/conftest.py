# tests/rhosocial/activerecord_test/feature/backend/sqlite4/conftest.py
"""
Pytest fixtures for SQLite introspection tests.

This module provides fixtures for testing SQLite backend introspection
capabilities, including database setup, table creation, and cleanup.
"""

import os
import sqlite3
import tempfile
from typing import Generator

import pytest

from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend


@pytest.fixture(autouse=True)
def reset_version_cache():
    """Reset SQLite version cache before and after each test.

    This ensures test isolation by clearing the class-level cache
    that may be modified by other tests.
    """
    # Clear cache before test
    SQLiteBackend._sqlite_version_cache = None

    yield

    # Clear cache after test
    SQLiteBackend._sqlite_version_cache = None


@pytest.fixture
def sqlite_backend() -> Generator[SQLiteBackend, None, None]:
    """Create an in-memory SQLite backend for testing.

    Yields:
        SQLiteBackend: Connected SQLite backend instance.
    """
    backend = SQLiteBackend(database=":memory:")
    backend.connect()
    yield backend
    backend.disconnect()


@pytest.fixture
def sqlite_file_backend() -> Generator[SQLiteBackend, None, None]:
    """Create a file-based SQLite backend for testing.

    This fixture creates a temporary database file that is automatically
    cleaned up after the test.

    Yields:
        SQLiteBackend: Connected SQLite backend instance.
    """
    # Create temporary database file
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    backend = SQLiteBackend(database=db_path)
    backend.connect()

    yield backend

    # Cleanup
    backend.disconnect()
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def backend_with_tables(sqlite_backend: SQLiteBackend) -> SQLiteBackend:
    """Create a backend with test tables.

    Creates the following tables:
    - users: User table with primary key
    - posts: Post table with foreign key to users
    - tags: Tag table
    - post_tags: Many-to-many relationship table

    Args:
        sqlite_backend: The base SQLite backend.

    Returns:
        SQLiteBackend: Backend with test tables created.
    """
    # Create users table
    sqlite_backend.executescript("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            age INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX idx_users_email ON users(email);
        CREATE INDEX idx_users_name_age ON users(name, age);

        CREATE TABLE posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            status TEXT DEFAULT 'draft',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
                ON DELETE CASCADE
                ON UPDATE NO ACTION
        );

        CREATE INDEX idx_posts_user_id ON posts(user_id);
        CREATE INDEX idx_posts_status ON posts(status);

        CREATE TABLE tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE post_tags (
            post_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY (post_id, tag_id),
            FOREIGN KEY (post_id) REFERENCES posts(id)
                ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id)
                ON DELETE CASCADE
        );
    """)

    return sqlite_backend


@pytest.fixture
def backend_with_view(backend_with_tables: SQLiteBackend) -> SQLiteBackend:
    """Create a backend with a test view.

    Args:
        backend_with_tables: Backend with test tables.

    Returns:
        SQLiteBackend: Backend with test view created.
    """
    backend_with_tables.executescript("""
        CREATE VIEW user_posts_summary AS
        SELECT
            u.id AS user_id,
            u.name AS user_name,
            COUNT(p.id) AS post_count
        FROM users u
        LEFT JOIN posts p ON u.id = p.user_id
        GROUP BY u.id;
    """)

    return backend_with_tables


@pytest.fixture
def backend_with_trigger(backend_with_tables: SQLiteBackend) -> SQLiteBackend:
    """Create a backend with a test trigger.

    Args:
        backend_with_tables: Backend with test tables.

    Returns:
        SQLiteBackend: Backend with test trigger created.
    """
    backend_with_tables.executescript("""
        CREATE TRIGGER update_user_timestamp
        AFTER UPDATE ON users
        FOR EACH ROW
        BEGIN
            UPDATE users SET created_at = CURRENT_TIMESTAMP
            WHERE id = NEW.id;
        END;
    """)

    return backend_with_tables
