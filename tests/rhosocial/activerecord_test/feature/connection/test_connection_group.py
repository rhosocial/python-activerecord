# tests/rhosocial/activerecord_test/feature/connection/test_connection_group.py
"""
Tests for BackendGroup and AsyncBackendGroup classes.

Tests the context-based lifecycle: configure() prepares backends without
connecting, and users manage connections via backend.context() or
manual connect()/disconnect() calls.
"""

import pytest

from rhosocial.activerecord.connection import BackendGroup, AsyncBackendGroup
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
# Import models from local conftest using absolute path
from tests.rhosocial.activerecord_test.feature.connection.conftest import (
    User, Post, Comment, AsyncUser, AsyncPost
)


class TestBackendGroup:
    """Tests for BackendGroup class."""

    def test_create_backend_group(self):
        """Test creating a BackendGroup with basic parameters."""
        group = BackendGroup(
            name="main",
            models=[],
        )
        assert group.name == "main"
        assert group.models == []
        assert group.config is None
        assert group.backend_class is None
        assert not group.is_configured()

    def test_create_backend_group_with_models(self):
        """Test creating a BackendGroup with models."""
        group = BackendGroup(
            name="main",
            models=[User, Post],
        )
        assert group.name == "main"
        assert len(group.models) == 2
        assert User in group.models
        assert Post in group.models

    def test_add_model(self):
        """Test adding models using add_model method."""
        group = BackendGroup(
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
        """Test successful configuration of BackendGroup."""
        group = BackendGroup(
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

        # Configure does NOT connect
        assert not group.is_connected()

        # Cleanup
        group.disconnect()

    def test_configure_without_config_raises(self):
        """Test that configure raises error when config is not set."""
        group = BackendGroup(
            name="main",
            models=[User],
            backend_class=SQLiteBackend,
        )

        with pytest.raises(ValueError, match="ConnectionConfig not set"):
            group.configure()

    def test_configure_without_backend_class_raises(self, sqlite_config):
        """Test that configure raises error when backend_class is not set."""
        group = BackendGroup(
            name="main",
            models=[User],
            config=sqlite_config,
        )

        with pytest.raises(ValueError, match="Backend class not set"):
            group.configure()

    def test_configure_idempotent(self, sqlite_config, backend_class):
        """Test that calling configure multiple times is safe."""
        group = BackendGroup(
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
        group = BackendGroup(
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
        group = BackendGroup(
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
        group = BackendGroup(
            name="main",
            models=[User],
        )
        group.disconnect()  # Should not raise

    def test_is_connected_after_configure(self, sqlite_config, backend_class):
        """Test is_connected returns False after configure (no persistent connection)."""
        group = BackendGroup(
            name="main",
            models=[User, Post],
            config=sqlite_config,
            backend_class=backend_class,
        )

        # Not connected before configure
        assert not group.is_connected()

        group.configure()
        # Still not connected after configure (context-based lifecycle)
        assert not group.is_connected()

        group.disconnect()
        assert not group.is_connected()

    def test_is_connected_inside_backend_context(self, sqlite_config, backend_class):
        """Test is_connected returns True inside backend.context() block."""
        group = BackendGroup(
            name="main",
            models=[User, Post],
            config=sqlite_config,
            backend_class=backend_class,
        )

        group.configure()
        assert not group.is_connected()

        with group.get_backend().context():
            assert group.is_connected()

        # After context exit, not connected again
        assert not group.is_connected()

        group.disconnect()

    def test_is_connected_manual_connect(self, sqlite_config, backend_class):
        """Test is_connected returns True after manual connect()."""
        group = BackendGroup(
            name="main",
            models=[User, Post],
            config=sqlite_config,
            backend_class=backend_class,
        )

        group.configure()
        assert not group.is_connected()

        # Manual connect
        group.get_backend().connect()
        group.get_backend().introspect_and_adapt()
        assert group.is_connected()

        # Manual disconnect
        group.get_backend().disconnect()
        assert not group.is_connected()

        group.disconnect()

    def test_ping_after_configure(self, sqlite_config, backend_class):
        """Test ping returns False after configure (no persistent connection)."""
        group = BackendGroup(
            name="main",
            models=[User, Post],
            config=sqlite_config,
            backend_class=backend_class,
        )

        group.configure()
        assert group.ping() is False

        group.disconnect()

    def test_context_manager_pattern(self, sqlite_config, backend_class):
        """Test using BackendGroup as context manager."""
        with BackendGroup(
            name="main",
            models=[User],
            config=sqlite_config,
            backend_class=backend_class,
        ) as group:
            assert group.is_configured()
            # Not connected yet - user manages connections
            assert not group.is_connected()

            with group.get_backend().context():
                assert group.is_connected()

        # After context, should be cleaned up
        assert not group.is_configured()

    def test_add_model_after_configure_raises(self, sqlite_config, backend_class):
        """Test that adding model after configure raises error."""
        group = BackendGroup(
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
        group = BackendGroup(
            name="main",
            models=[User],
        )

        assert group.get_backend() is None

    def test_ping_before_configure(self):
        """Test ping returns False before configuration."""
        group = BackendGroup(
            name="main",
            models=[User],
        )

        status = group.ping()
        assert status is False

    def test_disconnect_clears_model_backends(self, sqlite_config, backend_class):
        """Test that disconnect clears model __backend__ references."""
        group = BackendGroup(
            name="main",
            models=[User],
            config=sqlite_config,
            backend_class=backend_class,
        )
        group.configure()
        assert User.__backend__ is not None

        group.disconnect()
        assert User.__backend__ is None

    def test_backend_context_multiple_cycles(self, sqlite_config, backend_class):
        """Test multiple backend.context() cycles within same group."""
        group = BackendGroup(
            name="main",
            models=[User],
            config=sqlite_config,
            backend_class=backend_class,
        )
        group.configure()

        # First context
        with group.get_backend().context():
            assert group.is_connected()
        assert not group.is_connected()

        # Second context
        with group.get_backend().context():
            assert group.is_connected()
        assert not group.is_connected()

        group.disconnect()


class TestAsyncBackendGroup:
    """Tests for AsyncBackendGroup class."""

    @pytest.mark.asyncio
    async def test_async_create_backend_group(self):
        """Test creating an AsyncBackendGroup."""
        group = AsyncBackendGroup(
            name="main",
            models=[],
        )
        assert group.name == "main"
        assert not group.is_configured()

    @pytest.mark.asyncio
    async def test_async_configure_success(self, sqlite_config, async_backend_class):
        """Test successful async configuration (without connecting)."""
        group = AsyncBackendGroup(
            name="main",
            models=[AsyncUser, AsyncPost],
            config=sqlite_config,
            backend_class=async_backend_class,
        )

        assert not group.is_configured()
        await group.configure()
        assert group.is_configured()
        # Not connected after configure
        assert not await group.is_connected()

        await group.disconnect()

    @pytest.mark.asyncio
    async def test_async_disconnect(self, sqlite_config, async_backend_class):
        """Test async disconnect method."""
        group = AsyncBackendGroup(
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
    async def test_async_is_connected_after_configure(self, sqlite_config, async_backend_class):
        """Test async is_connected returns False after configure."""
        group = AsyncBackendGroup(
            name="main",
            models=[AsyncUser],
            config=sqlite_config,
            backend_class=async_backend_class,
        )

        assert not await group.is_connected()

        await group.configure()
        # Not connected after configure (context-based lifecycle)
        assert not await group.is_connected()

        await group.disconnect()
        assert not await group.is_connected()

    @pytest.mark.asyncio
    async def test_async_is_connected_inside_backend_context(self, sqlite_config, async_backend_class):
        """Test async is_connected returns True inside backend.context() block."""
        group = AsyncBackendGroup(
            name="main",
            models=[AsyncUser],
            config=sqlite_config,
            backend_class=async_backend_class,
        )

        await group.configure()
        assert not await group.is_connected()

        async with group.get_backend().context():
            assert await group.is_connected()

        assert not await group.is_connected()

        await group.disconnect()

    @pytest.mark.asyncio
    async def test_async_ping(self, sqlite_config, async_backend_class):
        """Test async ping method."""
        group = AsyncBackendGroup(
            name="main",
            models=[AsyncUser, AsyncPost],
            config=sqlite_config,
            backend_class=async_backend_class,
        )

        await group.configure()
        assert await group.ping() is False

        await group.disconnect()

    @pytest.mark.asyncio
    async def test_async_context_manager(self, sqlite_config, async_backend_class):
        """Test using AsyncBackendGroup as async context manager."""
        async with AsyncBackendGroup(
            name="main",
            models=[AsyncUser],
            config=sqlite_config,
            backend_class=async_backend_class,
        ) as group:
            assert group.is_configured()
            # Not connected - user manages connections
            assert not await group.is_connected()

            async with group.get_backend().context():
                assert await group.is_connected()

        # After context, should be cleaned up
        assert not group.is_configured()

    @pytest.mark.asyncio
    async def test_async_backend_context_multiple_cycles(self, sqlite_config, async_backend_class):
        """Test multiple async backend.context() cycles."""
        group = AsyncBackendGroup(
            name="main",
            models=[AsyncUser],
            config=sqlite_config,
            backend_class=async_backend_class,
        )
        await group.configure()

        for _ in range(3):
            async with group.get_backend().context():
                assert await group.is_connected()
            assert not await group.is_connected()

        await group.disconnect()
