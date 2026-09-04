# tests/rhosocial/activerecord_test/feature/backend/sqlite/extensions/test_rtree_async.py
"""Async twin of test_rtree.py: expression construction stays sync; backend scenarios run on AsyncSQLiteBackend."""
import pytest
import pytest_asyncio

from rhosocial.activerecord.backend.impl.sqlite import (
    SQLiteDialect,
    AsyncSQLiteBackend,
)
from rhosocial.activerecord.backend.impl.sqlite.expression import (
    SQLiteRTreeCreateVirtualTable,
    SQLiteRTreeRangeQuery,
)
from rhosocial.activerecord.backend.impl.sqlite.protocols import SQLiteRTreeSupport
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


# =============================================================================
# Part 1: Expression Construction Tests — R-Tree support & capability (sync-only)
# =============================================================================

class TestRTreeSupport:
    """R-Tree capability detection (pure dialect booleans)."""

    def test_implements_protocol(self):
        assert isinstance(SQLiteDialect(), SQLiteRTreeSupport)

    def test_supports_rtree_version_boundary(self):
        assert not SQLiteDialect(version=(3, 5, 9)).supports_rtree()
        assert SQLiteDialect(version=(3, 6, 0)).supports_rtree()
        assert SQLiteDialect(version=(3, 35, 1)).supports_rtree()

    def test_supports_rtree_compile_options(self):
        dialect = SQLiteDialect(version=(3, 5, 0))
        dialect.set_runtime_param("compile_options", {"ENABLE_RTREE": True})
        assert dialect.supports_rtree()
        dialect.set_runtime_param("compile_options", {})
        assert not dialect.supports_rtree()


class TestSQLiteRTreeCreateVirtualTableConstruction:
    """100% coverage of SQLiteRTreeCreateVirtualTable (pure expressions)."""

    def test_2d_default(self):
        sql, params = SQLiteRTreeCreateVirtualTable(
            SQLiteDialect(version=(3, 6, 0)),
            table="places"
        ).to_sql()
        assert sql == (
            'CREATE VIRTUAL TABLE "places" USING rtree('
            '"id", "min0", "max0", "min1", "max1"'
            ')'
        )
        assert params == ()

    def test_3d(self):
        sql, _ = SQLiteRTreeCreateVirtualTable(
            SQLiteDialect(version=(3, 6, 0)),
            table="volumes", dimensions=3
        ).to_sql()
        assert '"min0", "max0", "min1", "max1", "min2", "max2"' in sql

    def test_1d(self):
        sql, _ = SQLiteRTreeCreateVirtualTable(
            SQLiteDialect(version=(3, 6, 0)),
            table="intervals", dimensions=1
        ).to_sql()
        assert '"min0", "max0"' in sql

    def test_with_content_table(self):
        sql, params = SQLiteRTreeCreateVirtualTable(
            SQLiteDialect(version=(3, 6, 0)),
            table="places", content_table="places_data"
        ).to_sql()
        assert "content='places_data'" in sql
        assert params == ()

    def test_with_content_rowid(self):
        sql, params = SQLiteRTreeCreateVirtualTable(
            SQLiteDialect(version=(3, 6, 0)),
            table="places", content_table="places_data",
            content_rowid="pk"
        ).to_sql()
        assert "content='places_data'" in sql
        assert "content_rowid='pk'" in sql
        assert params == ()

    def test_content_rowid_without_content(self):
        sql, _ = SQLiteRTreeCreateVirtualTable(
            SQLiteDialect(version=(3, 6, 0)),
            table="places", content_rowid="pk"
        ).to_sql()
        assert "content_rowid" not in sql

    def test_unsupported_version_raises_error(self):
        expr = SQLiteRTreeCreateVirtualTable(
            SQLiteDialect(version=(3, 5, 0)),
            table="places"
        )
        with pytest.raises(UnsupportedFeatureError) as exc:
            expr.to_sql()
        assert "R-Tree" in str(exc.value)


class TestSQLiteRTreeInjectionSafety:
    """R-Tree expression safety: malicious identifiers must be rejected (pure expressions)."""

    def test_content_table_malicious_identifier_rejected(self):
        with pytest.raises(ValueError, match="Unsafe identifier"):
            SQLiteRTreeCreateVirtualTable(
                SQLiteDialect(version=(3, 6, 0)),
                table="places",
                content_table="tab'; DROP TABLE users; --"
            ).to_sql()

    def test_content_rowid_malicious_identifier_rejected(self):
        with pytest.raises(ValueError, match="Unsafe identifier"):
            SQLiteRTreeCreateVirtualTable(
                SQLiteDialect(version=(3, 6, 0)),
                table="places", content_table="x",
                content_rowid="pk'; DROP TABLE t; --"
            ).to_sql()


class TestSQLiteRTreeRangeQueryConstruction:
    """100% coverage of SQLiteRTreeRangeQuery (pure expressions)."""

    def test_2d_range(self):
        sql, params = SQLiteRTreeRangeQuery(
            SQLiteDialect(version=(3, 6, 0)),
            table="places",
            ranges=[(0.0, 10.0), (0.0, 10.0)]
        ).to_sql()
        assert sql == (
            'SELECT * FROM "places" WHERE '
            '"places"."min0" <= ? AND "places"."max0" >= ? AND '
            '"places"."min1" <= ? AND "places"."max1" >= ?'
        )
        assert params == (10.0, 0.0, 10.0, 0.0)

    def test_3d_range(self):
        sql, params = SQLiteRTreeRangeQuery(
            SQLiteDialect(version=(3, 6, 0)),
            table="volumes",
            ranges=[(0, 1), (0, 1), (0, 1)]
        ).to_sql()
        assert params == (1, 0, 1, 0, 1, 0)
        assert '"volumes"."min2"' in sql

    def test_1d_range(self):
        sql, params = SQLiteRTreeRangeQuery(
            SQLiteDialect(version=(3, 6, 0)),
            table="intervals",
            ranges=[(5.0, 10.0)]
        ).to_sql()
        assert sql == (
            'SELECT * FROM "intervals" WHERE '
            '"intervals"."min0" <= ? AND "intervals"."max0" >= ?'
        )
        assert params == (10.0, 5.0)

    def test_with_custom_column_names(self):
        sql, params = SQLiteRTreeRangeQuery(
            SQLiteDialect(version=(3, 6, 0)),
            table="places",
            ranges=[(0.0, 10.0), (0.0, 10.0)],
            column_names=[("x_min", "x_max"), ("y_min", "y_max")]
        ).to_sql()
        assert '"x_min" <= ? AND "x_max" >= ?' in sql
        assert '"y_min" <= ? AND "y_max" >= ?' in sql

    def test_single_custom_column_in_2d(self):
        sql, params = SQLiteRTreeRangeQuery(
            SQLiteDialect(version=(3, 6, 0)),
            table="places",
            ranges=[(0.0, 10.0), (0.0, 10.0)],
            column_names=[("x_min", "x_max")]
        ).to_sql()
        assert '"x_min" <= ? AND "x_max" >= ?' in sql
        assert '"places"."min1"' in sql

    def test_special_chars_in_table_name(self):
        sql, _ = SQLiteRTreeRangeQuery(
            SQLiteDialect(version=(3, 6, 0)),
            table='my"table',
            ranges=[(0.0, 1.0)]
        ).to_sql()
        assert '"my""table"."min0"' in sql


# =============================================================================
# Part 2: Real-World Scenario Tests — R-Tree with AsyncSQLiteBackend
# =============================================================================

class TestRTreeScenario:
    """Real R-Tree scenarios executed against in-memory AsyncSQLiteBackend."""

    @pytest_asyncio.fixture
    async def backend(self):
        b = AsyncSQLiteBackend(database=":memory:")
        await b.connect()
        await b.introspect_and_adapt()
        yield b
        await b.disconnect()

    @pytest.mark.asyncio
    async def test_create_and_query_2d(self, backend):
        dialect = backend.dialect
        if not dialect.supports_rtree():
            pytest.skip("R-Tree not available in this SQLite build")

        sql, _ = SQLiteRTreeCreateVirtualTable(
            dialect, table="places"
        ).to_sql()
        await backend.execute(sql, options=ExecutionOptions(stmt_type=StatementType.DDL))

        insert = ExecutionOptions(stmt_type=StatementType.INSERT)
        await backend.execute("INSERT INTO places VALUES (?, ?, ?, ?, ?)",
                              (1, 0.0, 5.0, 0.0, 5.0), options=insert)
        await backend.execute("INSERT INTO places VALUES (?, ?, ?, ?, ?)",
                              (2, 10.0, 15.0, 10.0, 15.0), options=insert)
        await backend.execute("INSERT INTO places VALUES (?, ?, ?, ?, ?)",
                              (3, 2.0, 3.0, 2.0, 3.0), options=insert)

        rows = await backend.fetch_all(
            "SELECT id FROM places WHERE min0 <= ? AND max0 >= ? AND min1 <= ? AND max1 >= ?",
            (6.0, 0.0, 6.0, 0.0)
        )
        assert len(rows) == 2
        assert {r["id"] for r in rows} == {1, 3}

    @pytest.mark.asyncio
    async def test_3d_volume_query(self, backend):
        dialect = backend.dialect
        if not dialect.supports_rtree():
            pytest.skip("R-Tree not available in this SQLite build")

        sql, _ = SQLiteRTreeCreateVirtualTable(
            dialect, table="boxes", dimensions=3
        ).to_sql()
        await backend.execute(sql, options=ExecutionOptions(stmt_type=StatementType.DDL))

        insert = ExecutionOptions(stmt_type=StatementType.INSERT)
        await backend.execute("INSERT INTO boxes VALUES (?, ?, ?, ?, ?, ?, ?)",
                              (1, 0, 10, 0, 10, 0, 10), options=insert)
        await backend.execute("INSERT INTO boxes VALUES (?, ?, ?, ?, ?, ?, ?)",
                              (2, 20, 30, 20, 30, 20, 30), options=insert)

        rows = await backend.fetch_all(
            "SELECT id FROM boxes WHERE "
            "min0 <= ? AND max0 >= ? AND min1 <= ? AND max1 >= ? AND min2 <= ? AND max2 >= ?",
            (15, 0, 15, 0, 15, 0)
        )
        assert len(rows) == 1
        assert rows[0]["id"] == 1

    @pytest.mark.asyncio
    async def test_create_verify_table_info(self, backend):
        dialect = backend.dialect
        if not dialect.supports_rtree():
            pytest.skip("R-Tree not available in this SQLite build")

        sql, _ = SQLiteRTreeCreateVirtualTable(
            dialect, table="verify_places"
        ).to_sql()
        await backend.execute(sql, options=ExecutionOptions(stmt_type=StatementType.DDL))
        cols = await backend.fetch_all("PRAGMA table_info(verify_places)")
        assert len(cols) == 5  # id + min0 + max0 + min1 + max1

    @pytest.mark.asyncio
    async def test_create_with_content_table_sql(self):
        """Test that SQL generation produces correct content table syntax (pure dialect)."""
        dialect = SQLiteDialect(version=(3, 35, 0))
        sql, _ = SQLiteRTreeCreateVirtualTable(
            dialect, table="places_idx", content_table="places_data"
        ).to_sql()
        assert "content='places_data'" in sql
        assert "rtree" in sql
