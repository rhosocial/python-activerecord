# tests/rhosocial/activerecord_test/feature/backend/backend/test_backend_functionality.py
"""
Tests for SQLiteBackend functionality (sync twin of test_backend_functionality_async.py)
"""

import pytest

from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


def test_backend_initialization(sqlite_backend):
    """Test SQLiteBackend initialization."""
    assert sqlite_backend is not None
    assert sqlite_backend.is_connected()


def test_backend_ping(sqlite_backend):
    """Test SQLiteBackend ping functionality."""
    result = sqlite_backend.ping()
    assert result is True


def test_backend_server_version(sqlite_backend):
    """Test SQLiteBackend server version."""
    version = sqlite_backend.get_server_version()
    assert isinstance(version, tuple)
    assert len(version) == 3
    assert all(isinstance(v, int) for v in version)


def test_backend_execute_basic(sqlite_backend):
    """Test SQLiteBackend basic execution."""
    # Create a simple table
    options = ExecutionOptions(stmt_type=StatementType.DDL)
    result = sqlite_backend.execute(
        "CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)", options=options
    )
    # For DDL statements like CREATE TABLE, affected_rows may be -1 (which is normal)
    assert result is not None

    # Insert a record
    options = ExecutionOptions(stmt_type=StatementType.DML)
    result = sqlite_backend.execute(
        "INSERT INTO test (name) VALUES (?)", params=("test_name",), options=options
    )
    assert result.affected_rows == 1

    # Query the record
    options = ExecutionOptions(stmt_type=StatementType.DQL)
    result = sqlite_backend.execute(
        "SELECT * FROM test WHERE name = ?", params=("test_name",), options=options
    )
    assert result.data is not None
    assert len(result.data) == 1
    assert result.data[0]["name"] == "test_name"


def test_backend_transaction(sqlite_backend):
    """Test SQLiteBackend transaction functionality."""
    # Test transaction begin/commit
    sqlite_backend.transaction_manager.begin()
    assert sqlite_backend.transaction_manager.is_active is True

    # Create a table in transaction
    options = ExecutionOptions(stmt_type=StatementType.DDL)
    sqlite_backend.execute("CREATE TABLE test_trans (id INTEGER PRIMARY KEY, name TEXT)", options=options)

    # Insert data
    options = ExecutionOptions(stmt_type=StatementType.DML)
    sqlite_backend.execute(
        "INSERT INTO test_trans (name) VALUES (?)", params=("trans_test",), options=options
    )

    sqlite_backend.transaction_manager.commit()
    assert sqlite_backend.transaction_manager.is_active is False

    # Verify data exists after commit
    options = ExecutionOptions(stmt_type=StatementType.DQL)
    result = sqlite_backend.execute("SELECT * FROM test_trans", options=options)
    assert result.data is not None
    assert len(result.data) == 1
    assert result.data[0]["name"] == "trans_test"


def test_backend_transaction_rollback(sqlite_backend):
    """Test SQLiteBackend transaction rollback functionality."""
    # Create table first
    options = ExecutionOptions(stmt_type=StatementType.DDL)
    sqlite_backend.execute(
        "CREATE TABLE test_rollback (id INTEGER PRIMARY KEY, name TEXT)", options=options
    )

    # Begin transaction and insert data
    sqlite_backend.transaction_manager.begin()
    options = ExecutionOptions(stmt_type=StatementType.DML)
    sqlite_backend.execute(
        "INSERT INTO test_rollback (name) VALUES (?)", params=("will_be_rolled_back",), options=options
    )

    # Verify data is visible within transaction
    options = ExecutionOptions(stmt_type=StatementType.DQL)
    result = sqlite_backend.execute("SELECT * FROM test_rollback", options=options)
    assert len(result.data) == 1

    # Rollback the transaction
    sqlite_backend.transaction_manager.rollback()
    assert sqlite_backend.transaction_manager.is_active is False

    # Verify data was rolled back
    options = ExecutionOptions(stmt_type=StatementType.DQL)
    result = sqlite_backend.execute("SELECT * FROM test_rollback", options=options)
    assert len(result.data) == 0


def test_backend_multiple_nested_levels(sqlite_backend):
    """Test SQLiteBackend multiple nested transaction levels."""
    # Create table first
    options = ExecutionOptions(stmt_type=StatementType.DDL)
    sqlite_backend.execute(
        """
                          CREATE TABLE nested_test
                          (
                              id    INTEGER PRIMARY KEY,
                              value TEXT,
                              level INTEGER
                          )
                          """,
        options=options,
    )

    # Begin main transaction
    sqlite_backend.transaction_manager.begin()
    assert sqlite_backend.transaction_manager.is_active is True

    # Insert data in main transaction
    options = ExecutionOptions(stmt_type=StatementType.DML)
    sqlite_backend.execute(
        "INSERT INTO nested_test (value, level) VALUES (?, ?)", params=("main", 0), options=options
    )

    # Begin first nested transaction
    sqlite_backend.transaction_manager.begin()
    sqlite_backend.execute(
        "INSERT INTO nested_test (value, level) VALUES (?, ?)", params=("nested1", 1), options=options
    )

    # Begin second nested transaction
    sqlite_backend.transaction_manager.begin()
    sqlite_backend.execute(
        "INSERT INTO nested_test (value, level) VALUES (?, ?)", params=("nested2", 2), options=options
    )

    # Verify data is visible within nested transaction
    options = ExecutionOptions(stmt_type=StatementType.DQL)
    result = sqlite_backend.execute("SELECT COUNT(*) as cnt FROM nested_test", options=options)
    assert result.data[0]["cnt"] == 3  # main + nested1 + nested2

    # Commit innermost transaction
    sqlite_backend.transaction_manager.commit()
    assert sqlite_backend.transaction_manager.is_active is True  # Still in outer transaction

    # Begin another nested transaction
    sqlite_backend.transaction_manager.begin()
    sqlite_backend.execute(
        "INSERT INTO nested_test (value, level) VALUES (?, ?)", params=("nested3", 3), options=options
    )

    # Rollback this nested transaction
    sqlite_backend.transaction_manager.rollback()

    # Verify nested3 was not added but others still exist
    result = sqlite_backend.execute("SELECT COUNT(*) as cnt FROM nested_test", options=options)
    assert result.data[0]["cnt"] == 3  # Should still be 3

    # Commit middle transaction
    sqlite_backend.transaction_manager.commit()
    assert sqlite_backend.transaction_manager.is_active is True  # Still in main transaction

    # Commit main transaction
    sqlite_backend.transaction_manager.commit()
    assert sqlite_backend.transaction_manager.is_active is False

    # Verify all committed data exists
    options = ExecutionOptions(stmt_type=StatementType.DQL)
    result = sqlite_backend.execute("SELECT * FROM nested_test ORDER BY level", options=options)
    assert len(result.data) == 3
    assert result.data[0]["value"] == "main"
    assert result.data[1]["value"] == "nested1"
    assert result.data[2]["value"] == "nested2"


def test_backend_error_handling(sqlite_backend):
    """Test SQLiteBackend error handling."""
    # Try to execute invalid SQL to trigger error handling
    with pytest.raises(Exception):  # noqa: B017
        sqlite_backend.execute("INVALID SQL STATEMENT")
