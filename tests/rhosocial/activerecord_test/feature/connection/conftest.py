# tests/rhosocial/activerecord_test/feature/connection/conftest.py
"""
Pytest fixtures for connection management tests.

This module provides fixtures for testing BackendGroup, BackendManager,
and session-aware connection pool classes with SQLite backends.
"""

import os
import tempfile
from typing import Generator, Type, Optional, Dict, Any

import pytest

from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.backend.async_backend import AsyncSQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.connection import (
    BackendPool,
    AsyncBackendPool,
    PoolConfig,
)


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


# ============================================================
# Session-Aware Connection Pool Fixtures
# ============================================================

@pytest.fixture
def pool_config(sqlite_config: SQLiteConnectionConfig) -> PoolConfig:
    """Create a pool configuration for testing."""
    return PoolConfig(
        min_size=2,
        max_size=5,
        timeout=5.0,
        validate_on_borrow=True,
        validation_query="SELECT 1",
        backend_config={
            'type': 'sqlite',
            'database': sqlite_config.database,
        }
    )


@pytest.fixture
def backend_pool(pool_config: PoolConfig) -> Generator[BackendPool, None, None]:
    """Create a backend pool for testing."""
    pool = BackendPool(pool_config)
    yield pool
    pool.close()


@pytest.fixture
def async_pool_config(sqlite_config: SQLiteConnectionConfig) -> PoolConfig:
    """Create an async pool configuration for testing."""
    return PoolConfig(
        min_size=1,
        max_size=3,
        timeout=5.0,
        validate_on_borrow=True,
        validation_query="SELECT 1",
        backend_config={
            'type': 'sqlite',
            'database': sqlite_config.database,
        }
    )


@pytest.fixture
async def async_backend_pool(async_pool_config: PoolConfig) -> AsyncBackendPool:
    """Create an async backend pool for testing."""
    pool = AsyncBackendPool(async_pool_config)
    yield pool
    await pool.close()


@pytest.fixture
def session_aware_user_model() -> Type[ActiveRecord]:
    """Create a session-aware User model for testing."""
    from rhosocial.activerecord.connection import SessionAwareMixin

    class SessionAwareUser(IntegerPKMixin, SessionAwareMixin, ActiveRecord):
        """Session-aware User model for pool testing."""
        __table_name__ = 'pool_users'

        id: Optional[int] = None
        name: str
        email: str

    return SessionAwareUser


@pytest.fixture
def session_aware_post_model() -> Type[ActiveRecord]:
    """Create a session-aware Post model for testing."""
    from rhosocial.activerecord.connection import SessionAwareMixin

    class SessionAwarePost(IntegerPKMixin, SessionAwareMixin, ActiveRecord):
        """Session-aware Post model for pool testing."""
        __table_name__ = 'pool_posts'

        id: Optional[int] = None
        title: str
        user_id: int

    return SessionAwarePost


@pytest.fixture
async def async_session_aware_user_model() -> Type[AsyncActiveRecord]:
    """Create an async session-aware User model for testing."""
    from rhosocial.activerecord.connection import AsyncSessionAwareMixin

    class AsyncSessionAwareUser(IntegerPKMixin, AsyncSessionAwareMixin, AsyncActiveRecord):
        """Async session-aware User model for pool testing."""
        __table_name__ = 'pool_users'

        id: Optional[int] = None
        name: str
        email: str

    return AsyncSessionAwareUser


@pytest.fixture
def pool_with_tables(backend_pool: BackendPool) -> Generator[BackendPool, None, None]:
    """Create a pool with test tables initialized."""
    with backend_pool.connection() as backend:
        backend.executescript("""
            CREATE TABLE IF NOT EXISTS pool_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS pool_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                user_id INTEGER NOT NULL
            );
        """)
    yield backend_pool
