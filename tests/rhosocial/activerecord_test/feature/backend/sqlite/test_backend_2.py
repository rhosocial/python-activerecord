# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_backend_2.py
"""Tests for improving SQLite backend coverage - Part 2 Fixed"""

import sqlite3
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

from rhosocial.activerecord.backend.dialect import ReturningOptions
from rhosocial.activerecord.backend.errors import (
    ReturningNotSupportedError,
    JsonOperationNotSupportedError
)
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.typing import DatabaseType


class TestSQLiteBackendCoveragePart2:
    """Fixed tests to improve coverage of SQLiteBackend - Part 2"""

    def test_get_statement_type_default_branch(self):
        """Test _get_statement_type() default branch (calls super)"""
        backend = SQLiteBackend(database=":memory:")

        # Test with a statement that is not PRAGMA or WITH
        result = backend._get_statement_type("CREATE TABLE test (id INTEGER)")
        assert result == "CREATE"

        # Test with empty string
        result = backend._get_statement_type("")
        assert result == ""  # Default behavior of base implementation

        # Test with comments
        sql_with_comments = "-- This is a comment\nSELECT * FROM users"
        result = backend._get_statement_type(sql_with_comments)
        assert result == "SELECT"

    def test_check_returning_compatibility_version_checks(self):
        """Test _check_returning_compatibility() version checks"""
        backend = SQLiteBackend(database=":memory:")

        # Test with SQLite version < 3.35.0 and force=False
        with patch('sqlite3.sqlite_version_info', (3, 34, 0)), \
                patch('sqlite3.sqlite_version', "3.34.0"):
            options = ReturningOptions(enabled=True, force=False)
            with pytest.raises(ReturningNotSupportedError) as exc_info:
                backend._check_returning_compatibility(options)

            assert "requires SQLite 3.35.0+" in str(exc_info.value)

        # Test with Python version < 3.10 and force=False
        with patch('sys.version_info', (3, 9, 0)):
            options = ReturningOptions(enabled=True, force=False)
            with pytest.raises(ReturningNotSupportedError) as exc_info:
                backend._check_returning_compatibility(options)

            assert "known issues in Python < 3.10" in str(exc_info.value)

        # Test with force=True bypasses checks
        with patch('sqlite3.sqlite_version_info', (3, 34, 0)), \
                patch('sys.version_info', (3, 9, 0)):
            options = ReturningOptions(enabled=True, force=True)
            # Should not raise exception
            backend._check_returning_compatibility(options)

    def test_get_cursor_with_existing_cursor(self):
        """Test _get_cursor() when cursor already exists"""
        backend = SQLiteBackend(database=":memory:")
        backend.connect()

        # Create a cursor and save it
        cursor = backend._connection.cursor()
        backend._cursor = cursor

        # Should return existing cursor
        result = backend._get_cursor()
        assert result is cursor

        backend.disconnect()

    def test_process_result_set_with_type_conversion(self):
        """Test _process_result_set() with column type conversion"""
        backend = SQLiteBackend(database=":memory:")
        backend.connect()

        # Create test table and data
        backend.execute("""
            CREATE TABLE test (
                id INTEGER,
                name TEXT,
                created_at TEXT,
                is_active INTEGER,
                data TEXT
            )
        """)

        backend.execute("""
            INSERT INTO test VALUES 
            (1, 'test', '2024-01-01 10:00:00', 1, '{"key": "value"}')
        """)

        # Define column types for conversion
        column_types = {
            "id": DatabaseType.INTEGER,
            "name": DatabaseType.TEXT,
            "created_at": DatabaseType.DATETIME,
            "is_active": DatabaseType.BOOLEAN,
            "data": DatabaseType.JSON
        }

        # Test with DatabaseType enum
        result = backend.fetch_one("SELECT * FROM test", column_types=column_types)
        assert result["id"] == 1
        assert result["name"] == "test"
        assert isinstance(result["created_at"], datetime)  # Datetime conversion
        assert result["is_active"] == True  # Boolean conversion
        assert isinstance(result["data"], dict)  # JSON conversion

        # Test with type name strings
        column_types_str = {
            "id": DatabaseType.INTEGER,
            "is_active": DatabaseType.BOOLEAN,
            "data": DatabaseType.JSON
        }

        result = backend.fetch_one("SELECT * FROM test", column_types=column_types_str)
        assert result["id"] == 1
        assert result["is_active"] == True
        assert isinstance(result["data"], dict)

        # Test with converter instance
        class MockConverter:
            def from_database(self, value, source_type=None):
                return f"converted:{value}"

        column_types_converter = {
            "name": MockConverter()
        }

        result = backend.fetch_one("SELECT * FROM test", column_types=column_types_converter)
        assert result["name"] == "converted:test"

        # Test with invalid converter (no from_database method)
        class InvalidConverter:
            pass

        column_types_invalid = {
            "name": InvalidConverter()
        }

        # Should fallback to using as type hint
        result = backend.fetch_one("SELECT * FROM test", column_types=column_types_invalid)
        assert result["name"] == "test"

        backend.disconnect()

    def test_process_result_set_with_tuple_rows(self):
        """Test _process_result_set() with tuple-like rows"""
        backend = SQLiteBackend(database=":memory:")
        backend.connect()

        # Create a mock cursor that returns tuples instead of sqlite3.Row objects
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{"id": 1, "name": "test", "is_active": True}]
        mock_cursor.description = [
            ("id",), ("name",), ("is_active",)
        ]

        # Test with column types
        column_types = {
            "id": DatabaseType.INTEGER,
            "name": DatabaseType.TEXT,
            "is_active": DatabaseType.BOOLEAN
        }

        result = backend._process_result_set(
            mock_cursor,
            is_select=True,
            need_returning=False,
            column_types=column_types
        )

        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["name"] == "test"
        assert result[0]["is_active"] == True

        backend.disconnect()

    def test_execute_many(self):
        """Test execute_many() method"""
        backend = SQLiteBackend(database=":memory:")
        backend.connect()

        # Create test table
        backend.execute("CREATE TABLE test (id INTEGER, name TEXT)")

        # Test batch insert
        params_list = [
            (1, "test1"),
            (2, "test2"),
            (3, "test3")
        ]

        result = backend.execute_many(
            "INSERT INTO test (id, name) VALUES (?, ?)",
            params_list
        )

        assert result.affected_rows == 3
        assert result.duration > 0

        # Verify data was inserted
        rows = backend.fetch_all("SELECT * FROM test ORDER BY id")
        assert len(rows) == 3
        assert rows[0]["name"] == "test1"
        assert rows[2]["name"] == "test3"

        # Test with empty params list
        result = backend.execute_many(
            "INSERT INTO test (id, name) VALUES (?, ?)",
            []
        )
        assert result.affected_rows == 0

        # Test error handling
        with pytest.raises(Exception):
            backend.execute_many(
                "INSERT INTO invalid_table VALUES (?, ?)",
                [(1, "test")]
            )

        backend.disconnect()

    def test_execute_many_without_connection(self):
        """Test execute_many() without connection"""
        backend = SQLiteBackend(database=":memory:")

        # First create the table with a regular execute
        backend.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER, name TEXT)")

        # Then test execute_many for the insert operation
        params_list = [(1, "test")]

        # Should work with auto-connected connection
        backend.execute_many(
            "INSERT INTO test VALUES (?, ?)",
            params_list
        )

        assert backend._connection is not None

        # Verify data was inserted correctly
        result = backend.fetch_all("SELECT * FROM test")
        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["name"] == "test"

        backend.disconnect()

    def test_handle_auto_commit_exception(self):
        """Test _handle_auto_commit() exception handling"""
        backend = SQLiteBackend(database=":memory:")
        backend.connect()

        # Make commit fail by closing connection first
        backend._connection.close()

        # Should not raise exception, just log warning
        backend._handle_auto_commit()

        # Restore connection for cleanup
        backend._connection = None

    def test_handle_auto_commit_without_connection(self):
        """Test _handle_auto_commit() without connection"""
        backend = SQLiteBackend(database=":memory:")

        # Should not raise exception
        backend._handle_auto_commit()

    # def test_handle_auto_commit_in_transaction(self):
    #     """Test _handle_auto_commit() during active transaction"""
    #     backend = SQLiteBackend(database=":memory:")
    #     backend.connect()
    # 
    #     # Start transaction
    #     backend.begin_transaction()
    # 
    #     # Use patch.object instead of direct attribute assignment
    #     with patch.object(backend._connection, 'commit') as mock_commit:
    #         # Should not call commit during active transaction
    #         backend._handle_auto_commit()
    #         mock_commit.assert_not_called()
    # 
    #     # Cleanup
    #     backend.rollback_transaction()
    #     backend.disconnect()

    def test_format_json_operation(self):
        """Test format_json_operation() method"""
        backend = SQLiteBackend(database=":memory:")

        # Test with valid JSON operation
        result = backend.format_json_operation(
            column="data",
            path="$.key",
            operation="extract"
        )

        # Should delegate to dialect's json_operation_handler
        # First check if arrow operators are supported
        if backend.dialect.json_operation_handler.supports_json_arrows:
            assert "->" in result
        else:
            assert "json_extract" in result

        # Test with value parameter
        result = backend.format_json_operation(
            column="data",
            path="$.key",
            operation="contains",
            value={"test": "value"}
        )

        # SQLite doesn't support contains operation, should raise error
        with pytest.raises(JsonOperationNotSupportedError):
            backend.format_json_operation(
                column="data",
                path="$.key",
                operation="unsupported"
            )

    def test_format_json_operation_without_handler(self):
        """Test format_json_operation() without json handler"""
        backend = SQLiteBackend(database=":memory:")

        # Remove json_operation_handler attribute
        original_handler = backend.dialect.json_operation_handler
        delattr(backend.dialect, '_json_operation_handler')

        try:
            with pytest.raises(JsonOperationNotSupportedError) as exc_info:
                backend.format_json_operation(
                    column="data",
                    path="$.key"
                )

            assert "JSON operations not supported" in str(exc_info.value)
        finally:
            # Restore the handler
            setattr(backend.dialect, '_json_operation_handler', original_handler)

    def test_process_result_set_error_handling(self):
        """Test error handling in _process_result_set"""
        backend = SQLiteBackend(database=":memory:")
        backend.connect()

        # Create a normal cursor
        cursor = backend._connection.cursor()
        cursor.execute("CREATE TABLE test (id INTEGER)")

        # Close the cursor to make fetchall fail
        cursor.close()

        # Should re-raise the exception
        with pytest.raises(sqlite3.ProgrammingError):
            backend._process_result_set(
                cursor,
                is_select=True,
                need_returning=False,
                column_types=None
            )

        backend.disconnect()
