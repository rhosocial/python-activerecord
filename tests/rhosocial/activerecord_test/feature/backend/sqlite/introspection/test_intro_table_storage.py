# tests/rhosocial/activerecord_test/feature/backend/sqlite/introspection/test_intro_table_storage.py
"""
Per-table storage introspection for SQLite.

The ``dbstat`` virtual table is a compile-time option, so these tests hold
for both kinds of build: where the library has it, the slots are filled;
where it does not, the family is refused and the slots stay ``None`` rather
than reporting zeroes. The reducer that attributes bytes to tables is
exercised on the rows a dbstat build returns, so the mapping itself is
tested everywhere.
"""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.impl.sqlite.expression.introspection import (
    SQLiteIndexOwnerStatement,
    SQLiteTableStorageStatement,
)
from rhosocial.activerecord.backend.introspection.types import IntrospectionTableInfo


class TestTableStorageCapability:
    """The probe answers, and the answer matches what the statements do."""

    def test_probe_answers_a_boolean(self, sqlite_backend):
        """The probe is a fact about the build, not a negotiation."""
        answered = sqlite_backend.dialect.supports_table_storage_introspection()
        assert isinstance(answered, bool)

    def test_statement_refused_without_dbstat(self, sqlite_backend, monkeypatch):
        """A build without the table refuses, and list_tables stays honest."""
        monkeypatch.setattr(
            sqlite_backend.dialect,
            "supports_table_storage_introspection",
            lambda: False,
        )
        with pytest.raises(UnsupportedFeatureError):
            SQLiteTableStorageStatement(sqlite_backend.dialect, "main").to_sql()

        sqlite_backend.execute("CREATE TABLE t (a INTEGER PRIMARY KEY)")
        tables = {t.name: t for t in sqlite_backend.introspector.list_tables()}
        assert tables["t"].size_bytes is None
        assert tables["t"].data_size_bytes is None
        assert tables["t"].index_size_bytes is None

    def test_statements_render_when_answerable(self, sqlite_backend, monkeypatch):
        """When the build can answer, the questions render as real SQL."""
        monkeypatch.setattr(
            sqlite_backend.dialect,
            "supports_table_storage_introspection",
            lambda: True,
        )
        storage_sql, _ = SQLiteTableStorageStatement(sqlite_backend.dialect, "main").to_sql()
        owner_sql, _ = SQLiteIndexOwnerStatement(sqlite_backend.dialect, "main").to_sql()
        assert "dbstat" in storage_sql.lower()
        assert "sqlite_master" in owner_sql.lower()
        assert "tbl_name" in owner_sql.lower()


class TestTableStorageReduction:
    """The reducer: which bytes belong to which table, and which stay None."""

    ROWS = [
        {"name": "users", "pgsize": 4096},
        {"name": "users", "pgsize": 4096},
        {"name": "idx_users_email", "pgsize": 4096},
        {"name": "idx_users_email", "pgsize": 2048},
        {"name": "logs", "pgsize": 4096},
        # no row for v_users: a view has no btree, so dbstat names none
    ]
    INDEX_ROWS = [{"name": "idx_users_email", "tbl_name": "users"}]

    def test_table_and_its_indexes_are_attributed(self, sqlite_backend):
        """A table's own btree is its data; its indexes' btrees are its index."""
        tables = sqlite_backend.introspector.parse_table_storage(
            [IntrospectionTableInfo(name="users"), IntrospectionTableInfo(name="logs")],
            self.ROWS,
            self.INDEX_ROWS,
        )
        by_name = {t.name: t for t in tables}
        assert by_name["users"].data_size_bytes == 8192
        assert by_name["users"].index_size_bytes == 6144
        assert by_name["users"].size_bytes == 8192 + 6144

    def test_table_without_indexes_has_no_index_slot(self, sqlite_backend):
        """No index means the slot stays None -- not zero, which would claim
        an index of no size rather than no index."""
        tables = sqlite_backend.introspector.parse_table_storage(
            [IntrospectionTableInfo(name="logs")],
            self.ROWS,
            self.INDEX_ROWS,
        )
        assert tables[0].index_size_bytes is None
        assert tables[0].size_bytes == 4096

    def test_object_with_no_btree_keeps_every_slot_none(self, sqlite_backend):
        """A view has no btree; every slot says so rather than reporting 0."""
        tables = sqlite_backend.introspector.parse_table_storage(
            [IntrospectionTableInfo(name="v_users"), IntrospectionTableInfo(name="missing")],
            self.ROWS,
            self.INDEX_ROWS,
        )
        by_name = {t.name: t for t in tables}
        for table in by_name.values():
            assert table.size_bytes is None
            assert table.data_size_bytes is None
            assert table.index_size_bytes is None

    def test_zero_byte_btree_is_a_real_answer(self, sqlite_backend):
        """An empty table's btree is zero bytes, reported as zero."""
        tables = sqlite_backend.introspector.parse_table_storage(
            [IntrospectionTableInfo(name="empty")],
            [{"name": "empty", "pgsize": 0}],
            [],
        )
        assert tables[0].data_size_bytes == 0
        assert tables[0].size_bytes == 0


class TestDatabaseStorageSlots:
    """The database-level slots: freelist fills free space on any build."""

    def test_free_space_is_filled_with_the_engines_own_accounting(self, sqlite_file_backend):
        """``freelist_count × page_size`` is a figure, not a subtraction."""
        sqlite_file_backend.execute("CREATE TABLE t (a INTEGER PRIMARY KEY, b TEXT)")
        for i in range(100):
            sqlite_file_backend.execute("INSERT INTO t (b) VALUES (?)", (f"v{i}",))
        storage = sqlite_file_backend.introspector.status.get_storage_info()
        assert storage.total_size_bytes is not None
        assert storage.data_size_bytes is not None
        assert storage.free_space_bytes is not None
        assert storage.free_space_bytes >= 0

    def test_overview_serializes_the_storage_slots(self, sqlite_backend):
        """to_dict is field-driven: the slots a backend fills are in it."""
        sqlite_backend.execute("CREATE TABLE t (a INTEGER PRIMARY KEY)")
        overview = sqlite_backend.introspector.status.get_overview()
        payload = overview.to_dict()
        assert set(payload) >= {
            "server_version",
            "server_vendor",
            "storage",
            "databases",
            "processes",
            "extensions",
        }
        assert "innodb" not in payload
        assert "wal" not in payload
        storage_keys = set(payload["storage"])
        assert "free_space_bytes" in storage_keys
        assert storage_keys == {
            "total_size_bytes",
            "data_size_bytes",
            "index_size_bytes",
            "log_size_bytes",
            "free_space_bytes",
            "extra",
        }
