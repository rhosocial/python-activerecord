# tests/rhosocial/activerecord_test/feature/backend/sqlite4/test_pragma_introspector.py
"""
Tests for SQLite PRAGMA introspector.

This module tests the SyncPragmaIntrospector class which provides
direct access to SQLite's PRAGMA interface.
"""

import sqlite3

import pytest

from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend


class TestSyncPragmaIntrospectorBasic:
    """Tests for basic PRAGMA operations."""

    def test_pragma_get_journal_mode(self, sqlite_backend):
        """Test getting journal_mode PRAGMA."""
        pragma = sqlite_backend.introspector.pragma
        result = pragma.get("journal_mode")

        assert result is not None
        assert "journal_mode" in result
        assert result["journal_mode"].upper() in ("WAL", "DELETE", "TRUNCATE", "MEMORY")

    def test_pragma_get_with_argument(self, backend_with_tables):
        """Test getting PRAGMA with argument (table_info)."""
        pragma = backend_with_tables.introspector.pragma
        result = pragma.get("table_info", "'users'")

        assert result is not None

    def test_pragma_set_value(self, sqlite_backend):
        """Test setting a PRAGMA value."""
        pragma = sqlite_backend.introspector.pragma

        pragma.set("cache_size", 5000)

        result = pragma.get("cache_size")
        assert result is not None
        assert result["cache_size"] == 5000

    def test_pragma_set_with_schema(self, sqlite_backend):
        """Test setting PRAGMA with schema prefix."""
        pragma = sqlite_backend.introspector.pragma

        pragma.set("cache_size", 2000, schema="main")

        result = pragma.get("cache_size", schema="main")
        assert result is not None

    def test_pragma_execute_returns_list(self, backend_with_tables):
        """Test execute method returns list of dicts."""
        pragma = backend_with_tables.introspector.pragma

        result = pragma.execute("table_info", "'users'")

        assert isinstance(result, list)
        assert len(result) >= 3
        for row in result:
            assert isinstance(row, dict)


class TestSyncPragmaIntrospectorTableInfo:
    """Tests for table_info and table_xinfo PRAGMAs."""

    def test_table_info(self, backend_with_tables):
        """Test table_info returns column information."""
        pragma = backend_with_tables.introspector.pragma

        result = pragma.table_info("users")

        assert isinstance(result, list)
        assert len(result) == 5  # id, name, email, age, created_at

        id_col = result[0]
        assert id_col["name"] == "id"
        assert id_col["pk"] == 1

    def test_table_info_nonexistent_table(self, sqlite_backend):
        """Test table_info for nonexistent table returns empty list."""
        pragma = sqlite_backend.introspector.pragma

        result = pragma.table_info("nonexistent_table")

        assert isinstance(result, list)
        assert len(result) == 0

    def test_table_xinfo(self, backend_with_tables):
        """Test table_xinfo returns column information with hidden columns."""
        pragma = backend_with_tables.introspector.pragma

        if sqlite3.sqlite_version_info < (3, 26, 0):
            pytest.skip("table_xinfo requires SQLite 3.26.0+")

        result = pragma.table_xinfo("users")

        assert isinstance(result, list)
        assert len(result) >= 5

        for col in result:
            assert "hidden" in col

    def test_table_info_with_schema(self, backend_with_tables):
        """Test table_info with schema parameter."""
        pragma = backend_with_tables.introspector.pragma

        result = pragma.table_info("users", schema="main")

        assert isinstance(result, list)
        assert len(result) == 5


class TestSyncPragmaIntrospectorIndexInfo:
    """Tests for index_list, index_info, and index_xinfo PRAGMAs."""

    def test_index_list(self, backend_with_tables):
        """Test index_list returns indexes for a table."""
        pragma = backend_with_tables.introspector.pragma

        result = pragma.index_list("users")

        assert isinstance(result, list)
        assert len(result) >= 2

        index_names = [idx["name"] for idx in result]
        assert "idx_users_email" in index_names

    def test_index_info(self, backend_with_tables):
        """Test index_info returns columns in an index."""
        pragma = backend_with_tables.introspector.pragma

        result = pragma.index_info("idx_users_email")

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["name"] == "email"

    def test_index_info_composite(self, backend_with_tables):
        """Test index_info for composite index."""
        pragma = backend_with_tables.introspector.pragma

        result = pragma.index_info("idx_users_name_age")

        assert isinstance(result, list)
        assert len(result) == 2

        column_names = [col["name"] for col in result]
        assert "name" in column_names
        assert "age" in column_names

    def test_index_xinfo(self, backend_with_tables):
        """Test index_xinfo returns extended index information."""
        pragma = backend_with_tables.introspector.pragma

        if sqlite3.sqlite_version_info < (3, 9, 0):
            pytest.skip("index_xinfo requires SQLite 3.9.0+")

        result = pragma.index_xinfo("idx_users_email")

        assert isinstance(result, list)
        assert len(result) >= 1


class TestSyncPragmaIntrospectorForeignKeyList:
    """Tests for foreign_key_list PRAGMA."""

    def test_foreign_key_list(self, backend_with_tables):
        """Test foreign_key_list returns foreign key information."""
        pragma = backend_with_tables.introspector.pragma

        result = pragma.foreign_key_list("posts")

        assert isinstance(result, list)
        assert len(result) == 1

        fk = result[0]
        assert fk["table"] == "users"
        assert fk["from"] == "user_id"
        assert fk["to"] == "id"

    def test_foreign_key_list_no_fks(self, backend_with_tables):
        """Test foreign_key_list for table without foreign keys."""
        pragma = backend_with_tables.introspector.pragma

        result = pragma.foreign_key_list("users")

        assert isinstance(result, list)
        assert len(result) == 0

    def test_foreign_key_list_composite(self, backend_with_tables):
        """Test foreign_key_list for table with composite foreign keys."""
        pragma = backend_with_tables.introspector.pragma

        result = pragma.foreign_key_list("post_tags")

        assert isinstance(result, list)
        assert len(result) == 2


class TestSyncPragmaIntrospectorTableList:
    """Tests for table_list PRAGMA."""

    def test_table_list(self, backend_with_tables):
        """Test table_list returns all tables."""
        pragma = backend_with_tables.introspector.pragma

        if sqlite3.sqlite_version_info < (3, 37, 0):
            pytest.skip("table_list requires SQLite 3.37.0+")

        result = pragma.table_list()

        assert isinstance(result, list)
        assert len(result) >= 4

        table_names = [t["name"] for t in result]
        assert "users" in table_names
        assert "posts" in table_names

    def test_table_list_with_schema(self, backend_with_tables):
        """Test table_list with schema parameter."""
        pragma = backend_with_tables.introspector.pragma

        if sqlite3.sqlite_version_info < (3, 37, 0):
            pytest.skip("table_list requires SQLite 3.37.0+")

        result = pragma.table_list(schema="main")

        assert isinstance(result, list)


class TestSyncPragmaIntrospectorMaintenance:
    """Tests for maintenance PRAGMAs."""

    def test_integrity_check(self, backend_with_tables):
        """Test integrity_check returns ok for valid database."""
        pragma = backend_with_tables.introspector.pragma

        result = pragma.integrity_check()

        assert isinstance(result, list)
        assert "ok" in result

    def test_integrity_check_with_schema(self, backend_with_tables):
        """Test integrity_check with schema parameter."""
        pragma = backend_with_tables.introspector.pragma

        result = pragma.integrity_check(schema="main")

        assert isinstance(result, list)
        assert "ok" in result

    def test_foreign_key_check(self, backend_with_tables):
        """Test foreign_key_check returns empty for valid FKs."""
        pragma = backend_with_tables.introspector.pragma

        result = pragma.foreign_key_check()

        assert isinstance(result, list)
        assert len(result) == 0

    def test_foreign_key_check_with_table(self, backend_with_tables):
        """Test foreign_key_check for specific table."""
        pragma = backend_with_tables.introspector.pragma

        result = pragma.foreign_key_check(table_name="posts")

        assert isinstance(result, list)

    def test_journal_mode(self, sqlite_backend):
        """Test journal_mode returns current mode."""
        pragma = sqlite_backend.introspector.pragma

        result = pragma.journal_mode()

        assert result is not None
        assert isinstance(result, str)
        assert result.upper() in ("WAL", "DELETE", "TRUNCATE", "MEMORY", "OFF")

    def test_wal_checkpoint(self, sqlite_file_backend):
        """Test wal_checkpoint executes successfully."""
        pragma = sqlite_file_backend.introspector.pragma

        pragma.set("journal_mode", "WAL")

        result = pragma.wal_checkpoint()

        if result is not None:
            assert isinstance(result, dict)

    def test_wal_checkpoint_modes(self, sqlite_file_backend):
        """Test wal_checkpoint with different modes."""
        pragma = sqlite_file_backend.introspector.pragma

        pragma.set("journal_mode", "WAL")

        for mode in ["PASSIVE", "FULL", "RESTART", "TRUNCATE"]:
            result = pragma.wal_checkpoint(mode=mode)
            if result is not None:
                assert isinstance(result, dict)


class TestSyncPragmaIntrospectorSchemaParameter:
    """Tests for schema parameter in PRAGMA operations."""

    def test_table_info_with_temp_schema(self, sqlite_backend):
        """Test table_info with temp schema."""
        # Create temp table
        sqlite_backend.executescript("""
            CREATE TEMP TABLE temp_table (
                id INTEGER PRIMARY KEY,
                name TEXT
            );
        """)

        pragma = sqlite_backend.introspector.pragma

        result = pragma.table_info("temp_table", schema="temp")

        assert isinstance(result, list)
        assert len(result) == 2


class TestPragmaIntrospectorSQLGeneration:
    """Tests for PRAGMA SQL generation helpers."""

    def test_pragma_sql_without_argument(self):
        """Test _pragma_sql generates correct SQL without argument."""
        from rhosocial.activerecord.backend.impl.sqlite.introspection.pragma_introspector import PragmaMixin

        sql, params = PragmaMixin._pragma_sql("journal_mode")

        assert sql == "PRAGMA journal_mode"
        assert params == ()

    def test_pragma_sql_with_argument(self):
        """Test _pragma_sql generates correct SQL with argument."""
        from rhosocial.activerecord.backend.impl.sqlite.introspection.pragma_introspector import PragmaMixin

        sql, params = PragmaMixin._pragma_sql("table_info", "'users'")

        assert sql == "PRAGMA table_info('users')"
        assert params == ()

    def test_pragma_sql_with_schema(self):
        """Test _pragma_sql generates correct SQL with schema."""
        from rhosocial.activerecord.backend.impl.sqlite.introspection.pragma_introspector import PragmaMixin

        sql, params = PragmaMixin._pragma_sql("journal_mode", schema="main")

        assert sql == "PRAGMA main.journal_mode"
        assert params == ()

    def test_pragma_sql_with_argument_and_schema(self):
        """Test _pragma_sql generates correct SQL with argument and schema."""
        from rhosocial.activerecord.backend.impl.sqlite.introspection.pragma_introspector import PragmaMixin

        sql, params = PragmaMixin._pragma_sql("table_info", "'users'", schema="temp")

        assert sql == "PRAGMA temp.table_info('users')"
        assert params == ()

    def test_set_pragma_sql(self):
        """Test _set_pragma_sql generates correct SQL."""
        from rhosocial.activerecord.backend.impl.sqlite.introspection.pragma_introspector import PragmaMixin

        sql, params = PragmaMixin._set_pragma_sql("cache_size", 5000)

        assert sql == "PRAGMA cache_size = 5000"
        assert params == ()

    def test_set_pragma_sql_with_schema(self):
        """Test _set_pragma_sql generates correct SQL with schema."""
        from rhosocial.activerecord.backend.impl.sqlite.introspection.pragma_introspector import PragmaMixin

        sql, params = PragmaMixin._set_pragma_sql("cache_size", 5000, schema="main")

        assert sql == "PRAGMA main.cache_size = 5000"
        assert params == ()
