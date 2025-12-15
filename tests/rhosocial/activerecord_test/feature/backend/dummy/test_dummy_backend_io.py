# tests/rhosocial/activerecord_test/feature/backend/dummy/test_dummy_backend_io.py
import pytest
from rhosocial.activerecord.backend.impl.dummy.backend import DummyBackend
from rhosocial.activerecord.backend.config import ConnectionConfig
from rhosocial.activerecord.backend.errors import QueryError, RecordNotFound, DatabaseError
from rhosocial.activerecord.model import ActiveRecord
from pydantic import Field
from typing import ClassVar, Optional
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


class UserModel(ActiveRecord):
    __table_name__: ClassVar[str] = "users"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str


@pytest.fixture
def dummy_backend_instance():
    """Provides a DummyBackend instance for testing I/O operations."""
    return DummyBackend()


@pytest.fixture
def unconfigured_user_model_for_io():
    """Provides a UserModel configured with DummyBackend for I/O testing."""
    backend = DummyBackend()
    UserModel.configure(ConnectionConfig(), DummyBackend)
    yield UserModel
    # Clean up after test
    UserModel.__backend__ = None
    UserModel.__backend_class__ = None
    UserModel.__connection_config__ = None


def get_expected_error_message():
    """Helper to get the consistent expected error message."""
    return "DummyBackend does not support real database operations. Did you forget to configure a concrete backend?"


def test_dummy_backend_connect_raises_not_implemented_error(dummy_backend_instance):
    """Test that connect() on DummyBackend raises NotImplementedError."""
    with pytest.raises(NotImplementedError) as excinfo:
        dummy_backend_instance.connect()
    assert get_expected_error_message() in str(excinfo.value)


def test_dummy_backend_ping_raises_not_implemented_error(dummy_backend_instance):
    """Test that ping() on DummyBackend raises NotImplementedError."""
    with pytest.raises(NotImplementedError) as excinfo:
        dummy_backend_instance.ping()
    assert get_expected_error_message() in str(excinfo.value)


def test_dummy_backend_get_cursor_raises_not_implemented_error(dummy_backend_instance):
    """Test that _get_cursor() on DummyBackend raises NotImplementedError."""
    with pytest.raises(NotImplementedError) as excinfo:
        dummy_backend_instance._get_cursor()
    assert get_expected_error_message() in str(excinfo.value)


def test_dummy_backend_execute_query_raises_not_implemented_error(dummy_backend_instance):
    """Test that _execute_query() on DummyBackend raises NotImplementedError."""
    with pytest.raises(NotImplementedError) as excinfo:
        dummy_backend_instance._execute_query(None, "SELECT 1", None)  # Cursor is None as it's dummy
    assert get_expected_error_message() in str(excinfo.value)


def test_dummy_backend_transaction_manager_raises_not_implemented_error(dummy_backend_instance):
    """Test that transaction_manager property on DummyBackend raises NotImplementedError."""
    with pytest.raises(NotImplementedError) as excinfo:
        _ = dummy_backend_instance.transaction_manager
    assert get_expected_error_message() in str(excinfo.value)


def test_dummy_backend_execute_raises_not_implemented_error(dummy_backend_instance):
    """Test that execute() on DummyBackend (via StorageBackend base) raises NotImplementedError."""
    options = ExecutionOptions(stmt_type=StatementType.DQL) # No sql, params here
    with pytest.raises(NotImplementedError) as excinfo:
        dummy_backend_instance.execute("SELECT 1", None, options=options) # Pass sql, params positionally
    assert get_expected_error_message() in str(excinfo.value)


def test_dummy_backend_execute_many_raises_not_implemented_error(dummy_backend_instance):
    """Test that execute_many() on DummyBackend (via StorageBackend base) raises NotImplementedError."""
    with pytest.raises(NotImplementedError) as excinfo:
        dummy_backend_instance.execute_many("INSERT INTO users VALUES (?)", [("name1",), ("name2",)])
    assert get_expected_error_message() in str(excinfo.value)


def test_dummy_backend_fetch_one_raises_not_implemented_error(dummy_backend_instance):
    """Test that fetch_one() on DummyBackend (via StorageBackend base) raises NotImplementedError."""
    with pytest.raises(NotImplementedError) as excinfo:
        dummy_backend_instance.fetch_one("SELECT 1", None)
    assert get_expected_error_message() in str(excinfo.value)


def test_dummy_backend_fetch_all_raises_not_implemented_error(dummy_backend_instance):
    """Test that fetch_all() on DummyBackend (via StorageBackend base) raises NotImplementedError."""
    with pytest.raises(NotImplementedError) as excinfo:
        dummy_backend_instance.fetch_all("SELECT 1", None)
    assert get_expected_error_message() in str(excinfo.value)


def test_dummy_backend_model_one_raises_not_implemented_error(unconfigured_user_model_for_io):
    """Test that Model.query().one() with DummyBackend raises NotImplementedError."""
    User = unconfigured_user_model_for_io
    with pytest.raises(NotImplementedError) as excinfo:
        User.query().one()
    assert get_expected_error_message() in str(excinfo.value)


def test_dummy_backend_model_all_raises_not_implemented_error(unconfigured_user_model_for_io):
    """Test that Model.query().all() with DummyBackend raises NotImplementedError."""
    User = unconfigured_user_model_for_io
    with pytest.raises(NotImplementedError) as excinfo:
        User.query().all()
    assert get_expected_error_message() in str(excinfo.value)


def test_dummy_backend_model_save_raises_not_implemented_error(unconfigured_user_model_for_io):
    """Test that Model.save() with DummyBackend raises NotImplementedError."""
    User = unconfigured_user_model_for_io
    user = User(name="Test User", id=1)
    with pytest.raises(DatabaseError) as excinfo:
        user.save()
    assert get_expected_error_message() in str(excinfo.value)


def test_dummy_backend_model_delete_raises_not_implemented_error(unconfigured_user_model_for_io):
    """Test that Model.delete() with DummyBackend raises NotImplementedError."""
    User = unconfigured_user_model_for_io
    user = User(name="Test User", id=1)
    # Mock _is_from_db to bypass the check for existing record for delete to be attempted
    user._is_from_db = True 
    with pytest.raises(NotImplementedError) as excinfo:
        user.delete()
    assert get_expected_error_message() in str(excinfo.value)


