# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_sqlite_operational_maintenance.py
"""Real SQLite operational maintenance tests."""


class TestSQLiteOperationalMaintenance:
    """Synchronous operational tests for SQLite maintenance tasks."""

    def test_integrity_check_reports_ok(self, sqlite_file_backend):
        """PRAGMA integrity_check should report a healthy database."""
        sqlite_file_backend.execute("CREATE TABLE operational_items (id INTEGER PRIMARY KEY, name TEXT)")
        sqlite_file_backend.execute("INSERT INTO operational_items (name) VALUES (?)", ("alpha",))

        row = sqlite_file_backend.fetch_one("PRAGMA integrity_check")
        assert list(row.values())[0] == "ok"

    def test_foreign_keys_pragma_is_enabled(self, sqlite_file_backend):
        """SQLite backend should enable foreign key enforcement via PRAGMA."""
        row = sqlite_file_backend.fetch_one("PRAGMA foreign_keys")
        assert row["foreign_keys"] == 1

    def test_table_and_index_pragmas_reflect_schema(self, sqlite_file_backend):
        """PRAGMA table_info/index_list/index_info should reflect real schema changes."""
        sqlite_file_backend.executescript("""
            CREATE TABLE operational_items (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL
            );
            CREATE INDEX idx_operational_items_category
                ON operational_items(category);
        """)

        columns = sqlite_file_backend.fetch_all("PRAGMA table_info(operational_items)")
        assert {column["name"] for column in columns} == {"id", "name", "category"}

        indexes = sqlite_file_backend.fetch_all("PRAGMA index_list(operational_items)")
        assert any(index["name"] == "idx_operational_items_category" for index in indexes)

        index_columns = sqlite_file_backend.fetch_all("PRAGMA index_info(idx_operational_items_category)")
        assert [column["name"] for column in index_columns] == ["category"]

    def test_vacuum_reindex_and_analyze_keep_table_usable(self, sqlite_file_backend):
        """VACUUM, REINDEX, and ANALYZE should run against a real file database."""
        sqlite_file_backend.executescript("""
            CREATE TABLE operational_items (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL
            );
            CREATE INDEX idx_operational_items_category
                ON operational_items(category);
            INSERT INTO operational_items (name, category)
            VALUES ('alpha', 'a'), ('beta', 'b'), ('gamma', 'a');
        """)

        sqlite_file_backend.execute("ANALYZE")
        sqlite_file_backend.execute("REINDEX idx_operational_items_category")
        sqlite_file_backend.execute("VACUUM")

        count = sqlite_file_backend.fetch_one("SELECT COUNT(*) AS count FROM operational_items")
        assert count["count"] == 3

        stats = sqlite_file_backend.fetch_all("SELECT tbl, idx FROM sqlite_stat1")
        assert any(row["idx"] == "idx_operational_items_category" for row in stats)
