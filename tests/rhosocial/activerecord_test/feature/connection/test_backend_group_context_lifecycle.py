# tests/rhosocial/activerecord_test/feature/connection/test_backend_group_context_lifecycle.py
"""
Tests for BackendGroup context-based connection lifecycle management.

Tests the pattern where users leverage backend.context() for on-demand
connections ("connect on demand, disconnect after use"):
    configure() → with backend.context(): → CRUD → exit context
    → group.disconnect()

The context manager handles connect/introspect/disconnect automatically.
"""

import os
import tempfile
from typing import Optional

import pytest

from rhosocial.activerecord.connection import BackendGroup, AsyncBackendGroup
from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.backend.async_backend import AsyncSQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.backend.errors import QueryError


# ============================================================
# Test Models (dedicated for context lifecycle tests)
# ============================================================

class ContextUser(IntegerPKMixin, ActiveRecord):
    """Test User model for context lifecycle tests."""
    __table_name__ = 'context_users'

    id: Optional[int] = None
    name: str
    email: str


class ContextPost(IntegerPKMixin, ActiveRecord):
    """Test Post model for context lifecycle tests."""
    __table_name__ = 'context_posts'

    id: Optional[int] = None
    title: str
    user_id: int


class AsyncContextUser(IntegerPKMixin, AsyncActiveRecord):
    """Test async User model for context lifecycle tests."""
    __table_name__ = 'context_users'

    id: Optional[int] = None
    name: str
    email: str


class AsyncContextPost(IntegerPKMixin, AsyncActiveRecord):
    """Test async Post model for context lifecycle tests."""
    __table_name__ = 'context_posts'

    id: Optional[int] = None
    title: str
    user_id: int


# ============================================================
# Helpers
# ============================================================

DDL_OPTIONS = ExecutionOptions(stmt_type=StatementType.DDL)
DML_OPTIONS = ExecutionOptions(stmt_type=StatementType.DML)
DQL_OPTIONS = ExecutionOptions(stmt_type=StatementType.DQL)

CREATE_USERS_TABLE = """
    CREATE TABLE IF NOT EXISTS context_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL
    )
"""

CREATE_POSTS_TABLE = """
    CREATE TABLE IF NOT EXISTS context_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        user_id INTEGER NOT NULL
    )
"""


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def backend_class():
    return SQLiteBackend


@pytest.fixture
def async_backend_class():
    return AsyncSQLiteBackend


@pytest.fixture
def context_group(backend_class):
    """Configured BackendGroup with file-based SQLite and pre-created schema.

    Uses file-based SQLite to ensure data persists across context() cycles.
    Schema is created during fixture setup so tests can focus on
    context-based connection lifecycle without worrying about DDL.
    """
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    config = SQLiteConnectionConfig(database=db_path)

    group = BackendGroup(
        name="context",
        models=[ContextUser, ContextPost],
        config=config,
        backend_class=backend_class,
    )
    group.configure()

    # Pre-create schema
    backend = group.get_backend()
    backend.connect()
    backend.introspect_and_adapt()
    backend.execute(CREATE_USERS_TABLE, options=DDL_OPTIONS)
    backend.execute(CREATE_POSTS_TABLE, options=DDL_OPTIONS)
    backend.disconnect()

    yield group
    group.disconnect()
    if os.path.exists(db_path):
        os.unlink(db_path)


# ============================================================
# Sync Tests
# ============================================================

class TestContextLifecycle:
    """Tests for context-based connection lifecycle management (sync)."""

    def test_full_lifecycle(self, context_group):
        """Test complete context lifecycle: context → CRUD → cleanup."""
        group = context_group
        backend = group.get_backend()

        # Not connected before context
        assert not group.is_connected()

        with backend.context() as ctx:
            assert group.is_connected()

            ctx.execute(
                "INSERT INTO context_users (name, email) VALUES (?, ?)",
                ["Alice", "alice@example.com"],
                options=DML_OPTIONS,
            )
            result = ctx.execute(
                "SELECT * FROM context_users WHERE name = ?",
                ["Alice"],
                options=DQL_OPTIONS,
            )
            assert len(result.data) == 1
            assert result.data[0]["name"] == "Alice"

        # Auto-disconnected after context exit
        assert not group.is_connected()

    def test_context_auto_connect_disconnect(self, context_group):
        """Test that context automatically connects and disconnects."""
        group = context_group
        backend = group.get_backend()

        # Before: not connected
        assert not group.is_connected()

        with backend.context():
            # Inside: connected (context calls connect + introspect_and_adapt)
            assert group.is_connected()

        # After: auto-disconnected
        assert not group.is_connected()

    def test_context_cycle(self, context_group):
        """Test multiple context() cycles within the same group."""
        group = context_group
        backend = group.get_backend()

        # First context: insert data
        with backend.context() as ctx:
            ctx.execute(
                "INSERT INTO context_users (name, email) VALUES (?, ?)",
                ["Alice", "alice@example.com"],
                options=DML_OPTIONS,
            )

        assert not group.is_connected()

        # Second context: verify data persists and add more
        with backend.context() as ctx:
            result = ctx.execute(
                "SELECT * FROM context_users",
                options=DQL_OPTIONS,
            )
            assert len(result.data) == 1

            ctx.execute(
                "INSERT INTO context_users (name, email) VALUES (?, ?)",
                ["Bob", "bob@example.com"],
                options=DML_OPTIONS,
            )

        # Third context: verify both records
        with backend.context() as ctx:
            result = ctx.execute(
                "SELECT * FROM context_users ORDER BY id",
                options=DQL_OPTIONS,
            )
            assert len(result.data) == 2

        assert not group.is_connected()

    def test_is_connected_inside_outside_context(self, context_group):
        """Test is_connected() state inside and outside context."""
        group = context_group
        backend = group.get_backend()

        # Outside: not connected
        assert not group.is_connected()

        with backend.context():
            # Inside: connected
            assert group.is_connected()

        # Outside again: not connected
        assert not group.is_connected()

    def test_crud_in_context(self, context_group):
        """Test full CRUD operations within a context block."""
        group = context_group
        backend = group.get_backend()

        with backend.context() as ctx:
            # Create
            ctx.execute(
                "INSERT INTO context_users (name, email) VALUES (?, ?)",
                ["Alice", "alice@example.com"],
                options=DML_OPTIONS,
            )

            # Read
            result = ctx.execute(
                "SELECT * FROM context_users WHERE name = ?",
                ["Alice"],
                options=DQL_OPTIONS,
            )
            assert len(result.data) == 1

            # Update
            ctx.execute(
                "UPDATE context_users SET email = ? WHERE name = ?",
                ["newalice@example.com", "Alice"],
                options=DML_OPTIONS,
            )
            result = ctx.execute(
                "SELECT email FROM context_users WHERE name = ?",
                ["Alice"],
                options=DQL_OPTIONS,
            )
            assert result.data[0]["email"] == "newalice@example.com"

            # Delete
            ctx.execute(
                "DELETE FROM context_users WHERE name = ?",
                ["Alice"],
                options=DML_OPTIONS,
            )
            result = ctx.execute(
                "SELECT * FROM context_users",
                options=DQL_OPTIONS,
            )
            assert len(result.data) == 0

    def test_exception_in_context_auto_disconnect(self, context_group):
        """Test that context auto-disconnects even on exception."""
        group = context_group
        backend = group.get_backend()

        with pytest.raises(ValueError):
            with backend.context() as ctx:
                assert group.is_connected()
                raise ValueError("Test exception")

        # Auto-disconnected despite exception
        assert not group.is_connected()

    def test_exception_in_context_from_sql(self, context_group):
        """Test that SQL error in context auto-disconnects."""
        group = context_group
        backend = group.get_backend()

        with pytest.raises(QueryError):
            with backend.context() as ctx:
                ctx.execute("SELECT * FROM nonexistent_table", options=DQL_OPTIONS)

        # Auto-disconnected despite SQL error
        assert not group.is_connected()

    def test_multiple_models_in_context(self, context_group):
        """Test operations on multiple models within the same context."""
        group = context_group
        backend = group.get_backend()

        with backend.context() as ctx:
            # Insert user
            ctx.execute(
                "INSERT INTO context_users (name, email) VALUES (?, ?)",
                ["Alice", "alice@example.com"],
                options=DML_OPTIONS,
            )

            # Insert post referencing user
            ctx.execute(
                "INSERT INTO context_posts (title, user_id) VALUES (?, ?)",
                ["First Post", 1],
                options=DML_OPTIONS,
            )

            # Join query
            result = ctx.execute(
                "SELECT p.title, u.name FROM context_posts p "
                "JOIN context_users u ON p.user_id = u.id",
                options=DQL_OPTIONS,
            )
            assert len(result.data) == 1
            assert result.data[0]["title"] == "First Post"
            assert result.data[0]["name"] == "Alice"


# ============================================================
# Async Tests
# ============================================================

class TestAsyncContextLifecycle:
    """Tests for context-based connection lifecycle management (async)."""

    @pytest.fixture
    async def async_context_group(self, async_backend_class):
        """Configured AsyncBackendGroup with file-based SQLite and pre-created schema."""
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        config = SQLiteConnectionConfig(database=db_path)

        group = AsyncBackendGroup(
            name="async_context",
            models=[AsyncContextUser, AsyncContextPost],
            config=config,
            backend_class=async_backend_class,
        )
        await group.configure()

        # Pre-create schema
        backend = group.get_backend()
        await backend.connect()
        await backend.introspect_and_adapt()
        await backend.execute(CREATE_USERS_TABLE, options=DDL_OPTIONS)
        await backend.execute(CREATE_POSTS_TABLE, options=DDL_OPTIONS)
        await backend.disconnect()

        yield group
        await group.disconnect()
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_async_full_lifecycle(self, async_context_group):
        """Test complete async context lifecycle."""
        group = async_context_group
        backend = group.get_backend()

        assert not await group.is_connected()

        async with backend.context() as ctx:
            assert await group.is_connected()
            await ctx.execute(
                "INSERT INTO context_users (name, email) VALUES (?, ?)",
                ["Alice", "alice@example.com"],
                options=DML_OPTIONS,
            )
            result = await ctx.execute(
                "SELECT * FROM context_users WHERE name = ?",
                ["Alice"],
                options=DQL_OPTIONS,
            )
            assert len(result.data) == 1

        assert not await group.is_connected()

    @pytest.mark.asyncio
    async def test_async_context_auto_connect_disconnect(self, async_context_group):
        """Test async context auto-connects and disconnects."""
        group = async_context_group
        backend = group.get_backend()

        assert not await group.is_connected()

        async with backend.context():
            assert await group.is_connected()

        assert not await group.is_connected()

    @pytest.mark.asyncio
    async def test_async_context_cycle(self, async_context_group):
        """Test multiple async context cycles with data persistence."""
        group = async_context_group
        backend = group.get_backend()

        # First context: insert data
        async with backend.context() as ctx:
            await ctx.execute(
                "INSERT INTO context_users (name, email) VALUES (?, ?)",
                ["User0", "user0@example.com"],
                options=DML_OPTIONS,
            )

        # Second context: verify and add more
        async with backend.context() as ctx:
            result = await ctx.execute(
                "SELECT * FROM context_users",
                options=DQL_OPTIONS,
            )
            assert len(result.data) == 1

            await ctx.execute(
                "INSERT INTO context_users (name, email) VALUES (?, ?)",
                ["User1", "user1@example.com"],
                options=DML_OPTIONS,
            )

        # Third context: verify both records
        async with backend.context() as ctx:
            result = await ctx.execute(
                "SELECT * FROM context_users ORDER BY id",
                options=DQL_OPTIONS,
            )
            assert len(result.data) == 2

        assert not await group.is_connected()

    @pytest.mark.asyncio
    async def test_async_is_connected_inside_outside_context(self, async_context_group):
        """Test async is_connected() inside and outside context."""
        group = async_context_group
        backend = group.get_backend()

        assert not await group.is_connected()

        async with backend.context():
            assert await group.is_connected()

        assert not await group.is_connected()

    @pytest.mark.asyncio
    async def test_async_crud_in_context(self, async_context_group):
        """Test async CRUD within context."""
        group = async_context_group
        backend = group.get_backend()

        async with backend.context() as ctx:
            await ctx.execute(
                "INSERT INTO context_users (name, email) VALUES (?, ?)",
                ["Alice", "alice@example.com"],
                options=DML_OPTIONS,
            )

            result = await ctx.execute(
                "SELECT * FROM context_users WHERE name = ?",
                ["Alice"],
                options=DQL_OPTIONS,
            )
            assert len(result.data) == 1

            await ctx.execute(
                "UPDATE context_users SET email = ? WHERE name = ?",
                ["newalice@example.com", "Alice"],
                options=DML_OPTIONS,
            )

            await ctx.execute(
                "DELETE FROM context_users WHERE name = ?",
                ["Alice"],
                options=DML_OPTIONS,
            )
            result = await ctx.execute(
                "SELECT * FROM context_users",
                options=DQL_OPTIONS,
            )
            assert len(result.data) == 0

    @pytest.mark.asyncio
    async def test_async_exception_in_context_auto_disconnect(self, async_context_group):
        """Test async context auto-disconnects on exception."""
        group = async_context_group
        backend = group.get_backend()

        with pytest.raises(ValueError):
            async with backend.context():
                assert await group.is_connected()
                raise ValueError("Async test exception")

        assert not await group.is_connected()

    @pytest.mark.asyncio
    async def test_async_multiple_models_in_context(self, async_context_group):
        """Test async operations on multiple models within same context."""
        group = async_context_group
        backend = group.get_backend()

        async with backend.context() as ctx:
            await ctx.execute(
                "INSERT INTO context_users (name, email) VALUES (?, ?)",
                ["Alice", "alice@example.com"],
                options=DML_OPTIONS,
            )
            await ctx.execute(
                "INSERT INTO context_posts (title, user_id) VALUES (?, ?)",
                ["First Post", 1],
                options=DML_OPTIONS,
            )

            result = await ctx.execute(
                "SELECT p.title, u.name FROM context_posts p "
                "JOIN context_users u ON p.user_id = u.id",
                options=DQL_OPTIONS,
            )
            assert len(result.data) == 1
            assert result.data[0]["title"] == "First Post"
