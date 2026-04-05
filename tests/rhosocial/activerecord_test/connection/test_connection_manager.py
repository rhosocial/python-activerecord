# tests/rhosocial/activerecord_test/connection/test_connection_manager.py
"""
Tests for ConnectionManager and AsyncConnectionManager classes.
"""

import pytest

from rhosocial.activerecord.connection import ConnectionManager, AsyncConnectionManager
# Import models from local conftest using absolute path
from tests.rhosocial.activerecord_test.connection.conftest import (
    User, Post, Comment, AsyncUser, AsyncPost
)


class TestConnectionManager:
    """Tests for ConnectionManager class."""

    def test_create_manager(self):
        """Test creating a ConnectionManager."""
        manager = ConnectionManager()
        assert len(manager) == 0
        assert manager.get_group_names() == []

    def test_create_group(self, sqlite_config, backend_class):
        """Test creating a connection group through manager."""
        manager = ConnectionManager()
        group = manager.create_group(
            name="main",
            config=sqlite_config,
            backend_class=backend_class,
            models=[User, Post],
        )

        assert group is not None
        assert group.name == "main"
        assert len(manager) == 1
        assert "main" in manager
        assert manager.has_group("main")

    def test_create_duplicate_group_raises(self, sqlite_config, backend_class):
        """Test that creating duplicate group raises error."""
        manager = ConnectionManager()
        manager.create_group(
            name="main",
            config=sqlite_config,
            backend_class=backend_class,
            models=[User],
        )

        with pytest.raises(ValueError, match="already exists"):
            manager.create_group(
                name="main",
                config=sqlite_config,
                backend_class=backend_class,
                models=[User],
            )

    def test_get_group(self, sqlite_config, backend_class):
        """Test getting a connection group."""
        manager = ConnectionManager()
        manager.create_group(
            name="main",
            config=sqlite_config,
            backend_class=backend_class,
            models=[User],
        )

        group = manager.get_group("main")
        assert group is not None
        assert group.name == "main"

        # Non-existent group returns None
        assert manager.get_group("nonexistent") is None

    def test_remove_group(self, sqlite_config, backend_class):
        """Test removing a connection group."""
        manager = ConnectionManager()
        manager.create_group(
            name="main",
            config=sqlite_config,
            backend_class=backend_class,
            models=[User],
        )

        assert len(manager) == 1

        # Remove without disconnect (not configured)
        result = manager.remove_group("main", disconnect=True)
        assert result is True
        assert len(manager) == 0
        assert manager.get_group("main") is None

    def test_remove_configured_group(self, sqlite_config, backend_class):
        """Test removing a configured connection group."""
        manager = ConnectionManager()
        manager.create_group(
            name="main",
            config=sqlite_config,
            backend_class=backend_class,
            models=[User],
        )
        manager.configure_all()

        assert manager.get_group("main").is_configured()

        # Remove with disconnect
        result = manager.remove_group("main", disconnect=True)
        assert result is True
        assert len(manager) == 0

    def test_remove_nonexistent_group(self):
        """Test removing a non-existent group."""
        manager = ConnectionManager()
        result = manager.remove_group("nonexistent")
        assert result is False

    def test_configure_all(self, sqlite_config, backend_class):
        """Test configuring all groups."""
        manager = ConnectionManager()

        manager.create_group(
            name="main",
            config=sqlite_config,
            backend_class=backend_class,
            models=[User],
        )
        manager.create_group(
            name="stats",
            config=sqlite_config,
            backend_class=backend_class,
            models=[Post, Comment],
        )

        assert not manager.get_group("main").is_configured()
        assert not manager.get_group("stats").is_configured()

        manager.configure_all()

        assert manager.get_group("main").is_configured()
        assert manager.get_group("stats").is_configured()

        manager.disconnect_all()

    def test_disconnect_all(self, sqlite_config, backend_class):
        """Test disconnecting all groups."""
        manager = ConnectionManager()

        manager.create_group(
            name="main",
            config=sqlite_config,
            backend_class=backend_class,
            models=[User],
        )
        manager.create_group(
            name="stats",
            config=sqlite_config,
            backend_class=backend_class,
            models=[Post],
        )

        manager.configure_all()
        assert manager.get_group("main").is_configured()
        assert manager.get_group("stats").is_configured()

        manager.disconnect_all()
        assert not manager.get_group("main").is_configured()
        assert not manager.get_group("stats").is_configured()

    def test_is_connected(self, sqlite_config, backend_class):
        """Test is_connected method."""
        manager = ConnectionManager()

        # Empty manager is "connected" (vacuously true)
        assert manager.is_connected()

        manager.create_group(
            name="main",
            config=sqlite_config,
            backend_class=backend_class,
            models=[User],
        )
        manager.create_group(
            name="stats",
            config=sqlite_config,
            backend_class=backend_class,
            models=[Post],
        )

        # Not connected before configure
        assert not manager.is_connected()

        manager.configure_all()
        assert manager.is_connected()

        manager.disconnect_all()
        assert not manager.is_connected()

    def test_get_group_names(self, sqlite_config, backend_class):
        """Test get_group_names method."""
        manager = ConnectionManager()
        assert manager.get_group_names() == []

        manager.create_group(
            name="main",
            config=sqlite_config,
            backend_class=backend_class,
            models=[User],
        )
        assert manager.get_group_names() == ["main"]

        manager.create_group(
            name="stats",
            config=sqlite_config,
            backend_class=backend_class,
            models=[User],
        )
        names = manager.get_group_names()
        assert len(names) == 2
        assert "main" in names
        assert "stats" in names

    def test_context_manager(self, sqlite_config, backend_class):
        """Test using ConnectionManager as context manager."""
        manager = ConnectionManager()
        manager.create_group(
            name="main",
            config=sqlite_config,
            backend_class=backend_class,
            models=[User],
        )
        manager.create_group(
            name="stats",
            config=sqlite_config,
            backend_class=backend_class,
            models=[Post],
        )

        with manager:
            assert manager.get_group("main").is_configured()
            assert manager.get_group("stats").is_configured()
            assert manager.is_connected()

        # After context, all should be disconnected
        assert not manager.get_group("main").is_configured()
        assert not manager.get_group("stats").is_configured()

    def test_contains_operator(self, sqlite_config, backend_class):
        """Test __contains__ operator."""
        manager = ConnectionManager()

        assert "main" not in manager

        manager.create_group(
            name="main",
            config=sqlite_config,
            backend_class=backend_class,
            models=[User],
        )

        assert "main" in manager
        assert "stats" not in manager

    def test_len_operator(self, sqlite_config, backend_class):
        """Test __len__ operator."""
        manager = ConnectionManager()
        assert len(manager) == 0

        manager.create_group(
            name="main",
            config=sqlite_config,
            backend_class=backend_class,
            models=[User],
        )
        assert len(manager) == 1

        manager.create_group(
            name="stats",
            config=sqlite_config,
            backend_class=backend_class,
            models=[User],
        )
        assert len(manager) == 2


class TestAsyncConnectionManager:
    """Tests for AsyncConnectionManager class."""

    @pytest.mark.asyncio
    async def test_async_create_manager(self):
        """Test creating an AsyncConnectionManager."""
        manager = AsyncConnectionManager()
        assert len(manager) == 0

    @pytest.mark.asyncio
    async def test_async_create_group(self, sqlite_config, async_backend_class):
        """Test creating a connection group through async manager."""
        manager = AsyncConnectionManager()
        group = manager.create_group(
            name="main",
            config=sqlite_config,
            backend_class=async_backend_class,
            models=[AsyncUser],
        )

        assert group is not None
        assert group.name == "main"
        assert "main" in manager

    @pytest.mark.asyncio
    async def test_async_configure_all(self, sqlite_config, async_backend_class):
        """Test async configuring all groups."""
        manager = AsyncConnectionManager()

        manager.create_group(
            name="main",
            config=sqlite_config,
            backend_class=async_backend_class,
            models=[AsyncUser],
        )
        manager.create_group(
            name="stats",
            config=sqlite_config,
            backend_class=async_backend_class,
            models=[AsyncPost],
        )

        assert not manager.get_group("main").is_configured()

        await manager.configure_all()

        assert manager.get_group("main").is_configured()
        assert manager.get_group("stats").is_configured()

        await manager.disconnect_all()

    @pytest.mark.asyncio
    async def test_async_disconnect_all(self, sqlite_config, async_backend_class):
        """Test async disconnecting all groups."""
        manager = AsyncConnectionManager()

        manager.create_group(
            name="main",
            config=sqlite_config,
            backend_class=async_backend_class,
            models=[AsyncUser],
        )

        await manager.configure_all()
        assert manager.get_group("main").is_configured()

        await manager.disconnect_all()
        assert not manager.get_group("main").is_configured()

    @pytest.mark.asyncio
    async def test_async_is_connected(self, sqlite_config, async_backend_class):
        """Test async is_connected method."""
        manager = AsyncConnectionManager()

        manager.create_group(
            name="main",
            config=sqlite_config,
            backend_class=async_backend_class,
            models=[AsyncUser],
        )

        assert not await manager.is_connected()

        await manager.configure_all()
        assert await manager.is_connected()

        await manager.disconnect_all()
        assert not await manager.is_connected()

    @pytest.mark.asyncio
    async def test_async_remove_group(self, sqlite_config, async_backend_class):
        """Test async removing a connection group."""
        manager = AsyncConnectionManager()
        manager.create_group(
            name="main",
            config=sqlite_config,
            backend_class=async_backend_class,
            models=[AsyncUser],
        )

        await manager.configure_all()
        assert manager.get_group("main").is_configured()

        result = await manager.remove_group("main", disconnect=True)
        assert result is True
        assert len(manager) == 0

    @pytest.mark.asyncio
    async def test_async_context_manager(self, sqlite_config, async_backend_class):
        """Test using AsyncConnectionManager as async context manager."""
        manager = AsyncConnectionManager()
        manager.create_group(
            name="main",
            config=sqlite_config,
            backend_class=async_backend_class,
            models=[AsyncUser],
        )
        manager.create_group(
            name="stats",
            config=sqlite_config,
            backend_class=async_backend_class,
            models=[AsyncPost],
        )

        async with manager:
            assert manager.get_group("main").is_configured()
            assert manager.get_group("stats").is_configured()
            assert await manager.is_connected()

        # After context, all should be disconnected
        assert not manager.get_group("main").is_configured()
        assert not manager.get_group("stats").is_configured()
