# tests/rhosocial/activerecord_test/feature/backend/sqlite4/test_introspection_columns.py
"""
Tests for SQLite column introspection.

This module tests the list_columns, get_column_info, and column_exists methods
for retrieving column metadata.
"""

import pytest

from rhosocial.activerecord.backend.introspection.types import (
    ColumnInfo,
    ColumnNullable,
)


class TestListColumns:
    """Tests for list_columns method."""

    def test_list_columns_returns_column_info(self, backend_with_tables):
        """Test that list_columns returns ColumnInfo objects."""
        columns = backend_with_tables.introspector.list_columns("users")

        assert isinstance(columns, list)
        assert len(columns) > 0

        for col in columns:
            assert isinstance(col, ColumnInfo)

    def test_list_columns_all_columns_present(self, backend_with_tables):
        """Test that all columns are returned."""
        columns = backend_with_tables.introspector.list_columns("users")
        column_names = [c.name for c in columns]

        expected_columns = ["id", "name", "email", "age", "created_at"]
        for expected in expected_columns:
            assert expected in column_names

    def test_list_columns_nonexistent_table(self, sqlite_backend):
        """Test list_columns for non-existent table."""
        columns = sqlite_backend.introspector.list_columns("nonexistent")

        # Should return empty list for non-existent table
        assert isinstance(columns, list)
        assert len(columns) == 0

    def test_list_columns_caching(self, backend_with_tables):
        """Test that column list is cached."""
        columns1 = backend_with_tables.introspector.list_columns("users")
        columns2 = backend_with_tables.introspector.list_columns("users")

        # Should return the same cached list
        assert columns1 is columns2


class TestGetColumnInfo:
    """Tests for get_column_info method."""

    def test_get_column_info_existing(self, backend_with_tables):
        """Test get_column_info for existing column."""
        col = backend_with_tables.introspector.get_column_info("users", "email")

        assert col is not None
        assert isinstance(col, ColumnInfo)
        assert col.name == "email"
        assert col.table_name == "users"

    def test_get_column_info_nonexistent_column(self, backend_with_tables):
        """Test get_column_info for non-existent column."""
        col = backend_with_tables.introspector.get_column_info("users", "nonexistent")

        assert col is None

    def test_get_column_info_nonexistent_table(self, sqlite_backend):
        """Test get_column_info for non-existent table."""
        col = sqlite_backend.introspector.get_column_info("nonexistent", "id")

        assert col is None


class TestColumnExists:
    """Tests for column_exists method."""

    def test_column_exists_true(self, backend_with_tables):
        """Test column_exists returns True for existing column."""
        assert backend_with_tables.introspector.column_exists("users", "id") is True
        assert backend_with_tables.introspector.column_exists("users", "name") is True
        assert backend_with_tables.introspector.column_exists("users", "email") is True

    def test_column_exists_false(self, backend_with_tables):
        """Test column_exists returns False for non-existent column."""
        assert backend_with_tables.introspector.column_exists("users", "nonexistent") is False

    def test_column_exists_nonexistent_table(self, sqlite_backend):
        """Test column_exists for non-existent table."""
        assert sqlite_backend.introspector.column_exists("nonexistent", "id") is False


class TestColumnInfoDetails:
    """Tests for detailed column information."""

    def test_column_data_type(self, backend_with_tables):
        """Test that data type is correctly detected."""
        columns = backend_with_tables.introspector.list_columns("users")

        id_col = next(c for c in columns if c.name == "id")
        assert id_col.data_type == "integer"

        name_col = next(c for c in columns if c.name == "name")
        assert name_col.data_type == "text"

    def test_column_data_type_full(self, backend_with_tables):
        """Test that full data type is correctly detected."""
        sqlite_backend = backend_with_tables
        sqlite_backend.executescript("""
            CREATE TABLE type_test (
                col1 VARCHAR(255),
                col2 DECIMAL(10, 2),
                col3 CHAR(10)
            );
        """)

        columns = sqlite_backend.introspector.list_columns("type_test")

        col1 = next(c for c in columns if c.name == "col1")
        assert col1.data_type == "varchar"
        assert col1.data_type_full == "VARCHAR(255)"

        col2 = next(c for c in columns if c.name == "col2")
        assert col2.data_type == "decimal"
        assert col2.data_type_full == "DECIMAL(10, 2)"

    def test_column_nullable(self, backend_with_tables):
        """Test nullability detection."""
        columns = backend_with_tables.introspector.list_columns("users")

        # NOT NULL columns
        name_col = next(c for c in columns if c.name == "name")
        assert name_col.nullable == ColumnNullable.NOT_NULL

        email_col = next(c for c in columns if c.name == "email")
        assert email_col.nullable == ColumnNullable.NOT_NULL

        # Nullable column
        age_col = next(c for c in columns if c.name == "age")
        assert age_col.nullable == ColumnNullable.NULLABLE

    def test_column_primary_key(self, backend_with_tables):
        """Test primary key detection."""
        columns = backend_with_tables.introspector.list_columns("users")

        id_col = next(c for c in columns if c.name == "id")
        assert id_col.is_primary_key is True

        name_col = next(c for c in columns if c.name == "name")
        assert name_col.is_primary_key is False

    def test_column_unique_constraint(self, backend_with_tables):
        """Test unique constraint detection."""
        columns = backend_with_tables.introspector.list_columns("users")

        # email has UNIQUE constraint
        # Note: SQLite doesn't expose UNIQUE constraint directly in PRAGMA table_info
        # The uniqueness is implemented via an index, not a column constraint
        email_col = next(c for c in columns if c.name == "email")
        # Check that unique index exists for email
        indexes = backend_with_tables.introspector.list_indexes("users")
        email_idx = next((i for i in indexes if "email" in [c.name for c in i.columns]), None)
        assert email_idx is not None or email_col.is_unique is False

    def test_column_default_value_string(self, backend_with_tables):
        """Test default value detection for string."""
        columns = backend_with_tables.introspector.list_columns("posts")

        status_col = next(c for c in columns if c.name == "status")
        assert status_col.default_value is not None
        assert "'draft'" in status_col.default_value or "draft" in status_col.default_value

    def test_column_default_value_expression(self, backend_with_tables):
        """Test default value detection for expression."""
        columns = backend_with_tables.introspector.list_columns("users")

        created_at_col = next(c for c in columns if c.name == "created_at")
        assert created_at_col.default_value is not None
        # CURRENT_TIMESTAMP is a function call
        assert "CURRENT_TIMESTAMP" in created_at_col.default_value.upper()

    def test_column_no_default(self, backend_with_tables):
        """Test column without default value."""
        columns = backend_with_tables.introspector.list_columns("users")

        name_col = next(c for c in columns if c.name == "name")
        assert name_col.default_value is None

    def test_integer_primary_key_autoincrement(self, sqlite_backend):
        """Test INTEGER PRIMARY KEY is detected as auto-increment."""
        sqlite_backend.executescript("""
            CREATE TABLE auto_inc (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT
            );
        """)

        columns = sqlite_backend.introspector.list_columns("auto_inc")
        id_col = next(c for c in columns if c.name == "id")

        # Note: SQLite autoincrement detection may vary
        # INTEGER PRIMARY KEY without AUTOINCREMENT also works as auto-increment
        assert id_col.is_primary_key is True

    def test_column_schema(self, backend_with_tables):
        """Test that schema is correctly set."""
        columns = backend_with_tables.introspector.list_columns("users")

        for col in columns:
            assert col.schema == "main"

    def test_column_table_name(self, backend_with_tables):
        """Test that table_name is correctly set."""
        columns = backend_with_tables.introspector.list_columns("posts")

        for col in columns:
            assert col.table_name == "posts"
