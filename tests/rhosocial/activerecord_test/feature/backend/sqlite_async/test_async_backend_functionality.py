"""
Tests for AsyncSQLiteBackend functionality
"""
import pytest
from rhosocial.activerecord_test.feature.backend.sqlite_async.async_backend import AsyncSQLiteBackend


@pytest.mark.asyncio
async def test_async_backend_initialization(async_sqlite_backend):
    """Test AsyncSQLiteBackend initialization."""
    assert async_sqlite_backend is not None
    assert async_sqlite_backend.is_connected()


@pytest.mark.asyncio
async def test_async_backend_ping(async_sqlite_backend):
    """Test AsyncSQLiteBackend ping functionality."""
    result = await async_sqlite_backend.ping()
    assert result is True


@pytest.mark.asyncio
async def test_async_backend_server_version(async_sqlite_backend):
    """Test AsyncSQLiteBackend server version."""
    version = async_sqlite_backend.get_server_version()
    assert isinstance(version, tuple)
    assert len(version) == 3
    assert all(isinstance(v, int) for v in version)




from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


@pytest.mark.asyncio
async def test_async_backend_execute_basic(async_sqlite_backend):
    """Test AsyncSQLiteBackend basic execution."""
    # Create a simple table
    options = ExecutionOptions(stmt_type=StatementType.DDL)
    result = await async_sqlite_backend.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)", options=options)
    # For DDL statements like CREATE TABLE, affected_rows may be -1 (which is normal)
    assert result is not None

    # Insert a record
    options = ExecutionOptions(stmt_type=StatementType.DML)
    result = await async_sqlite_backend.execute("INSERT INTO test (name) VALUES (?)", params=("test_name",), options=options)
    assert result.affected_rows == 1

    # Query the record
    options = ExecutionOptions(stmt_type=StatementType.DQL)
    result = await async_sqlite_backend.execute("SELECT * FROM test WHERE name = ?", params=("test_name",), options=options)
    assert result.data is not None
    assert len(result.data) == 1
    assert result.data[0]['name'] == 'test_name'


@pytest.mark.asyncio
async def test_async_backend_transaction(async_sqlite_backend):
    """Test AsyncSQLiteBackend transaction functionality."""
    # Test transaction begin/commit
    await async_sqlite_backend.transaction_manager.begin()
    assert async_sqlite_backend.transaction_manager.is_active is True

    # Create a table in transaction
    options = ExecutionOptions(stmt_type=StatementType.DDL)
    await async_sqlite_backend.execute("CREATE TABLE test_trans (id INTEGER PRIMARY KEY, name TEXT)", options=options)

    # Insert data
    options = ExecutionOptions(stmt_type=StatementType.DML)
    await async_sqlite_backend.execute("INSERT INTO test_trans (name) VALUES (?)", params=("trans_test",), options=options)

    await async_sqlite_backend.transaction_manager.commit()
    assert async_sqlite_backend.transaction_manager.is_active is False

    # Verify data exists after commit
    options = ExecutionOptions(stmt_type=StatementType.DQL)
    result = await async_sqlite_backend.execute("SELECT * FROM test_trans", options=options)
    assert result.data is not None
    assert len(result.data) == 1
    assert result.data[0]['name'] == 'trans_test'


@pytest.mark.asyncio
async def test_async_backend_transaction_rollback(async_sqlite_backend):
    """Test AsyncSQLiteBackend transaction rollback functionality."""
    # Create table first
    options = ExecutionOptions(stmt_type=StatementType.DDL)
    await async_sqlite_backend.execute("CREATE TABLE test_rollback (id INTEGER PRIMARY KEY, name TEXT)", options=options)

    # Begin transaction and insert data
    await async_sqlite_backend.transaction_manager.begin()
    options = ExecutionOptions(stmt_type=StatementType.DML)
    await async_sqlite_backend.execute("INSERT INTO test_rollback (name) VALUES (?)", params=("will_be_rolled_back",), options=options)

    # Verify data is visible within transaction
    options = ExecutionOptions(stmt_type=StatementType.DQL)
    result = await async_sqlite_backend.execute("SELECT * FROM test_rollback", options=options)
    assert len(result.data) == 1

    # Rollback the transaction
    await async_sqlite_backend.transaction_manager.rollback()
    assert async_sqlite_backend.transaction_manager.is_active is False

    # Verify data was rolled back
    options = ExecutionOptions(stmt_type=StatementType.DQL)
    result = await async_sqlite_backend.execute("SELECT * FROM test_rollback", options=options)
    assert len(result.data) == 0


@pytest.mark.asyncio
async def test_async_backend_multiple_nested_levels(async_sqlite_backend):
    """Test AsyncSQLiteBackend multiple nested transaction levels."""
    # Create table first
    options = ExecutionOptions(stmt_type=StatementType.DDL)
    await async_sqlite_backend.execute("""
                              CREATE TABLE nested_test
                              (
                                  id    INTEGER PRIMARY KEY,
                                  value TEXT,
                                  level INTEGER
                              )
                              """, options=options)

    # Begin main transaction
    await async_sqlite_backend.transaction_manager.begin()
    assert async_sqlite_backend.transaction_manager.is_active is True

    # Insert data in main transaction
    options = ExecutionOptions(stmt_type=StatementType.DML)
    await async_sqlite_backend.execute(
        "INSERT INTO nested_test (value, level) VALUES (?, ?)",
        params=("main", 0),
        options=options
    )

    # Begin first nested transaction
    await async_sqlite_backend.transaction_manager.begin()
    await async_sqlite_backend.execute(
        "INSERT INTO nested_test (value, level) VALUES (?, ?)",
        params=("nested1", 1),
        options=options
    )

    # Begin second nested transaction
    await async_sqlite_backend.transaction_manager.begin()
    await async_sqlite_backend.execute(
        "INSERT INTO nested_test (value, level) VALUES (?, ?)",
        params=("nested2", 2),
        options=options
    )

    # Verify data is visible within nested transaction
    options = ExecutionOptions(stmt_type=StatementType.DQL)
    result = await async_sqlite_backend.execute("SELECT COUNT(*) as cnt FROM nested_test", options=options)
    assert result.data[0]['cnt'] == 3  # main + nested1 + nested2

    # Commit innermost transaction
    await async_sqlite_backend.transaction_manager.commit()
    assert async_sqlite_backend.transaction_manager.is_active is True  # Still in outer transaction

    # Begin another nested transaction
    await async_sqlite_backend.transaction_manager.begin()
    await async_sqlite_backend.execute(
        "INSERT INTO nested_test (value, level) VALUES (?, ?)",
        params=("nested3", 3),
        options=options
    )

    # Rollback this nested transaction
    await async_sqlite_backend.transaction_manager.rollback()

    # Verify nested3 was not added but others still exist
    result = await async_sqlite_backend.execute("SELECT COUNT(*) as cnt FROM nested_test", options=options)
    assert result.data[0]['cnt'] == 3  # Should still be 3

    # Commit middle transaction
    await async_sqlite_backend.transaction_manager.commit()
    assert async_sqlite_backend.transaction_manager.is_active is True  # Still in main transaction

    # Commit main transaction
    await async_sqlite_backend.transaction_manager.commit()
    assert async_sqlite_backend.transaction_manager.is_active is False

    # Verify all committed data exists
    options = ExecutionOptions(stmt_type=StatementType.DQL)
    result = await async_sqlite_backend.execute("SELECT * FROM nested_test ORDER BY level", options=options)
    assert len(result.data) == 3
    assert result.data[0]['value'] == 'main'
    assert result.data[1]['value'] == 'nested1'
    assert result.data[2]['value'] == 'nested2'


@pytest.mark.asyncio
async def test_async_backend_error_handling(async_sqlite_backend):
    """Test AsyncSQLiteBackend error handling."""
    # Try to execute invalid SQL to trigger error handling
    with pytest.raises(Exception):
        await async_sqlite_backend.execute("INVALID SQL STATEMENT")