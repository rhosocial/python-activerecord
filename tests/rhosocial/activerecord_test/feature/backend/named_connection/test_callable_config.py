# tests/rhosocial/activerecord_test/feature/backend/named_connection/test_callable_config.py
"""
Tests for callable config support in configure(), BackendGroup, and BackendManager.

Verifies that ConnectionConfig callables (e.g., named connection functions)
can be passed directly as the config argument.
"""

import pytest
from typing import Optional
from unittest.mock import MagicMock, patch

from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.backend.async_backend import AsyncSQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import (
    SQLiteConnectionConfig,
    SQLiteInMemoryConfig,
)
from rhosocial.activerecord.backend.errors import DatabaseError
from rhosocial.activerecord.connection import BackendGroup, AsyncBackendGroup
from rhosocial.activerecord.connection.manager import BackendManager, AsyncBackendManager


# ============================================================
# Test Models
# ============================================================

class CallableUser(IntegerPKMixin, ActiveRecord):
    """Test User model for callable config tests."""
    __table_name__ = 'callable_users'

    id: Optional[int] = None
    name: str


class AsyncCallableUser(IntegerPKMixin, AsyncActiveRecord):
    """Test async User model for callable config tests."""
    __table_name__ = 'callable_users'

    id: Optional[int] = None
    name: str


# ============================================================
# Callable config fixtures
# ============================================================

def memory_config():
    """A simple callable returning in-memory SQLite config."""
    return SQLiteInMemoryConfig()


def file_config_with_suffix(suffix: str = ".sqlite"):
    """A callable returning file-based SQLite config with a suffix parameter."""
    import tempfile
    import os
    fd, db_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    return SQLiteConnectionConfig(database=db_path, delete_on_close=True)


class ConfigFactory:
    """A callable class returning SQLite config."""
    def __call__(self):
        return SQLiteInMemoryConfig()


# ============================================================
# configure() tests - sync
# ============================================================

class TestConfigureWithCallable:
    """Tests for BaseActiveRecord.configure() with callable config."""

    def test_configure_with_function(self):
        """configure() accepts a function returning ConnectionConfig."""
        CallableUser.configure(memory_config, SQLiteBackend)
        assert isinstance(CallableUser.__connection_config__, SQLiteConnectionConfig)
        assert CallableUser.__backend_class__ is SQLiteBackend
        assert CallableUser.__backend__ is not None

    def test_configure_with_lambda(self):
        """configure() accepts a lambda returning ConnectionConfig."""
        CallableUser.configure(lambda: SQLiteInMemoryConfig(), SQLiteBackend)
        assert isinstance(CallableUser.__connection_config__, SQLiteConnectionConfig)

    def test_configure_with_callable_instance(self):
        """configure() accepts a callable class instance."""
        factory = ConfigFactory()
        CallableUser.configure(factory, SQLiteBackend)
        assert isinstance(CallableUser.__connection_config__, SQLiteConnectionConfig)

    def test_configure_with_partial(self):
        """configure() accepts functools.partial for parameterized callables."""
        from functools import partial
        CallableUser.configure(partial(file_config_with_suffix, suffix=".test"), SQLiteBackend)
        assert isinstance(CallableUser.__connection_config__, SQLiteConnectionConfig)

    def test_configure_with_instance_still_works(self):
        """configure() still accepts ConnectionConfig instance directly."""
        config = SQLiteInMemoryConfig()
        CallableUser.configure(config, SQLiteBackend)
        assert CallableUser.__connection_config__ is config

    def test_configure_with_invalid_callable(self):
        """configure() raises DatabaseError when callable returns non-ConnectionConfig."""
        with pytest.raises(DatabaseError, match="Invalid connection config"):
            CallableUser.configure(lambda: "not_a_config", SQLiteBackend)

    def test_configure_with_non_callable_non_config(self):
        """configure() raises DatabaseError when passed neither callable nor config."""
        with pytest.raises(DatabaseError, match="Invalid connection config"):
            CallableUser.configure("just_a_string", SQLiteBackend)


# ============================================================
# configure() tests - async
# ============================================================

class TestAsyncConfigureWithCallable:
    """Tests for AsyncBaseActiveRecord.configure() with callable config."""

    @pytest.mark.asyncio
    async def test_async_configure_with_function(self):
        """Async configure() accepts a function returning ConnectionConfig."""
        await AsyncCallableUser.configure(memory_config, AsyncSQLiteBackend)
        assert isinstance(AsyncCallableUser.__connection_config__, SQLiteConnectionConfig)
        assert AsyncCallableUser.__backend_class__ is AsyncSQLiteBackend

    @pytest.mark.asyncio
    async def test_async_configure_with_lambda(self):
        """Async configure() accepts a lambda returning ConnectionConfig."""
        await AsyncCallableUser.configure(lambda: SQLiteInMemoryConfig(), AsyncSQLiteBackend)
        assert isinstance(AsyncCallableUser.__connection_config__, SQLiteConnectionConfig)

    @pytest.mark.asyncio
    async def test_async_configure_with_instance_still_works(self):
        """Async configure() still accepts ConnectionConfig instance directly."""
        config = SQLiteInMemoryConfig()
        await AsyncCallableUser.configure(config, AsyncSQLiteBackend)
        assert AsyncCallableUser.__connection_config__ is config

    @pytest.mark.asyncio
    async def test_async_configure_with_invalid_callable(self):
        """Async configure() raises DatabaseError when callable returns non-ConnectionConfig."""
        with pytest.raises(DatabaseError, match="Invalid connection config"):
            await AsyncCallableUser.configure(lambda: 42, AsyncSQLiteBackend)


# ============================================================
# BackendGroup tests - sync
# ============================================================

class TestBackendGroupWithCallable:
    """Tests for BackendGroup with callable config."""

    def test_group_with_function_config(self):
        """BackendGroup accepts a function as config."""
        group = BackendGroup(
            name="test",
            models=[CallableUser],
            config=memory_config,
            backend_class=SQLiteBackend,
        )
        group.configure()
        assert group.is_configured()
        assert isinstance(CallableUser.__connection_config__, SQLiteConnectionConfig)

    def test_group_with_instance_config_still_works(self):
        """BackendGroup still accepts ConnectionConfig instance directly."""
        config = SQLiteInMemoryConfig()
        group = BackendGroup(
            name="test",
            models=[CallableUser],
            config=config,
            backend_class=SQLiteBackend,
        )
        group.configure()
        assert group.is_configured()
        assert CallableUser.__connection_config__ is config


# ============================================================
# BackendGroup tests - async
# ============================================================

class TestAsyncBackendGroupWithCallable:
    """Tests for AsyncBackendGroup with callable config."""

    @pytest.mark.asyncio
    async def test_async_group_with_function_config(self):
        """AsyncBackendGroup accepts a function as config."""
        group = AsyncBackendGroup(
            name="test",
            models=[AsyncCallableUser],
            config=memory_config,
            backend_class=AsyncSQLiteBackend,
        )
        await group.configure()
        assert group.is_configured()
        assert isinstance(AsyncCallableUser.__connection_config__, SQLiteConnectionConfig)


# ============================================================
# BackendManager tests
# ============================================================

class TestBackendManagerWithCallable:
    """Tests for BackendManager.create_group() with callable config."""

    def test_manager_create_group_with_callable(self):
        """BackendManager.create_group() accepts callable config."""
        manager = BackendManager()
        group = manager.create_group(
            name="test",
            config=memory_config,
            backend_class=SQLiteBackend,
            models=[CallableUser],
        )
        manager.configure_all()
        assert manager.is_connected() or group.is_configured()
        assert isinstance(CallableUser.__connection_config__, SQLiteConnectionConfig)

    def test_manager_create_group_with_instance(self):
        """BackendManager.create_group() still accepts ConnectionConfig instance."""
        config = SQLiteInMemoryConfig()
        manager = BackendManager()
        manager.create_group(
            name="test",
            config=config,
            backend_class=SQLiteBackend,
            models=[CallableUser],
        )
        manager.configure_all()
        assert CallableUser.__connection_config__ is config


class TestAsyncBackendManagerWithCallable:
    """Tests for AsyncBackendManager.create_group() with callable config."""

    @pytest.mark.asyncio
    async def test_async_manager_create_group_with_callable(self):
        """AsyncBackendManager.create_group() accepts callable config."""
        manager = AsyncBackendManager()
        manager.create_group(
            name="test",
            config=memory_config,
            backend_class=AsyncSQLiteBackend,
            models=[AsyncCallableUser],
        )
        await manager.configure_all()
        assert isinstance(AsyncCallableUser.__connection_config__, SQLiteConnectionConfig)
