"""
Tests for high-level async SQL operations with RETURNING clause using AsyncSQLOperationsMixin.

This test file specifically tests the async insert, update, and delete methods
from AsyncSQLOperationsMixin with returning_columns parameter.
"""
import logging
import pytest
import pytest_asyncio
import sqlite3
import tempfile
import os
from datetime import datetime

from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord_test.feature.backend.sqlite_async.async_backend import AsyncSQLiteBackend
from rhosocial.activerecord.backend.options import InsertOptions, UpdateOptions, DeleteOptions
from rhosocial.activerecord.backend.expression import ComparisonPredicate, Column, Literal
from rhosocial.activerecord.backend.schema import StatementType


@pytest_asyncio.fixture
async def async_returning_backend():
    """
    Fixture to set up an in-memory async SQLite database with a test table
    for RETURNING clause tests.
    """
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger(__name__)
    
    log.info("Setting up in-memory async SQLite backend for RETURNING tests.")
    config = SQLiteConnectionConfig(database=":memory:")
    backend = AsyncSQLiteBackend(connection_config=config)
    await backend.connect()

    # Create test table
    from rhosocial.activerecord.backend.options import ExecutionOptions
    await backend.execute(
        """CREATE TABLE test_users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            age INTEGER,
            is_active INTEGER DEFAULT 1
        );""",
        options=ExecutionOptions(stmt_type=StatementType.DDL)
    )
    log.info("Table 'test_users' created.")

    yield backend

    log.info("Tearing down async SQLite backend.")
    await backend.disconnect()


@pytest.mark.skipif(
    sqlite3.sqlite_version_info < (3, 35),
    reason="RETURNING clause requires SQLite 3.35+"
)
@pytest.mark.asyncio
async def test_async_insert_with_returning_columns(async_returning_backend):
    """
    Tests the async insert method with returning_columns parameter.
    """
    backend = async_returning_backend
    
    # Create InsertOptions with returning_columns
    insert_options = InsertOptions(
        table="test_users",
        data={
            "name": "Async John Doe",
            "email": "async.john.doe@example.com",
            "age": 30
        },
        returning_columns=["user_id", "name", "email"]
    )

    result = await backend.insert(insert_options)

    # Verify the result contains the returned data
    assert result is not None
    assert result.data is not None
    assert len(result.data) == 1  # One row returned

    returned_row = result.data[0]
    assert "user_id" in returned_row
    assert "name" in returned_row
    assert "email" in returned_row
    assert returned_row["name"] == "Async John Doe"
    assert returned_row["email"] == "async.john.doe@example.com"
    assert returned_row["user_id"] > 0  # Should be the auto-generated ID


@pytest.mark.skipif(
    sqlite3.sqlite_version_info < (3, 35),
    reason="RETURNING clause requires SQLite 3.35+"
)
@pytest.mark.asyncio
async def test_async_update_with_returning_columns(async_returning_backend):
    """
    Tests the async update method with returning_columns parameter.
    """
    backend = async_returning_backend
    
    # First, insert a record to update
    insert_options = InsertOptions(
        table="test_users",
        data={
            "name": "Async Jane Doe",
            "email": "async.jane.doe@example.com",
            "age": 25
        },
        returning_columns=["user_id"]
    )
    insert_result = await backend.insert(insert_options)
    user_id = insert_result.data[0]["user_id"]
    
    # Create UpdateOptions with returning_columns
    where_predicate = ComparisonPredicate(
        backend.dialect, '=', Column(backend.dialect, "user_id"), Literal(backend.dialect, user_id)
    )
    update_options = UpdateOptions(
        table="test_users",
        data={
            "name": "Async Jane Smith",
            "age": 26
        },
        where=where_predicate,
        returning_columns=["user_id", "name", "age"]
    )

    result = await backend.update(update_options)

    # Verify the result contains the returned data
    assert result is not None
    assert result.data is not None
    assert len(result.data) == 1  # One row returned

    returned_row = result.data[0]
    assert "user_id" in returned_row
    assert "name" in returned_row
    assert "age" in returned_row
    assert returned_row["name"] == "Async Jane Smith"
    assert returned_row["age"] == 26
    assert returned_row["user_id"] == user_id


@pytest.mark.skipif(
    sqlite3.sqlite_version_info < (3, 35),
    reason="RETURNING clause requires SQLite 3.35+"
)
@pytest.mark.asyncio
async def test_async_delete_with_returning_columns(async_returning_backend):
    """
    Tests the async delete method with returning_columns parameter.
    """
    backend = async_returning_backend
    
    # First, insert a record to delete
    insert_options = InsertOptions(
        table="test_users",
        data={
            "name": "Async ToDelete User",
            "email": "async.to_delete@example.com",
            "age": 35
        },
        returning_columns=["user_id"]
    )
    insert_result = await backend.insert(insert_options)
    user_id = insert_result.data[0]["user_id"]
    
    # Verify the record exists before deletion
    check_result = await backend.fetch_one(
        "SELECT * FROM test_users WHERE user_id = ?",
        (user_id,)
    )
    assert check_result is not None
    assert check_result["name"] == "Async ToDelete User"
    
    # Create DeleteOptions with returning_columns
    where_predicate = ComparisonPredicate(
        backend.dialect, '=', Column(backend.dialect, "user_id"), Literal(backend.dialect, user_id)
    )
    delete_options = DeleteOptions(
        table="test_users",
        where=where_predicate,
        returning_columns=["user_id", "name", "email"]
    )

    result = await backend.delete(delete_options)

    # Verify the result contains the returned data
    assert result is not None
    assert result.data is not None
    assert len(result.data) == 1  # One row returned

    returned_row = result.data[0]
    assert "user_id" in returned_row
    assert "name" in returned_row
    assert "email" in returned_row
    assert returned_row["name"] == "Async ToDelete User"
    assert returned_row["email"] == "async.to_delete@example.com"
    assert returned_row["user_id"] == user_id
    
    # Verify the record was actually deleted
    check_result = await backend.fetch_one(
        "SELECT * FROM test_users WHERE user_id = ?",
        (user_id,)
    )
    assert check_result is None


@pytest.mark.skipif(
    sqlite3.sqlite_version_info < (3, 35),
    reason="RETURNING clause requires SQLite 3.35+"
)
@pytest.mark.asyncio
async def test_async_operations_without_returning_columns(async_returning_backend):
    """
    Tests that async operations work correctly when returning_columns is not specified.
    """
    backend = async_returning_backend
    
    # Test insert without returning columns
    insert_options = InsertOptions(
        table="test_users",
        data={
            "name": "Async No Return User",
            "email": "async.no_return@example.com",
            "age": 40
        }
        # No returning_columns specified
    )
    
    result = await backend.insert(insert_options)
    # Should still work, but result.data might be None or empty depending on implementation
    assert result is not None
    
    # Test update without returning columns
    where_predicate = ComparisonPredicate(
        backend.dialect, '=', Column(backend.dialect, "name"), Literal(backend.dialect, "Async No Return User")
    )
    update_options = UpdateOptions(
        table="test_users",
        data={
            "age": 41
        },
        where=where_predicate
        # No returning_columns specified
    )
    
    result = await backend.update(update_options)
    assert result is not None
    # The result should still have affected_rows info
    assert result.affected_rows >= 0
    
    # Test delete without returning columns
    delete_where = ComparisonPredicate(
        backend.dialect, '=', Column(backend.dialect, "name"), Literal(backend.dialect, "Async No Return User")
    )
    delete_options = DeleteOptions(
        table="test_users",
        where=delete_where
        # No returning_columns specified
    )
    
    result = await backend.delete(delete_options)
    assert result is not None
    # The result should still have affected_rows info
    assert result.affected_rows >= 0


@pytest.mark.skipif(
    sqlite3.sqlite_version_info < (3, 35),
    reason="RETURNING clause requires SQLite 3.35+"
)
@pytest.mark.asyncio
async def test_async_multiple_returning_columns(async_returning_backend):
    """
    Tests async operations with multiple returning columns.
    """
    backend = async_returning_backend
    
    # Insert with multiple returning columns
    insert_options = InsertOptions(
        table="test_users",
        data={
            "name": "Async Multi Return User",
            "email": "async.multi_return@example.com",
            "age": 33,
            "is_active": 1
        },
        returning_columns=["user_id", "name", "email", "age", "is_active"]
    )
    
    result = await backend.insert(insert_options)
    assert result is not None
    assert result.data is not None
    assert len(result.data) == 1
    
    returned_row = result.data[0]
    assert "user_id" in returned_row
    assert "name" in returned_row
    assert "email" in returned_row
    assert "age" in returned_row
    assert "is_active" in returned_row
    assert returned_row["name"] == "Async Multi Return User"
    assert returned_row["email"] == "async.multi_return@example.com"
    assert returned_row["age"] == 33
    assert returned_row["is_active"] == 1
    assert returned_row["user_id"] > 0


@pytest.mark.skipif(
    sqlite3.sqlite_version_info < (3, 35),
    reason="RETURNING clause requires SQLite 3.35+"
)
@pytest.mark.asyncio
async def test_async_returning_with_transaction(async_returning_backend):
    """
    Tests async operations with returning columns inside a transaction.
    """
    backend = async_returning_backend
    
    # Begin transaction
    await backend.transaction_manager.begin()
    
    try:
        # Insert with returning columns in transaction
        insert_options = InsertOptions(
            table="test_users",
            data={
                "name": "Async Transaction User",
                "email": "async.transaction@example.com",
                "age": 28
            },
            returning_columns=["user_id", "name"]
        )
        
        result = await backend.insert(insert_options)
        assert result is not None
        assert result.data is not None
        assert len(result.data) == 1
        
        returned_row = result.data[0]
        assert "user_id" in returned_row
        assert "name" in returned_row
        assert returned_row["name"] == "Async Transaction User"
        user_id = returned_row["user_id"]
        
        # Update with returning columns in transaction
        where_predicate = ComparisonPredicate(
            backend.dialect, '=', Column(backend.dialect, "user_id"), Literal(backend.dialect, user_id)
        )
        update_options = UpdateOptions(
            table="test_users",
            data={
                "age": 29
            },
            where=where_predicate,
            returning_columns=["user_id", "age"]
        )
        
        result = await backend.update(update_options)
        assert result is not None
        assert result.data is not None
        assert len(result.data) == 1
        
        returned_row = result.data[0]
        assert "user_id" in returned_row
        assert "age" in returned_row
        assert returned_row["age"] == 29
        assert returned_row["user_id"] == user_id
        
        # Commit transaction
        await backend.transaction_manager.commit()
        
        # Verify data exists after commit
        check_result = await backend.fetch_one(
            "SELECT * FROM test_users WHERE user_id = ?",
            (user_id,)
        )
        assert check_result is not None
        assert check_result["name"] == "Async Transaction User"
        assert check_result["age"] == 29
        
    except Exception:
        # Rollback on error
        await backend.transaction_manager.rollback()
        raise


if __name__ == "__main__":
    pytest.main([__file__])