# tests/rhosocial/activerecord_test/connection/conftest.py
"""
Pytest fixtures for connection management tests.

This module provides fixtures for testing ConnectionGroup and ConnectionManager
classes with SQLite backends.
"""

import os
import tempfile
from typing import Generator, Type, Optional

import pytest

from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.backend.async_backend import AsyncSQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.field import IntegerPKMixin


# Define test model classes
class User(IntegerPKMixin, ActiveRecord):
    """Test User model."""
    __table_name__ = 'users'

    id: Optional[int] = None
    name: str
    email: str


class Post(IntegerPKMixin, ActiveRecord):
    """Test Post model."""
    __table_name__ = 'posts'

    id: Optional[int] = None
    title: str
    user_id: int


class Comment(IntegerPKMixin, ActiveRecord):
    """Test Comment model."""
    __table_name__ = 'comments'

    id: Optional[int] = None
    content: str
    post_id: int


class AsyncUser(IntegerPKMixin, AsyncActiveRecord):
    """Test Async User model."""
    __table_name__ = 'users'

    id: Optional[int] = None
    name: str
    email: str


class AsyncPost(IntegerPKMixin, AsyncActiveRecord):
    """Test Async Post model."""
    __table_name__ = 'posts'

    id: Optional[int] = None
    title: str
    user_id: int


@pytest.fixture
def sqlite_config() -> SQLiteConnectionConfig:
    """Create an in-memory SQLite connection config."""
    return SQLiteConnectionConfig(database=":memory:")


@pytest.fixture
def sqlite_file_config() -> Generator[SQLiteConnectionConfig, None, None]:
    """Create a file-based SQLite connection config."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    config = SQLiteConnectionConfig(database=db_path)

    yield config

    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def backend_class() -> Type[SQLiteBackend]:
    """Return SQLite backend class."""
    return SQLiteBackend


@pytest.fixture
def async_backend_class() -> Type[AsyncSQLiteBackend]:
    """Return async SQLite backend class."""
    return AsyncSQLiteBackend


@pytest.fixture
def configured_backend(sqlite_config: SQLiteConnectionConfig,
                       backend_class: Type[SQLiteBackend]) -> Generator[SQLiteBackend, None, None]:
    """Create and connect a backend for tests that need pre-configured backends."""
    backend = backend_class(**sqlite_config.model_dump())
    backend.connect()

    # Create test tables
    backend.executescript("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL
        );
        CREATE TABLE posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            user_id INTEGER NOT NULL
        );
        CREATE TABLE comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            post_id INTEGER NOT NULL
        );
    """)

    yield backend

    backend.disconnect()
