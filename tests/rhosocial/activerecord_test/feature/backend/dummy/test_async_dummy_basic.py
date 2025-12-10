"""
Test to verify that AsyncDummyBackend can be imported and instantiated without errors.
This test verifies that the async backend implementation is properly structured.
"""
import pytest
from rhosocial.activerecord.backend.impl.dummy.async_backend import AsyncDummyBackend
from rhosocial.activerecord.backend.config import ConnectionConfig


def test_async_dummy_backend_import_and_instantiation():
    """Test that AsyncDummyBackend can be imported and instantiated."""
    backend = AsyncDummyBackend()
    assert backend is not None
    assert hasattr(backend, 'dialect')


def test_async_dummy_backend_with_connection_config():
    """Test that AsyncDummyBackend works with a connection config."""
    config = ConnectionConfig()
    backend = AsyncDummyBackend(connection_config=config)
    assert backend is not None


@pytest.mark.asyncio
async def test_async_dummy_backend_server_version():
    """Test that AsyncDummyBackend can return a server version."""
    backend = AsyncDummyBackend()
    version = await backend.get_server_version()
    assert isinstance(version, tuple)
    assert len(version) == 3
    assert version == (0, 0, 0)  # Expected dummy version


@pytest.mark.asyncio
async def test_async_dummy_backend_raises_not_implemented_error():
    """Test that async operations raise NotImplementedError."""
    backend = AsyncDummyBackend()
    
    expected_message = "AsyncDummyBackend does not support real database operations. Did you forget to configure a concrete backend?"
    
    # Test connect
    with pytest.raises(NotImplementedError) as exc_info:
        await backend.connect()
    assert expected_message in str(exc_info.value)
    
    # Test ping
    with pytest.raises(NotImplementedError) as exc_info:
        await backend.ping()
    assert expected_message in str(exc_info.value)
    
    # Test _get_cursor (though in practice this would be an internal call)
    with pytest.raises(NotImplementedError) as exc_info:
        await backend._get_cursor()
    assert expected_message in str(exc_info.value)