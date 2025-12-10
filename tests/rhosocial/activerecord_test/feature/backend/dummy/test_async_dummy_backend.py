# tests/rhosocial/activerecord_test/feature/backend/dummy/test_async_dummy_backend.py
import pytest
from rhosocial.activerecord.backend.impl.dummy.async_backend import AsyncDummyBackend
from rhosocial.activerecord.backend.config import ConnectionConfig
from rhosocial.activerecord.backend.errors import QueryError, RecordNotFound, DatabaseError


@pytest.fixture
def async_dummy_backend_instance():
    """Provides an AsyncDummyBackend instance for testing I/O operations."""
    return AsyncDummyBackend()


def get_expected_error_message():
    """Helper to get the consistent expected error message."""
    return "AsyncDummyBackend does not support real database operations. Did you forget to configure a concrete backend?"


@pytest.mark.asyncio
async def test_async_dummy_backend_connect_raises_not_implemented_error(async_dummy_backend_instance):
    """Test that connect() on AsyncDummyBackend raises NotImplementedError."""
    with pytest.raises(NotImplementedError) as excinfo:
        await async_dummy_backend_instance.connect()
    assert get_expected_error_message() in str(excinfo.value)


@pytest.mark.asyncio
async def test_async_dummy_backend_ping_raises_not_implemented_error(async_dummy_backend_instance):
    """Test that ping() on AsyncDummyBackend raises NotImplementedError."""
    with pytest.raises(NotImplementedError) as excinfo:
        await async_dummy_backend_instance.ping()
    assert get_expected_error_message() in str(excinfo.value)


@pytest.mark.asyncio
async def test_async_dummy_backend_get_cursor_raises_not_implemented_error(async_dummy_backend_instance):
    """Test that _get_cursor() on AsyncDummyBackend raises NotImplementedError."""
    with pytest.raises(NotImplementedError) as excinfo:
        await async_dummy_backend_instance._get_cursor()
    assert get_expected_error_message() in str(excinfo.value)


@pytest.mark.asyncio
async def test_async_dummy_backend_execute_query_raises_not_implemented_error(async_dummy_backend_instance):
    """Test that _execute_query() on AsyncDummyBackend raises NotImplementedError."""
    with pytest.raises(NotImplementedError) as excinfo:
        await async_dummy_backend_instance._execute_query(None, "SELECT 1", None)  # Cursor is None as it's dummy
    assert get_expected_error_message() in str(excinfo.value)


@pytest.mark.asyncio
async def test_async_dummy_backend_transaction_manager_raises_not_implemented_error(async_dummy_backend_instance):
    """Test that transaction_manager property on AsyncDummyBackend raises NotImplementedError."""
    with pytest.raises(NotImplementedError) as excinfo:
        _ = async_dummy_backend_instance.transaction_manager
    assert get_expected_error_message() in str(excinfo.value)


@pytest.mark.asyncio
async def test_async_dummy_backend_execute_raises_not_implemented_error(async_dummy_backend_instance):
    """Test that execute() on AsyncDummyBackend (via AsyncStorageBackend base) raises NotImplementedError."""
    with pytest.raises(NotImplementedError) as excinfo:
        await async_dummy_backend_instance.execute("SELECT 1", None)
    assert get_expected_error_message() in str(excinfo.value)


@pytest.mark.asyncio
async def test_async_dummy_backend_execute_many_raises_not_implemented_error(async_dummy_backend_instance):
    """Test that execute_many() on AsyncDummyBackend (via AsyncStorageBackend base) raises NotImplementedError."""
    with pytest.raises(NotImplementedError) as excinfo:
        await async_dummy_backend_instance.execute_many("INSERT INTO users VALUES (?)", [("name1",), ("name2",)])
    assert get_expected_error_message() in str(excinfo.value)


@pytest.mark.asyncio
async def test_async_dummy_backend_fetch_one_raises_not_implemented_error(async_dummy_backend_instance):
    """Test that fetch_one() on AsyncDummyBackend (via AsyncStorageBackend base) raises NotImplementedError."""
    with pytest.raises(NotImplementedError) as excinfo:
        await async_dummy_backend_instance.fetch_one("SELECT 1", None)
    assert get_expected_error_message() in str(excinfo.value)


@pytest.mark.asyncio
async def test_async_dummy_backend_fetch_all_raises_not_implemented_error(async_dummy_backend_instance):
    """Test that fetch_all() on AsyncDummyBackend (via AsyncStorageBackend base) raises NotImplementedError."""
    with pytest.raises(NotImplementedError) as excinfo:
        await async_dummy_backend_instance.fetch_all("SELECT 1", None)
    assert get_expected_error_message() in str(excinfo.value)


@pytest.mark.asyncio
async def test_async_dummy_backend_dialect_returns_dummy_dialect(async_dummy_backend_instance):
    """Test that the dialect property returns a DummyDialect instance."""
    from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
    dialect = async_dummy_backend_instance.dialect
    assert isinstance(dialect, DummyDialect)


@pytest.mark.asyncio
async def test_async_dummy_backend_server_version_returns_tuple(async_dummy_backend_instance):
    """Test that get_server_version returns a version tuple."""
    version = await async_dummy_backend_instance.get_server_version()
    assert isinstance(version, tuple)
    assert len(version) == 3
    assert version == (0, 0, 0)  # Dummy version