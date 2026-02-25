"""
Basic functionality tests for DummyBackend.
These tests verify that the dummy backend can be properly configured
and raises appropriate errors for unsupported operations.
"""
import pytest
from rhosocial.activerecord.backend.impl.dummy.backend import DummyBackend
from rhosocial.activerecord.backend.config import ConnectionConfig


def test_dummy_backend_creation():
    """Test that DummyBackend can be instantiated."""
    backend = DummyBackend()
    assert backend is not None
    assert hasattr(backend, 'dialect')


def test_dummy_backend_with_connection_config():
    """Test that DummyBackend works with a connection config."""
    config = ConnectionConfig()
    backend = DummyBackend(connection_config=config)
    assert backend is not None


def test_dummy_backend_dialect_property():
    """Test that DummyBackend has a dialect property."""
    backend = DummyBackend()
    from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
    assert isinstance(backend.dialect, DummyDialect)


def test_dummy_backend_has_required_attributes():
    """Test that DummyBackend has required attributes."""
    backend = DummyBackend()
    # Check that backend has dialect property
    assert hasattr(backend, 'dialect')
    # Check that backend can access dialect
    assert backend.dialect is not None


def test_dummy_backend_connect_raises_error():
    """Test that connect() on DummyBackend raises NotImplementedError."""
    backend = DummyBackend()
    expected_message = "DummyBackend does not support real database operations. Did you forget to configure a concrete backend?"
    
    with pytest.raises(NotImplementedError) as excinfo:
        backend.connect()
    assert expected_message in str(excinfo.value)


def test_dummy_backend_ping_raises_error():
    """Test that ping() on DummyBackend raises NotImplementedError."""
    backend = DummyBackend()
    expected_message = "DummyBackend does not support real database operations. Did you forget to configure a concrete backend?"
    
    with pytest.raises(NotImplementedError) as excinfo:
        backend.ping()
    assert expected_message in str(excinfo.value)


def test_dummy_backend_server_version():
    """Test that get_server_version returns a dummy version."""
    backend = DummyBackend()
    version = backend.get_server_version()
    assert isinstance(version, tuple)
    assert len(version) == 3
    assert version == (0, 0, 0)  # Dummy version


def test_dummy_backend_transaction_manager_raises_error():
    """Test that transaction_manager property on DummyBackend raises NotImplementedError."""
    backend = DummyBackend()
    expected_message = "DummyBackend does not support real database operations. Did you forget to configure a concrete backend?"
    
    with pytest.raises(NotImplementedError) as excinfo:
        _ = backend.transaction_manager
    assert expected_message in str(excinfo.value)