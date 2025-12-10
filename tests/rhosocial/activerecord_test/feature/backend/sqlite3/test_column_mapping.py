# tests/rhosocial/activerecord_test/feature/backend/sqlite3/test_column_mapping.py
import pytest
from datetime import datetime
import logging
import uuid

from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.dialect import ReturningOptions
from rhosocial.activerecord.backend.errors import QueryError

# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


@pytest.fixture
def mapped_table_backend():
    """
    Fixture to set up an in-memory SQLite database, a SQLiteBackend instance,
    and a 'mapped_users' table with columns for type adaptation.
    Yields the configured backend instance.
    """
    log.info("Setting up in-memory SQLite backend for column mapping test.")
    backend = SQLiteBackend(database=":memory:")
    backend.connect()

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
    backend.executescript(create_table_sql)
    log.info("Table 'mapped_users' created.")

    yield backend

    log.info("Tearing down SQLite backend.")
    backend.disconnect()

# =================================================================
# Original tests from the previous successful run (RESTORED)
# =================================================================

def test_insert_and_returning_with_mapping(mapped_table_backend):
    """
    Tests that execute() with an INSERT and a RETURNING clause correctly uses
    column_mapping to map the resulting column names back to field names.
    """
    backend = mapped_table_backend
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    
    column_to_field_mapping = {
        "user_id": "user_pk",
        "name": "full_name",
        "email": "user_email",
        "created_at": "created_timestamp"
    }

    sql = "INSERT INTO mapped_users (name, email, created_at) VALUES (?, ?, ?)"
    params = ("John Doe", "john.doe@example.com", now_str)

    result = backend.execute(
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
    assert returned_row["full_name"] == "John Doe"
    assert result.last_insert_id == 1


def test_update_with_backend(mapped_table_backend):
    """
    Tests that an update operation via execute() works correctly.
    """
    backend = mapped_table_backend
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    
    backend.execute("INSERT INTO mapped_users (name, email, created_at) VALUES (?, ?, ?)",
                    ("Jane Doe", "jane.doe@example.com", now_str))

    sql = "UPDATE mapped_users SET name = ? WHERE user_id = ?"
    params = ("Jane Smith", 1)
    result = backend.execute(sql, params)

    assert result.affected_rows == 1

    fetch_result = backend.execute("SELECT name FROM mapped_users WHERE user_id = 1")
    fetched_row = fetch_result.data[0] if fetch_result.data else None
    assert fetched_row is not None
    assert fetched_row["name"] == "Jane Smith"


def test_execute_fetch_with_mapping(mapped_table_backend):
    """
    Tests that a general execute/fetch call correctly uses column_mapping
    to return rows with field names as keys.
    """
    backend = mapped_table_backend
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    
    column_to_field_mapping = {
        "user_id": "user_pk",
        "name": "full_name",
        "email": "user_email"
    }

    backend.execute("INSERT INTO mapped_users (name, email, created_at) VALUES (?, ?, ?)",
                    ("Fetch Test", "fetch@example.com", now_str))

    result = backend.execute(
        "SELECT * FROM mapped_users WHERE user_id = 1",
        column_mapping=column_to_field_mapping
    )
    fetched_row = result.data[0] if result.data else None

    assert fetched_row is not None
    assert "full_name" in fetched_row
    assert "user_email" in fetched_row
    assert "created_at" in fetched_row
    assert fetched_row["full_name"] == "Fetch Test"
    assert fetched_row["user_pk"] == 1


def test_execute_fetch_without_mapping(mapped_table_backend):
    """
    Tests that a fetch call WITHOUT column_mapping returns rows
    with raw database column names as keys.
    """
    backend = mapped_table_backend
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')

    backend.execute("INSERT INTO mapped_users (name, email, created_at) VALUES (?, ?, ?)",
                    ("No Map", "nomap@example.com", now_str))

    result = backend.execute("SELECT * FROM mapped_users WHERE user_id = 1")
    fetched_row = result.data[0] if result.data else None

    assert fetched_row is not None
    assert "user_id" in fetched_row
    assert "name" in fetched_row
    assert "full_name" not in fetched_row
    assert "user_pk" not in fetched_row
    assert fetched_row["name"] == "No Map"

# =================================================================
# New test case for combined adapters and mapping
# =================================================================

def test_fetch_with_combined_mapping_and_adapters(mapped_table_backend):
    """
    Tests that execute() correctly applies both column_mapping and column_adapters.
    """
    backend = mapped_table_backend
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    test_uuid = uuid.uuid4()

    # Define mappings and adapters
    column_to_field_mapping = {
        "user_id": "pk",
        "name": "full_name",
        "user_uuid": "uuid",
        "is_active": "active"
    }
    
    # Get adapters from the backend's registry
    uuid_adapter = backend.adapter_registry.get_adapter(uuid.UUID, str)
    bool_adapter = backend.adapter_registry.get_adapter(bool, int)

    column_adapters = {
        "user_uuid": (uuid_adapter, uuid.UUID),
        "is_active": (bool_adapter, bool)
    }

    # Insert data in DB-compatible format
    backend.execute(
        "INSERT INTO mapped_users (name, email, created_at, user_uuid, is_active) VALUES (?, ?, ?, ?, ?)",
        ("Combined Test", "combined@example.com", now_str, str(test_uuid), 1)
    )

    # Execute SELECT with both mapping and adapters
    result = backend.execute(
        "SELECT * FROM mapped_users WHERE user_id = 1",
        column_mapping=column_to_field_mapping,
        column_adapters=column_adapters
    )

    fetched_row = result.data[0] if result.data else None
    assert fetched_row is not None

    # 1. Assert keys are the MAPPED FIELD NAMES
    assert "full_name" in fetched_row
    assert "uuid" in fetched_row
    assert "active" in fetched_row
    assert "name" not in fetched_row
    assert "user_uuid" not in fetched_row

    # 2. Assert values are the ADAPTED PYTHON TYPES
    assert fetched_row["full_name"] == "Combined Test"
    assert isinstance(fetched_row["uuid"], uuid.UUID)
    assert fetched_row["uuid"] == test_uuid
    assert isinstance(fetched_row["active"], bool)
    assert fetched_row["active"] is True
