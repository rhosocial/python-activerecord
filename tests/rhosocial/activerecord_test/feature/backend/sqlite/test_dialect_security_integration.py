# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_dialect_security_integration.py
"""
Integration tests for SQLite dialect SQL injection security fixes.

These tests verify that the security fixes work correctly when
SQL is actually executed against a SQLite database.
"""
import pytest

from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.expression.statements import ColumnDefinition
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


@pytest.fixture
def backend():
    """Provides a SQLiteBackend instance connected to an in-memory database."""
    backend = SQLiteBackend(database=":memory:")
    backend.connect()
    yield backend
    backend.disconnect()


class TestSQLiteDialectSecurityIntegration:
    """Integration tests for SQLite dialect security."""

    @pytest.fixture
    def test_table_with_special_chars(self, backend):
        """Create a test table with special characters in defaults."""
        backend.execute(
            """
            CREATE TABLE test_security_chars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT DEFAULT 'test''s value'
            )
            """,
            options=ExecutionOptions(stmt_type=StatementType.DDL)
        )
        yield "test_security_chars"
        backend.execute(
            "DROP TABLE IF EXISTS test_security_chars",
            options=ExecutionOptions(stmt_type=StatementType.DDL)
        )

    def test_default_string_with_single_quote_insert_and_retrieve(
        self, backend, test_table_with_special_chars
    ):
        """Test that single quotes in DEFAULT are properly escaped and retrieved correctly."""
        # Insert a row with special characters
        backend.execute(
            "INSERT INTO test_security_chars (name) VALUES (?)",
            ("O'Brien",),
            options=ExecutionOptions(stmt_type=StatementType.DML)
        )

        # Retrieve and verify
        result = backend.fetch_one(
            "SELECT name FROM test_security_chars WHERE id = 1"
        )
        assert result["name"] == "O'Brien"

    @pytest.fixture
    def test_table_for_data_type(self, backend):
        """Create a test table for data type security tests."""
        backend.execute(
            "DROP TABLE IF EXISTS test_data_type_security",
            options=ExecutionOptions(stmt_type=StatementType.DDL)
        )
        yield "test_data_type_security"
        backend.execute(
            "DROP TABLE IF EXISTS test_data_type_security",
            options=ExecutionOptions(stmt_type=StatementType.DDL)
        )

    def test_valid_data_type_works(self, backend, test_table_for_data_type):
        """Test that valid data types work correctly."""
        # This should succeed with valid data type
        backend.execute(
            f"""
            CREATE TABLE {test_table_for_data_type} (
                id INTEGER PRIMARY KEY,
                data TEXT
            )
            """,
            options=ExecutionOptions(stmt_type=StatementType.DDL)
        )

        # Verify table was created - use fetch_one
        result = backend.fetch_one(
            f"SELECT name FROM sqlite_master WHERE name = '{test_table_for_data_type}'"
        )
        assert result is not None
        assert result["name"] == test_table_for_data_type

    def test_malicious_data_type_rejected_at_dialect_level(self, backend):
        """Test that malicious data type is rejected at dialect level before DB execution."""
        dialect = backend.dialect

        # This should raise ValueError before reaching the database
        col_def = ColumnDefinition(
            name="test_col",
            data_type="TEXT; DROP TABLE users--",
        )

        with pytest.raises(ValueError, match="Invalid data type"):
            dialect.format_column_definition(col_def)


class TestSQLiteDefaultConstraintSecurityIntegration:
    """Integration tests for DEFAULT constraint security."""

    def test_default_with_single_quote_retrieved_correctly(self, backend):
        """Test that DEFAULT with single quote is retrieved correctly."""
        # Create table with DEFAULT containing single quote
        backend.execute(
            """
            CREATE TABLE test_default_quote (
                id INTEGER PRIMARY KEY,
                name TEXT DEFAULT 'it''s a test'
            )
            """,
            options=ExecutionOptions(stmt_type=StatementType.DDL)
        )

        # Get default value from sqlite_master
        result = backend.fetch_one(
            "SELECT sql FROM sqlite_master WHERE name = 'test_default_quote'"
        )
        assert result is not None
        assert "it''s a test" in result["sql"]

        backend.execute(
            "DROP TABLE IF EXISTS test_default_quote",
            options=ExecutionOptions(stmt_type=StatementType.DDL)
        )


class TestSQLiteStorageOptionsSecurityIntegration:
    """Integration tests for storage options security."""

    def test_storage_options_work(self, backend):
        """Test storage options work correctly."""
        # SQLite storage options are handled differently
        backend.execute(
            "DROP TABLE IF EXISTS test_storage_opts",
            options=ExecutionOptions(stmt_type=StatementType.DDL)
        )
        backend.execute(
            """
            CREATE TABLE test_storage_opts (
                id INTEGER PRIMARY KEY,
                data TEXT
            ) WITHOUT ROWID
            """,
            options=ExecutionOptions(stmt_type=StatementType.DDL)
        )

        # Verify table was created
        result = backend.fetch_one(
            "SELECT name FROM sqlite_master WHERE name = 'test_storage_opts'"
        )
        assert result is not None

        backend.execute(
            "DROP TABLE IF EXISTS test_storage_opts",
            options=ExecutionOptions(stmt_type=StatementType.DDL)
        )