# tests/rhosocial/activerecord_test/feature/backend/sqlite_async/test_async_column_mapping.py
import pytest
import pytest_asyncio
from datetime import datetime
import logging
import uuid

from async_backend import AsyncSQLiteBackend
from rhosocial.activerecord.backend.dialect import ReturningOptions

# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


@pytest_asyncio.fixture
async def async_mapped_table_backend():
    """
    Fixture to set up an in-memory async SQLite database, an AsyncSQLiteBackend instance,
    and a 'mapped_users' table with columns for type adaptation.
    Yields the configured async backend instance.
    """
    log.info("Setting up in-memory async SQLite backend for column mapping test.")
    backend = AsyncSQLiteBackend(database=":memory:")
    await backend.connect()

    create_table_sql = """
    CREATE TABLE mapped_users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        created_at TIMESTAMP NOT NULL,
        user_uuid TEXT,
        is_active INTEGER
    );
    """
    await backend.executescript(create_table_sql)
    log.info("Table 'mapped_users' created.")

    yield backend

    log.info("Tearing down async SQLite backend.")
    await backend.disconnect()

# =================================================================
# Original tests from the previous successful run (RESTORED)
# =================================================================

@pytest.mark.asyncio
async def test_async_insert_and_returning_with_mapping(async_mapped_table_backend):
    """
    Tests that async execute() with an INSERT and a RETURNING clause correctly uses
    column_mapping to map the resulting column names back to field names.
    """
    backend = async_mapped_table_backend
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    
    column_to_field_mapping = {
        "user_id": "user_pk",
        "name": "full_name",
        "email": "user_email",
        "created_at": "created_timestamp"
    }

    sql = "INSERT INTO mapped_users (name, email, created_at) VALUES (?, ?, ?)"
    params = ("John Doe Async", "john.doe.async@example.com", now_str)

    result = await backend.execute(
        sql=sql,
        params=params,
        returning=ReturningOptions(enabled=True, force=True),
        column_mapping=column_to_field_mapping
    )

    assert result.data is not None
    assert len(result.data) == 1
    returned_row = result.data[0]
    
    assert "user_pk" in returned_row
    assert "full_name" in returned_row
    assert returned_row["user_pk"] == 1
    assert returned_row["full_name"] == "John Doe Async"
    assert result.last_insert_id == 1


@pytest.mark.asyncio
async def test_async_update_with_backend(async_mapped_table_backend):
    """
    Tests that an async update operation via execute() works correctly.
    """
    backend = async_mapped_table_backend
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    
    await backend.execute("INSERT INTO mapped_users (name, email, created_at) VALUES (?, ?, ?)",
                          ("Jane Doe Async", "jane.doe.async@example.com", now_str))

    sql = "UPDATE mapped_users SET name = ? WHERE user_id = ?"
    params = ("Jane Smith Async", 1)
    result = await backend.execute(sql, params)

    assert result.affected_rows == 1

    fetch_result = await backend.execute("SELECT name FROM mapped_users WHERE user_id = 1")
    fetched_row = fetch_result.data[0] if fetch_result.data else None
    assert fetched_row is not None
    assert fetched_row["name"] == "Jane Smith Async"


@pytest.mark.asyncio
async def test_async_execute_fetch_with_mapping(async_mapped_table_backend):
    """
    Tests that an async execute/fetch call correctly uses column_mapping.
    """
    backend = async_mapped_table_backend
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    
    column_to_field_mapping = {
        "user_id": "user_pk",
        "name": "full_name",
        "email": "user_email"
    }

    await backend.execute("INSERT INTO mapped_users (name, email, created_at) VALUES (?, ?, ?)",
                          ("Async Fetch Test", "asyncfetch@example.com", now_str))

    result = await backend.execute(
        "SELECT * FROM mapped_users WHERE user_id = 1",
        column_mapping=column_to_field_mapping
    )
    fetched_row = result.data[0] if result.data else None

    assert fetched_row is not None
    assert "full_name" in fetched_row
    assert "user_email" in fetched_row
    assert "created_at" in fetched_row
    assert fetched_row["full_name"] == "Async Fetch Test"
    assert fetched_row["user_pk"] == 1


@pytest.mark.asyncio
async def test_async_execute_fetch_without_mapping(async_mapped_table_backend):
    """
    Tests an async fetch call WITHOUT column_mapping returns raw column names.
    """
    backend = async_mapped_table_backend
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')

    await backend.execute("INSERT INTO mapped_users (name, email, created_at) VALUES (?, ?, ?)",
                          ("Async No Map", "asyncnomap@example.com", now_str))

    result = await backend.execute("SELECT * FROM mapped_users WHERE user_id = 1")
    fetched_row = result.data[0] if result.data else None

    assert fetched_row is not None
    assert "user_id" in fetched_row
    assert "name" in fetched_row
    assert "full_name" not in fetched_row
    assert "user_pk" not in fetched_row
    assert fetched_row["name"] == "Async No Map"

# =================================================================
# New test case for combined adapters and mapping
# =================================================================

@pytest.mark.asyncio
async def test_async_fetch_with_combined_mapping_and_adapters(async_mapped_table_backend):
    """
    Tests that async execute() correctly applies both column_mapping and column_adapters.
    """
    backend = async_mapped_table_backend
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    test_uuid = uuid.uuid4()

    column_to_field_mapping = {
        "user_id": "pk",
        "name": "full_name",
        "user_uuid": "uuid",
        "is_active": "active"
    }

    uuid_adapter = backend.adapter_registry.get_adapter(uuid.UUID, str)
    bool_adapter = backend.adapter_registry.get_adapter(bool, int)

    column_adapters = {
        "user_uuid": (uuid_adapter, uuid.UUID),
        "is_active": (bool_adapter, bool)
    }

    await backend.execute(
        "INSERT INTO mapped_users (name, email, created_at, user_uuid, is_active) VALUES (?, ?, ?, ?, ?)",
        ("Async Combined", "asynccombined@example.com", now_str, str(test_uuid), 1)
    )

    result = await backend.execute(
        "SELECT * FROM mapped_users WHERE user_id = 1",
        column_mapping=column_to_field_mapping,
        column_adapters=column_adapters
    )

    fetched_row = result.data[0] if result.data else None
    assert fetched_row is not None

    assert "full_name" in fetched_row
    assert "uuid" in fetched_row
    assert "active" in fetched_row
    assert "name" not in fetched_row
    assert "user_uuid" not in fetched_row
    
    assert fetched_row["full_name"] == "Async Combined"
    assert isinstance(fetched_row["uuid"], uuid.UUID)
    assert fetched_row["uuid"] == test_uuid
    assert isinstance(fetched_row["active"], bool)
    assert fetched_row["active"] is True
