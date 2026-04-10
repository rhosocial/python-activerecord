# tests/rhosocial/activerecord_test/feature/connection/test_backend_group_manual_lifecycle.py
"""
Tests for BackendGroup manual connection lifecycle management.

Tests the pattern where users manually manage connection timing:
    configure() → backend.connect() → backend.introspect_and_adapt()
    → CRUD operations → backend.disconnect() → group.disconnect()

Users are responsible for deciding when to connect and disconnect.
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


# ============================================================
# Test Models (dedicated for manual lifecycle tests)
# ============================================================

class ManualUser(IntegerPKMixin, ActiveRecord):
    """Test User model for manual lifecycle tests."""
    __table_name__ = 'manual_users'

    id: Optional[int] = None
    name: str
    email: str


class ManualPost(IntegerPKMixin, ActiveRecord):
    """Test Post model for manual lifecycle tests."""
    __table_name__ = 'manual_posts'

    id: Optional[int] = None
    title: str
    user_id: int


class AsyncManualUser(IntegerPKMixin, AsyncActiveRecord):
    """Test async User model for manual lifecycle tests."""
    __table_name__ = 'manual_users'

    id: Optional[int] = None
    name: str
    email: str


class AsyncManualPost(IntegerPKMixin, AsyncActiveRecord):
    """Test async Post model for manual lifecycle tests."""
    __table_name__ = 'manual_posts'

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
    CREATE TABLE IF NOT EXISTS manual_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL
    )
"""

CREATE_POSTS_TABLE = """
    CREATE TABLE IF NOT EXISTS manual_posts (
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
def manual_group(backend_class):
    """Configured BackendGroup with file-based SQLite and pre-created schema.

    Uses file-based SQLite to ensure data persists across connect/disconnect
    cycles. Schema is created during fixture setup so tests can focus on
    connection lifecycle without worrying about DDL.
    """
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    config = SQLiteConnectionConfig(database=db_path)

    group = BackendGroup(
        name="manual",
        models=[ManualUser, ManualPost],
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

class TestManualLifecycle:
    """Tests for manual connection lifecycle management (sync)."""

    def test_full_lifecycle(self, manual_group):
        """Test complete manual lifecycle: connect → CRUD → disconnect."""
        group = manual_group
        backend = group.get_backend()

        # Not connected before manual connect
        assert not group.is_connected()

        # Manual connect
        backend.connect()
        backend.introspect_and_adapt()
        assert group.is_connected()

        # CRUD operations (schema already prepared)
        backend.execute(
            "INSERT INTO manual_users (name, email) VALUES (?, ?)",
            ["Alice", "alice@example.com"],
            options=DML_OPTIONS,
        )
        result = backend.execute(
            "SELECT * FROM manual_users WHERE name = ?",
            ["Alice"],
            options=DQL_OPTIONS,
        )
        assert len(result.data) == 1
        assert result.data[0]["name"] == "Alice"

        # Manual disconnect
        backend.disconnect()
        assert not group.is_connected()

    def test_connect_disconnect_cycle(self, manual_group):
        """Test multiple connect/disconnect cycles within the same group."""
        group = manual_group
        backend = group.get_backend()

        for i in range(3):
            backend.connect()
            backend.introspect_and_adapt()
            assert group.is_connected()

            backend.execute(
                "INSERT INTO manual_users (name, email) VALUES (?, ?)",
                [f"User{i}", f"user{i}@example.com"],
                options=DML_OPTIONS,
            )

            backend.disconnect()
            assert not group.is_connected()

        # Verify all data from cycles persists (file-based DB)
        backend.connect()
        backend.introspect_and_adapt()
        result = backend.execute(
            "SELECT * FROM manual_users ORDER BY id",
            options=DQL_OPTIONS,
        )
        assert len(result.data) == 3
        backend.disconnect()

    def test_data_persistence_across_connections(self, manual_group):
        """Test data persists across manual connect/disconnect."""
        group = manual_group
        backend = group.get_backend()

        # First connection: insert data
        backend.connect()
        backend.introspect_and_adapt()
        backend.execute(
            "INSERT INTO manual_users (name, email) VALUES (?, ?)",
            ["Alice", "alice@example.com"],
            options=DML_OPTIONS,
        )
        backend.disconnect()

        # Second connection: verify data persists
        backend.connect()
        backend.introspect_and_adapt()
        result = backend.execute(
            "SELECT * FROM manual_users",
            options=DQL_OPTIONS,
        )
        assert len(result.data) == 1
        assert result.data[0]["name"] == "Alice"
        backend.disconnect()

    def test_is_connected_state_transitions(self, manual_group):
        """Test is_connected() reflects correct state at each stage."""
        group = manual_group
        backend = group.get_backend()

        # After configure: not connected
        assert not group.is_connected()

        # After connect: connected
        backend.connect()
        backend.introspect_and_adapt()
        assert group.is_connected()

        # After disconnect: not connected
        backend.disconnect()
        assert not group.is_connected()

        # Can reconnect
        backend.connect()
        backend.introspect_and_adapt()
        assert group.is_connected()
        backend.disconnect()
        assert not group.is_connected()

    def test_crud_while_connected(self, manual_group):
        """Test full CRUD operations while manually connected."""
        group = manual_group
        backend = group.get_backend()

        backend.connect()
        backend.introspect_and_adapt()

        # Create
        backend.execute(
            "INSERT INTO manual_users (name, email) VALUES (?, ?)",
            ["Alice", "alice@example.com"],
            options=DML_OPTIONS,
        )

        # Read
        result = backend.execute(
            "SELECT * FROM manual_users WHERE name = ?",
            ["Alice"],
            options=DQL_OPTIONS,
        )
        assert len(result.data) == 1

        # Update
        backend.execute(
            "UPDATE manual_users SET email = ? WHERE name = ?",
            ["newalice@example.com", "Alice"],
            options=DML_OPTIONS,
        )
        result = backend.execute(
            "SELECT email FROM manual_users WHERE name = ?",
            ["Alice"],
            options=DQL_OPTIONS,
        )
        assert result.data[0]["email"] == "newalice@example.com"

        # Delete
        backend.execute(
            "DELETE FROM manual_users WHERE name = ?",
            ["Alice"],
            options=DML_OPTIONS,
        )
        result = backend.execute(
            "SELECT * FROM manual_users",
            options=DQL_OPTIONS,
        )
        assert len(result.data) == 0

        backend.disconnect()

    def test_multiple_models_share_backend(self, manual_group):
        """Test two models share the same backend instance."""
        group = manual_group
        backend = group.get_backend()

        assert ManualUser.__backend__ is ManualPost.__backend__
        assert ManualUser.__backend__ is backend

        backend.connect()
        backend.introspect_and_adapt()

        # Insert user
        backend.execute(
            "INSERT INTO manual_users (name, email) VALUES (?, ?)",
            ["Alice", "alice@example.com"],
            options=DML_OPTIONS,
        )

        # Insert post referencing user
        backend.execute(
            "INSERT INTO manual_posts (title, user_id) VALUES (?, ?)",
            ["First Post", 1],
            options=DML_OPTIONS,
        )

        # Query both
        users = backend.execute("SELECT * FROM manual_users", options=DQL_OPTIONS)
        posts = backend.execute("SELECT * FROM manual_posts", options=DQL_OPTIONS)
        assert len(users.data) == 1
        assert len(posts.data) == 1
        assert posts.data[0]["user_id"] == users.data[0]["id"]

        backend.disconnect()

    def test_exception_during_operation(self, manual_group):
        """Test that exception during operation doesn't auto-disconnect."""
        group = manual_group
        backend = group.get_backend()

        backend.connect()
        backend.introspect_and_adapt()

        # Operation raises an error, but connection remains open
        with pytest.raises(Exception):
            backend.execute("SELECT * FROM nonexistent_table", options=DQL_OPTIONS)

        # Still connected after error
        assert group.is_connected()

        # Can still execute valid queries
        result = backend.execute("SELECT 1", options=DQL_OPTIONS)
        assert result is not None

        # User decides when to disconnect
        backend.disconnect()
        assert not group.is_connected()


# ============================================================
# Async Tests
# ============================================================

class TestAsyncManualLifecycle:
    """Tests for manual connection lifecycle management (async)."""

    @pytest.fixture
    async def async_manual_group(self, async_backend_class):
        """Configured AsyncBackendGroup with file-based SQLite and pre-created schema."""
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        config = SQLiteConnectionConfig(database=db_path)

        group = AsyncBackendGroup(
            name="async_manual",
            models=[AsyncManualUser, AsyncManualPost],
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
    async def test_async_full_lifecycle(self, async_manual_group):
        """Test complete async manual lifecycle."""
        group = async_manual_group
        backend = group.get_backend()

        assert not await group.is_connected()

        await backend.connect()
        await backend.introspect_and_adapt()
        assert await group.is_connected()

        await backend.execute(
            "INSERT INTO manual_users (name, email) VALUES (?, ?)",
            ["Alice", "alice@example.com"],
            options=DML_OPTIONS,
        )
        result = await backend.execute(
            "SELECT * FROM manual_users",
            options=DQL_OPTIONS,
        )
        assert len(result.data) == 1

        await backend.disconnect()
        assert not await group.is_connected()

    @pytest.mark.asyncio
    async def test_async_connect_disconnect_cycle(self, async_manual_group):
        """Test multiple async connect/disconnect cycles."""
        group = async_manual_group
        backend = group.get_backend()

        for i in range(3):
            await backend.connect()
            await backend.introspect_and_adapt()
            assert await group.is_connected()

            await backend.execute(
                "INSERT INTO manual_users (name, email) VALUES (?, ?)",
                [f"User{i}", f"user{i}@example.com"],
                options=DML_OPTIONS,
            )

            await backend.disconnect()
            assert not await group.is_connected()

        # Verify all data persists (file-based DB)
        await backend.connect()
        await backend.introspect_and_adapt()
        result = await backend.execute(
            "SELECT * FROM manual_users ORDER BY id",
            options=DQL_OPTIONS,
        )
        assert len(result.data) == 3
        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_async_is_connected_state_transitions(self, async_manual_group):
        """Test async is_connected() state transitions."""
        group = async_manual_group
        backend = group.get_backend()

        assert not await group.is_connected()

        await backend.connect()
        await backend.introspect_and_adapt()
        assert await group.is_connected()

        await backend.disconnect()
        assert not await group.is_connected()

        await backend.connect()
        await backend.introspect_and_adapt()
        assert await group.is_connected()
        await backend.disconnect()
        assert not await group.is_connected()

    @pytest.mark.asyncio
    async def test_async_crud_while_connected(self, async_manual_group):
        """Test async CRUD while manually connected."""
        group = async_manual_group
        backend = group.get_backend()

        await backend.connect()
        await backend.introspect_and_adapt()

        # Create
        await backend.execute(
            "INSERT INTO manual_users (name, email) VALUES (?, ?)",
            ["Alice", "alice@example.com"],
            options=DML_OPTIONS,
        )

        # Read
        result = await backend.execute(
            "SELECT * FROM manual_users WHERE name = ?",
            ["Alice"],
            options=DQL_OPTIONS,
        )
        assert len(result.data) == 1

        # Update
        await backend.execute(
            "UPDATE manual_users SET email = ? WHERE name = ?",
            ["newalice@example.com", "Alice"],
            options=DML_OPTIONS,
        )

        # Delete
        await backend.execute(
            "DELETE FROM manual_users WHERE name = ?",
            ["Alice"],
            options=DML_OPTIONS,
        )
        result = await backend.execute(
            "SELECT * FROM manual_users",
            options=DQL_OPTIONS,
        )
        assert len(result.data) == 0

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_async_exception_during_operation(self, async_manual_group):
        """Test async exception during operation doesn't auto-disconnect."""
        group = async_manual_group
        backend = group.get_backend()

        await backend.connect()
        await backend.introspect_and_adapt()

        with pytest.raises(Exception):
            await backend.execute("SELECT * FROM nonexistent_table", options=DQL_OPTIONS)

        # Still connected
        assert await group.is_connected()

        await backend.disconnect()
        assert not await group.is_connected()
