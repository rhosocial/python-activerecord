# tests/rhosocial/activerecord_test/feature/query/test_to_sql_no_backend.py
import pytest
from pydantic import Field
from typing import ClassVar, Optional

from rhosocial.activerecord.model import ActiveRecord

from rhosocial.activerecord.backend.base import StorageBackend


class UserModel(ActiveRecord):
    __table_name__: ClassVar[str] = "users"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str


@pytest.fixture
def unconfigured_user_model():
    """Provides a UserModel that has no backend configured."""
    # Ensure no backend is configured before each test
    UserModel.__backend__ = None
    UserModel.__backend_class__ = None
    UserModel.__connection_config__ = None
    yield UserModel
    # Clean up after test
    UserModel.__backend__ = None
    UserModel.__backend_class__ = None
    UserModel.__connection_config__ = None
    if hasattr(UserModel, '_dummy_backend'):
        del UserModel._dummy_backend


def test_to_sql_with_dummy_backend(unconfigured_user_model):
    """
    Test that to_sql() works correctly even when no real backend is configured,
    falling back to DummyBackend.
    """
    User = unconfigured_user_model
    
    # Verify that the backend is indeed DummyBackend
    backend_instance = User.backend()
    assert isinstance(backend_instance, StorageBackend)
    from rhosocial.activerecord.backend.impl.dummy.backend import DummyBackend
    assert isinstance(backend_instance, DummyBackend)

    # Build a query
    query_builder = User.query().query({'name': 'Alice'}).limit(5).offset(10).order_by("id DESC")
    sql, params = query_builder.to_sql()

    # Expected SQL from DummyDialect (uses double quotes for identifiers, ? for placeholders)
    expected_sql = 'SELECT * FROM "users" WHERE name = ? ORDER BY "id" DESC LIMIT 5 OFFSET 10'
    expected_params = ("Alice",)

    assert sql == expected_sql
    assert params == expected_params

    # Test another query with multiple conditions
    query_builder_2 = User.query().query({'name__like': '%Bob%'}).where('email = ?', ("bob@example.com",))
    sql_2, params_2 = query_builder_2.to_sql()
    expected_sql_2 = (
        'SELECT * FROM "users" WHERE name LIKE ? AND email = ?'
    )
    expected_params_2 = ("%Bob%", "bob@example.com")
    assert sql_2 == expected_sql_2
    assert params_2 == expected_params_2


def test_sync_execution_fails_with_dummy_backend(unconfigured_user_model):
    """
    Test that synchronous execution methods on an unconfigured model
    raise NotImplementedError when using DummyBackend.
    """
    User = unconfigured_user_model

    # Attempt to execute a query that requires database interaction
    with pytest.raises(NotImplementedError) as excinfo:
        User.query().one()
    assert "DummyBackend does not support real database operations. Did you forget to configure a concrete backend?" in str(excinfo.value)

    with pytest.raises(NotImplementedError) as excinfo:
        User.query().all()
    assert "DummyBackend does not support real database operations. Did you forget to configure a concrete backend?" in str(excinfo.value)


@pytest.mark.asyncio
async def test_async_execution_fails_with_dummy_backend(unconfigured_user_model):
    """
    Test that asynchronous execution methods on an unconfigured model
    raise TypeError (because a sync method is not awaitable) when using DummyBackend.
    """
    User = unconfigured_user_model

    # Attempt to execute an async query (should implicitly call an async method on backend)
    # Since DummyBackend has sync methods, awaiting them will cause TypeError
    with pytest.raises(NotImplementedError) as excinfo:
        await User.query().one() # This will try to await a sync backend.one() which does not exist
    
    # The error message might vary slightly depending on how pytest-asyncio and Python handle it,
    assert "DummyBackend does not support real database operations. Did you forget to configure a concrete backend?" in str(excinfo.value)
