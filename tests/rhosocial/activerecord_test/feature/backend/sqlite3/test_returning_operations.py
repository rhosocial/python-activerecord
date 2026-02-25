"""
Tests for high-level SQL operations with RETURNING clause using SQLOperationsMixin.

This test file specifically tests the insert, update, and delete methods
from SQLOperationsMixin with returning_columns parameter.
"""
import logging
import pytest
import sqlite3
from datetime import datetime

from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.options import InsertOptions, UpdateOptions, DeleteOptions
from rhosocial.activerecord.backend.expression import ComparisonPredicate, Column, Literal
from rhosocial.activerecord.backend.schema import StatementType


@pytest.fixture
def returning_backend():
    """
    Fixture to set up an in-memory SQLite database with a test table
    for RETURNING clause tests.
    """
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger(__name__)
    
    log.info("Setting up in-memory SQLite backend for RETURNING tests.")
    backend = SQLiteBackend(database=":memory:")
    backend.connect()

    create_table_sql = """
    CREATE TABLE test_users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        age INTEGER,
        is_active INTEGER DEFAULT 1
    );
    """
    from rhosocial.activerecord.backend.options import ExecutionOptions
    backend.execute(create_table_sql, options=ExecutionOptions(stmt_type=StatementType.DDL))
    log.info("Table 'test_users' created.")

    yield backend

    log.info("Tearing down SQLite backend.")
    backend.disconnect()


@pytest.mark.skipif(
    sqlite3.sqlite_version_info < (3, 35),
    reason="RETURNING clause requires SQLite 3.35+"
)
def test_insert_with_returning_columns(returning_backend):
    """
    Tests the insert method with returning_columns parameter.
    """
    backend = returning_backend
    
    # Create InsertOptions with returning_columns
    insert_options = InsertOptions(
        table="test_users",
        data={
            "name": "John Doe",
            "email": "john.doe@example.com",
            "age": 30
        },
        returning_columns=["user_id", "name", "email"]
    )

    result = backend.insert(insert_options)

    # Verify the result contains the returned data
    assert result is not None
    assert result.data is not None
    assert len(result.data) == 1  # One row returned

    returned_row = result.data[0]
    assert "user_id" in returned_row
    assert "name" in returned_row
    assert "email" in returned_row
    assert returned_row["name"] == "John Doe"
    assert returned_row["email"] == "john.doe@example.com"
    assert returned_row["user_id"] > 0  # Should be the auto-generated ID


@pytest.mark.skipif(
    sqlite3.sqlite_version_info < (3, 35),
    reason="RETURNING clause requires SQLite 3.35+"
)
def test_update_with_returning_columns(returning_backend):
    """
    Tests the update method with returning_columns parameter.
    """
    backend = returning_backend
    
    # First, insert a record to update
    insert_options = InsertOptions(
        table="test_users",
        data={
            "name": "Jane Doe",
            "email": "jane.doe@example.com",
            "age": 25
        },
        returning_columns=["user_id"]
    )
    insert_result = backend.insert(insert_options)
    user_id = insert_result.data[0]["user_id"]
    
    # Create UpdateOptions with returning_columns
    where_predicate = ComparisonPredicate(
        backend.dialect, '=', Column(backend.dialect, "user_id"), Literal(backend.dialect, user_id)
    )
    update_options = UpdateOptions(
        table="test_users",
        data={
            "name": "Jane Smith",
            "age": 26
        },
        where=where_predicate,
        returning_columns=["user_id", "name", "age"]
    )

    result = backend.update(update_options)

    # Verify the result contains the returned data
    assert result is not None
    assert result.data is not None
    assert len(result.data) == 1  # One row returned

    returned_row = result.data[0]
    assert "user_id" in returned_row
    assert "name" in returned_row
    assert "age" in returned_row
    assert returned_row["name"] == "Jane Smith"
    assert returned_row["age"] == 26
    assert returned_row["user_id"] == user_id


@pytest.mark.skipif(
    sqlite3.sqlite_version_info < (3, 35),
    reason="RETURNING clause requires SQLite 3.35+"
)
def test_delete_with_returning_columns(returning_backend):
    """
    Tests the delete method with returning_columns parameter.
    """
    backend = returning_backend
    
    # First, insert a record to delete
    insert_options = InsertOptions(
        table="test_users",
        data={
            "name": "ToDelete User",
            "email": "to_delete@example.com",
            "age": 35
        },
        returning_columns=["user_id"]
    )
    insert_result = backend.insert(insert_options)
    user_id = insert_result.data[0]["user_id"]
    
    # Verify the record exists before deletion
    check_result = backend.fetch_one(
        "SELECT * FROM test_users WHERE user_id = ?",
        (user_id,)
    )
    assert check_result is not None
    assert check_result["name"] == "ToDelete User"
    
    # Create DeleteOptions with returning_columns
    where_predicate = ComparisonPredicate(
        backend.dialect, '=', Column(backend.dialect, "user_id"), Literal(backend.dialect, user_id)
    )
    delete_options = DeleteOptions(
        table="test_users",
        where=where_predicate,
        returning_columns=["user_id", "name", "email"]
    )

    result = backend.delete(delete_options)

    # Verify the result contains the returned data
    assert result is not None
    assert result.data is not None
    assert len(result.data) == 1  # One row returned

    returned_row = result.data[0]
    assert "user_id" in returned_row
    assert "name" in returned_row
    assert "email" in returned_row
    assert returned_row["name"] == "ToDelete User"
    assert returned_row["email"] == "to_delete@example.com"
    assert returned_row["user_id"] == user_id
    
    # Verify the record was actually deleted
    check_result = backend.fetch_one(
        "SELECT * FROM test_users WHERE user_id = ?",
        (user_id,)
    )
    assert check_result is None


@pytest.mark.skipif(
    sqlite3.sqlite_version_info < (3, 35),
    reason="RETURNING clause requires SQLite 3.35+"
)
def test_operations_without_returning_columns(returning_backend):
    """
    Tests that operations work correctly when returning_columns is not specified.
    """
    backend = returning_backend
    
    # Test insert without returning columns
    insert_options = InsertOptions(
        table="test_users",
        data={
            "name": "No Return User",
            "email": "no_return@example.com",
            "age": 40
        }
        # No returning_columns specified
    )
    
    result = backend.insert(insert_options)
    # Should still work, but result.data might be None or empty depending on implementation
    assert result is not None
    
    # Test update without returning columns
    where_predicate = ComparisonPredicate(
        backend.dialect, '=', Column(backend.dialect, "name"), Literal(backend.dialect, "No Return User")
    )
    update_options = UpdateOptions(
        table="test_users",
        data={
            "age": 41
        },
        where=where_predicate
        # No returning_columns specified
    )
    
    result = backend.update(update_options)
    assert result is not None
    # The result should still have affected_rows info
    assert result.affected_rows >= 0
    
    # Test delete without returning columns
    delete_where = ComparisonPredicate(
        backend.dialect, '=', Column(backend.dialect, "name"), Literal(backend.dialect, "No Return User")
    )
    delete_options = DeleteOptions(
        table="test_users",
        where=delete_where
        # No returning_columns specified
    )
    
    result = backend.delete(delete_options)
    assert result is not None
    # The result should still have affected_rows info
    assert result.affected_rows >= 0


@pytest.mark.skipif(
    sqlite3.sqlite_version_info < (3, 35),
    reason="RETURNING clause requires SQLite 3.35+"
)
def test_multiple_returning_columns(returning_backend):
    """
    Tests operations with multiple returning columns.
    """
    backend = returning_backend
    
    # Insert with multiple returning columns
    insert_options = InsertOptions(
        table="test_users",
        data={
            "name": "Multi Return User",
            "email": "multi_return@example.com",
            "age": 33,
            "is_active": 1
        },
        returning_columns=["user_id", "name", "email", "age", "is_active"]
    )
    
    result = backend.insert(insert_options)
    assert result is not None
    assert result.data is not None
    assert len(result.data) == 1
    
    returned_row = result.data[0]
    assert "user_id" in returned_row
    assert "name" in returned_row
    assert "email" in returned_row
    assert "age" in returned_row
    assert "is_active" in returned_row
    assert returned_row["name"] == "Multi Return User"
    assert returned_row["email"] == "multi_return@example.com"
    assert returned_row["age"] == 33
    assert returned_row["is_active"] == 1
    assert returned_row["user_id"] > 0


if __name__ == "__main__":
    pytest.main([__file__])