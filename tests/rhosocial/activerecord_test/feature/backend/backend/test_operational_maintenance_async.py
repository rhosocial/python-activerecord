# tests/rhosocial/activerecord_test/feature/backend/backend/test_operational_maintenance_async.py
"""Real async SQLite operational maintenance tests."""

import pytest


class TestAsyncSQLiteOperationalMaintenance:
    """Asynchronous operational tests for SQLite maintenance tasks."""

    @pytest.mark.asyncio
    async def test_integrity_check_reports_ok(self, async_sqlite_backend):
        """PRAGMA integrity_check should report a healthy database."""
        await async_sqlite_backend.execute("CREATE TABLE operational_items (id INTEGER PRIMARY KEY, name TEXT)")
        await async_sqlite_backend.execute(
            "INSERT INTO operational_items (name) VALUES (?)",
            ("alpha",),
        )

        row = await async_sqlite_backend.fetch_one("PRAGMA integrity_check")
        assert list(row.values())[0] == "ok"

    @pytest.mark.asyncio
    async def test_foreign_keys_pragma_is_enabled(self, async_sqlite_backend):
        """SQLite backend should enable foreign key enforcement via PRAGMA."""
        row = await async_sqlite_backend.fetch_one("PRAGMA foreign_keys")
        assert row["foreign_keys"] == 1

    @pytest.mark.asyncio
    async def test_table_and_index_pragmas_reflect_schema(self, async_sqlite_backend):
        """PRAGMA table_info/index_list/index_info should reflect real schema changes."""
        await async_sqlite_backend.executescript("""
            CREATE TABLE operational_items (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL
            );
            CREATE INDEX idx_operational_items_category
                ON operational_items(category);
        """)

        columns = await async_sqlite_backend.fetch_all("PRAGMA table_info(operational_items)")
        assert {column["name"] for column in columns} == {"id", "name", "category"}

        indexes = await async_sqlite_backend.fetch_all("PRAGMA index_list(operational_items)")
        assert any(index["name"] == "idx_operational_items_category" for index in indexes)

        index_columns = await async_sqlite_backend.fetch_all("PRAGMA index_info(idx_operational_items_category)")
        assert [column["name"] for column in index_columns] == ["category"]

    @pytest.mark.asyncio
    async def test_vacuum_reindex_and_analyze_keep_table_usable(self, async_sqlite_backend):
        """VACUUM, REINDEX, and ANALYZE should run against a real file database."""
        await async_sqlite_backend.executescript("""
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

        await async_sqlite_backend.execute("ANALYZE")
        await async_sqlite_backend.execute("REINDEX idx_operational_items_category")
        await async_sqlite_backend.execute("VACUUM")

        count = await async_sqlite_backend.fetch_one("SELECT COUNT(*) AS count FROM operational_items")
        assert count["count"] == 3

        stats = await async_sqlite_backend.fetch_all("SELECT tbl, idx FROM sqlite_stat1")
        assert any(row["idx"] == "idx_operational_items_category" for row in stats)
