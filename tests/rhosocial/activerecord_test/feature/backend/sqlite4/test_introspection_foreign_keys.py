# tests/rhosocial/activerecord_test/feature/backend/sqlite4/test_introspection_foreign_keys.py
"""
Tests for SQLite foreign key introspection.

This module tests the list_foreign_keys and get_foreign_key_info methods
for retrieving foreign key metadata.
"""

import pytest

from rhosocial.activerecord.backend.introspection.types import (
    ForeignKeyInfo,
    ReferentialAction,
)


class TestListForeignKeys:
    """Tests for list_foreign_keys method."""

    def test_list_foreign_keys_returns_fk_info(self, backend_with_tables):
        """Test that list_foreign_keys returns ForeignKeyInfo objects."""
        fks = backend_with_tables.introspector.list_foreign_keys("posts")

        assert isinstance(fks, list)
        assert len(fks) > 0

        for fk in fks:
            assert isinstance(fk, ForeignKeyInfo)

    def test_list_foreign_keys_posts_table(self, backend_with_tables):
        """Test foreign keys on posts table."""
        fks = backend_with_tables.introspector.list_foreign_keys("posts")

        assert len(fks) >= 1

        # Find the user_id foreign key
        user_fk = next((fk for fk in fks if fk.referenced_table == "users"), None)
        assert user_fk is not None
        assert "user_id" in user_fk.columns

    def test_list_foreign_keys_post_tags_table(self, backend_with_tables):
        """Test foreign keys on post_tags table (composite FKs)."""
        fks = backend_with_tables.introspector.list_foreign_keys("post_tags")

        assert len(fks) == 2

        referenced_tables = {fk.referenced_table for fk in fks}
        assert "posts" in referenced_tables
        assert "tags" in referenced_tables

    def test_list_foreign_keys_no_fks(self, backend_with_tables):
        """Test list_foreign_keys for table without foreign keys."""
        fks = backend_with_tables.introspector.list_foreign_keys("users")

        # users table has no foreign keys
        assert isinstance(fks, list)
        assert len(fks) == 0

    def test_list_foreign_keys_nonexistent_table(self, sqlite_backend):
        """Test list_foreign_keys for non-existent table."""
        fks = sqlite_backend.introspector.list_foreign_keys("nonexistent")

        # Should return empty list for non-existent table
        assert isinstance(fks, list)
        assert len(fks) == 0

    def test_list_foreign_keys_caching(self, backend_with_tables):
        """Test that foreign key list is cached."""
        fks1 = backend_with_tables.introspector.list_foreign_keys("posts")
        fks2 = backend_with_tables.introspector.list_foreign_keys("posts")

        # Should return the same cached list
        assert fks1 is fks2


class TestGetForeignKeyInfo:
    """Tests for get_foreign_key_info method."""

    def test_get_foreign_key_info_existing(self, backend_with_tables):
        """Test get_foreign_key_info for existing FK."""
        # Get all FKs first to find the name
        fks = backend_with_tables.introspector.list_foreign_keys("posts")
        assert len(fks) > 0

        fk_name = fks[0].name
        fk = backend_with_tables.introspector.get_foreign_key_info("posts", fk_name)

        assert fk is not None
        assert isinstance(fk, ForeignKeyInfo)
        assert fk.name == fk_name

    def test_get_foreign_key_info_nonexistent(self, backend_with_tables):
        """Test get_foreign_key_info for non-existent FK."""
        fk = backend_with_tables.introspector.get_foreign_key_info("posts", "nonexistent")

        assert fk is None


class TestForeignKeyDetails:
    """Tests for detailed foreign key information."""

    def test_foreign_key_referenced_table(self, backend_with_tables):
        """Test referenced table detection."""
        fks = backend_with_tables.introspector.list_foreign_keys("posts")

        user_fk = next((fk for fk in fks if fk.referenced_table == "users"), None)
        assert user_fk is not None

    def test_foreign_key_referenced_columns(self, backend_with_tables):
        """Test referenced columns detection."""
        fks = backend_with_tables.introspector.list_foreign_keys("posts")

        user_fk = next((fk for fk in fks if fk.referenced_table == "users"), None)
        assert user_fk is not None
        assert len(user_fk.referenced_columns) == 1
        assert user_fk.referenced_columns[0] == "id"

    def test_foreign_key_on_delete_cascade(self, backend_with_tables):
        """Test ON DELETE CASCADE detection."""
        fks = backend_with_tables.introspector.list_foreign_keys("posts")

        user_fk = next((fk for fk in fks if fk.referenced_table == "users"), None)
        assert user_fk is not None
        assert user_fk.on_delete == ReferentialAction.CASCADE

    def test_foreign_key_on_delete_no_action(self, backend_with_tables):
        """Test ON DELETE NO ACTION detection."""
        fks = backend_with_tables.introspector.list_foreign_keys("posts")

        user_fk = next((fk for fk in fks if fk.referenced_table == "users"), None)
        assert user_fk is not None
        assert user_fk.on_update == ReferentialAction.NO_ACTION

    def test_foreign_key_on_delete_default(self, backend_with_tables):
        """Test default ON DELETE action."""
        fks = backend_with_tables.introspector.list_foreign_keys("post_tags")

        # Default action should be NO ACTION or CASCADE (as defined in schema)
        for fk in fks:
            # Check that on_delete is a valid ReferentialAction enum
            assert hasattr(fk.on_delete, 'value')
            assert fk.on_delete.value in ("CASCADE", "NO ACTION")

    def test_foreign_key_schema(self, backend_with_tables):
        """Test that schema is correctly set."""
        fks = backend_with_tables.introspector.list_foreign_keys("posts")

        for fk in fks:
            assert fk.schema == "main"

    def test_foreign_key_table_name(self, backend_with_tables):
        """Test that table_name is correctly set."""
        fks = backend_with_tables.introspector.list_foreign_keys("posts")

        for fk in fks:
            assert fk.table_name == "posts"

    def test_composite_foreign_key_columns(self, sqlite_backend):
        """Test composite foreign key columns."""
        sqlite_backend.executescript("""
            CREATE TABLE parent (
                col1 INTEGER NOT NULL,
                col2 INTEGER NOT NULL,
                PRIMARY KEY (col1, col2)
            );

            CREATE TABLE child (
                id INTEGER PRIMARY KEY,
                parent_col1 INTEGER NOT NULL,
                parent_col2 INTEGER NOT NULL,
                FOREIGN KEY (parent_col1, parent_col2)
                    REFERENCES parent(col1, col2)
            );
        """)

        fks = sqlite_backend.introspector.list_foreign_keys("child")

        assert len(fks) == 1
        fk = fks[0]

        assert len(fk.columns) == 2
        assert len(fk.referenced_columns) == 2

        assert fk.columns == ["parent_col1", "parent_col2"]
        assert fk.referenced_columns == ["col1", "col2"]


class TestForeignKeyEnforcement:
    """Tests related to foreign key enforcement."""

    def test_foreign_keys_not_enforced_by_default(self, sqlite_backend):
        """Test that foreign keys can be introspected even when not enforced."""
        # SQLite doesn't enforce FK by default, but they should still be introspected
        sqlite_backend.executescript("""
            CREATE TABLE ref_table (
                id INTEGER PRIMARY KEY
            );

            CREATE TABLE main_table (
                id INTEGER PRIMARY KEY,
                ref_id INTEGER,
                FOREIGN KEY (ref_id) REFERENCES ref_table(id)
            );
        """)

        fks = sqlite_backend.introspector.list_foreign_keys("main_table")

        assert len(fks) == 1
        assert fks[0].referenced_table == "ref_table"
