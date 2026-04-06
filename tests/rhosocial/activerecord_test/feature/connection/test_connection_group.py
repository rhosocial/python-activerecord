# tests/rhosocial/activerecord_test/feature/connection/test_connection_group.py
"""
Tests for ConnectionGroup and AsyncConnectionGroup classes.
"""

import pytest

from rhosocial.activerecord.connection import ConnectionGroup, AsyncConnectionGroup
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
# Import models from local conftest using absolute path
from tests.rhosocial.activerecord_test.feature.connection.conftest import (
    User, Post, Comment, AsyncUser, AsyncPost
)


class TestConnectionGroup:
    """Tests for ConnectionGroup class."""

    def test_create_connection_group(self):
        """Test creating a ConnectionGroup with basic parameters."""
        group = ConnectionGroup(
            name="main",
            models=[],
        )
        assert group.name == "main"
        assert group.models == []
        assert group.config is None
        assert group.backend_class is None
        assert not group.is_configured()

    def test_create_connection_group_with_models(self):
        """Test creating a ConnectionGroup with models."""
        group = ConnectionGroup(
            name="main",
            models=[User, Post],
        )
        assert group.name == "main"
        assert len(group.models) == 2
        assert User in group.models
        assert Post in group.models

    def test_add_model(self):
        """Test adding models using add_model method."""
        group = ConnectionGroup(
            name="main",
            models=[User],
        )
        assert len(group.models) == 1

        # Test chaining
        result = group.add_model(Post).add_model(Comment)
        assert result is group  # Returns self
        assert len(group.models) == 3
        assert Post in group.models
        assert Comment in group.models

    def test_configure_success(self, sqlite_config, backend_class):
        """Test successful configuration of ConnectionGroup."""
        group = ConnectionGroup(
            name="main",
            models=[User, Post],
            config=sqlite_config,
            backend_class=backend_class,
        )

        assert not group.is_configured()
        group.configure()
        assert group.is_configured()

        # Verify shared backend is created
        backend = group.get_backend()
        assert backend is not None

        # Cleanup
        group.disconnect()

    def test_configure_without_config_raises(self):
        """Test that configure raises error when config is not set."""
        group = ConnectionGroup(
            name="main",
            models=[User],
            backend_class=SQLiteBackend,
        )

        with pytest.raises(ValueError, match="ConnectionConfig not set"):
            group.configure()

    def test_configure_without_backend_class_raises(self, sqlite_config):
        """Test that configure raises error when backend_class is not set."""
        group = ConnectionGroup(
            name="main",
            models=[User],
            config=sqlite_config,
        )

        with pytest.raises(ValueError, match="Backend class not set"):
            group.configure()

    def test_configure_idempotent(self, sqlite_config, backend_class):
        """Test that calling configure multiple times is safe."""
        group = ConnectionGroup(
            name="main",
            models=[User],
            config=sqlite_config,
            backend_class=backend_class,
        )

        group.configure()
        backend1 = group.get_backend()

        group.configure()  # Second call should be no-op
        backend2 = group.get_backend()

        # Same backend instance
        assert backend1 is backend2

        group.disconnect()

    def test_disconnect(self, sqlite_config, backend_class):
        """Test disconnect method."""
        group = ConnectionGroup(
            name="main",
            models=[User, Post],
            config=sqlite_config,
            backend_class=backend_class,
        )

        group.configure()
        assert group.is_configured()

        group.disconnect()
        assert not group.is_configured()
        assert group.get_backend() is None

    def test_disconnect_idempotent(self, sqlite_config, backend_class):
        """Test that calling disconnect multiple times is safe."""
        group = ConnectionGroup(
            name="main",
            models=[User],
            config=sqlite_config,
            backend_class=backend_class,
        )

        group.configure()
        group.disconnect()
        group.disconnect()  # Second call should not raise

    def test_disconnect_without_configure(self):
        """Test that disconnect without configure is safe."""
        group = ConnectionGroup(
            name="main",
            models=[User],
        )
        group.disconnect()  # Should not raise

    def test_is_connected(self, sqlite_config, backend_class):
        """Test is_connected method."""
        group = ConnectionGroup(
            name="main",
            models=[User, Post],
            config=sqlite_config,
            backend_class=backend_class,
        )

        # Not connected before configure
        assert not group.is_connected()

        group.configure()
        assert group.is_connected()

        group.disconnect()
        assert not group.is_connected()

    def test_ping(self, sqlite_config, backend_class):
        """Test ping method returns connection status."""
        group = ConnectionGroup(
            name="main",
            models=[User, Post],
            config=sqlite_config,
            backend_class=backend_class,
        )

        group.configure()
        status = group.ping()

        assert status is True

        group.disconnect()

    def test_context_manager(self, sqlite_config, backend_class):
        """Test using ConnectionGroup as context manager."""
        with ConnectionGroup(
            name="main",
            models=[User],
            config=sqlite_config,
            backend_class=backend_class,
        ) as group:
            assert group.is_configured()
            assert group.is_connected()

        # After context, should be disconnected
        assert not group.is_configured()

    def test_add_model_after_configure_raises(self, sqlite_config, backend_class):
        """Test that adding model after configure raises error."""
        group = ConnectionGroup(
            name="main",
            models=[User],
            config=sqlite_config,
            backend_class=backend_class,
        )

        group.configure()

        with pytest.raises(RuntimeError, match="Cannot add model to configured"):
            group.add_model(Post)

        group.disconnect()

    def test_get_backend_before_configure(self):
        """Test get_backend returns None before configuration."""
        group = ConnectionGroup(
            name="main",
            models=[User],
        )

        assert group.get_backend() is None

    def test_ping_before_configure(self):
        """Test ping returns False before configuration."""
        group = ConnectionGroup(
            name="main",
            models=[User],
        )

        status = group.ping()
        assert status is False


class TestAsyncConnectionGroup:
    """Tests for AsyncConnectionGroup class."""

    @pytest.mark.asyncio
    async def test_async_create_connection_group(self):
        """Test creating an AsyncConnectionGroup."""
        group = AsyncConnectionGroup(
            name="main",
            models=[],
        )
        assert group.name == "main"
        assert not group.is_configured()

    @pytest.mark.asyncio
    async def test_async_configure_success(self, sqlite_config, async_backend_class):
        """Test successful async configuration."""
        group = AsyncConnectionGroup(
            name="main",
            models=[AsyncUser, AsyncPost],
            config=sqlite_config,
            backend_class=async_backend_class,
        )

        assert not group.is_configured()
        await group.configure()
        assert group.is_configured()

        await group.disconnect()

    @pytest.mark.asyncio
    async def test_async_disconnect(self, sqlite_config, async_backend_class):
        """Test async disconnect method."""
        group = AsyncConnectionGroup(
            name="main",
            models=[AsyncUser],
            config=sqlite_config,
            backend_class=async_backend_class,
        )

        await group.configure()
        assert group.is_configured()

        await group.disconnect()
        assert not group.is_configured()

    @pytest.mark.asyncio
    async def test_async_is_connected(self, sqlite_config, async_backend_class):
        """Test async is_connected method."""
        group = AsyncConnectionGroup(
            name="main",
            models=[AsyncUser],
            config=sqlite_config,
            backend_class=async_backend_class,
        )

        assert not await group.is_connected()

        await group.configure()
        assert await group.is_connected()

        await group.disconnect()
        assert not await group.is_connected()

    @pytest.mark.asyncio
    async def test_async_ping(self, sqlite_config, async_backend_class):
        """Test async ping method."""
        group = AsyncConnectionGroup(
            name="main",
            models=[AsyncUser, AsyncPost],
            config=sqlite_config,
            backend_class=async_backend_class,
        )

        await group.configure()
        status = await group.ping()

        assert status is True

        await group.disconnect()

    @pytest.mark.asyncio
    async def test_async_context_manager(self, sqlite_config, async_backend_class):
        """Test using AsyncConnectionGroup as async context manager."""
        async with AsyncConnectionGroup(
            name="main",
            models=[AsyncUser],
            config=sqlite_config,
            backend_class=async_backend_class,
        ) as group:
            assert group.is_configured()
            assert await group.is_connected()

        # After context, should be disconnected
        assert not group.is_configured()
