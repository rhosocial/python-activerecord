# tests/rhosocial/activerecord_test/feature/backend/sqlite/extensions/test_geopoly_async.py
"""Async twin of test_geopoly.py: expression construction stays sync; backend scenarios run on AsyncSQLiteBackend."""
import pytest
import pytest_asyncio

from rhosocial.activerecord.backend.impl.sqlite import (
    SQLiteDialect,
    AsyncSQLiteBackend,
)
from rhosocial.activerecord.backend.impl.sqlite.expression import (
    SQLiteGeopolyCreateVirtualTable,
    SQLiteGeopolyContainsExpression,
    SQLiteGeopolyAreaExpression,
)
from rhosocial.activerecord.backend.impl.sqlite.protocols import SQLiteGeopolySupport
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


# =============================================================================
# Part 1: Expression Construction Tests — Geopoly support & capability (sync-only)
# =============================================================================

class TestGeopolySupport:
    """Geopoly capability detection (pure dialect booleans)."""

    def test_implements_protocol(self):
        assert isinstance(SQLiteDialect(), SQLiteGeopolySupport)

    def test_supports_geopoly_version_boundary(self):
        assert not SQLiteDialect(version=(3, 25, 9)).supports_geopoly()
        assert SQLiteDialect(version=(3, 26, 0)).supports_geopoly()
        assert SQLiteDialect(version=(3, 35, 1)).supports_geopoly()

    def test_supports_geopoly_compile_options(self):
        dialect = SQLiteDialect(version=(3, 25, 0))
        dialect.set_runtime_param("compile_options", {"ENABLE_GEOPOLY": True})
        assert dialect.supports_geopoly()
        dialect.set_runtime_param("compile_options", {})
        assert not dialect.supports_geopoly()


class TestSQLiteGeopolyCreateVirtualTableConstruction:
    """100% coverage of SQLiteGeopolyCreateVirtualTable (pure expressions)."""

    def test_basic(self):
        expr = SQLiteGeopolyCreateVirtualTable(
            SQLiteDialect(version=(3, 26, 0)),
            table="zones"
        )
        sql, params = expr.to_sql()
        assert sql == 'CREATE VIRTUAL TABLE "zones" USING geopoly()'
        assert params == ()

    def test_with_content_table(self):
        sql, _ = SQLiteGeopolyCreateVirtualTable(
            SQLiteDialect(version=(3, 26, 0)),
            table="zones", content_table="zones_data"
        ).to_sql()
        assert "content='zones_data'" in sql

    def test_with_extra_columns(self):
        sql, _ = SQLiteGeopolyCreateVirtualTable(
            SQLiteDialect(version=(3, 26, 0)),
            table="zones", extra_columns=["name", "category"]
        ).to_sql()
        assert sql == (
            'CREATE VIRTUAL TABLE "zones" USING geopoly('
            '"name", "category"'
            ')'
        )

    def test_with_extra_columns_and_content(self):
        sql, params = SQLiteGeopolyCreateVirtualTable(
            SQLiteDialect(version=(3, 26, 0)),
            table="zones", extra_columns=["name"],
            content_table="zones_data"
        ).to_sql()
        assert '"name"' in sql
        assert "content='zones_data'" in sql
        assert params == ()

    def test_empty_extra_columns(self):
        expr = SQLiteGeopolyCreateVirtualTable(
            SQLiteDialect(version=(3, 26, 0)),
            table="zones", extra_columns=[]
        )
        sql, _ = expr.to_sql()
        assert sql == 'CREATE VIRTUAL TABLE "zones" USING geopoly()'

    def test_special_chars_in_extra_columns(self):
        sql, _ = SQLiteGeopolyCreateVirtualTable(
            SQLiteDialect(version=(3, 26, 0)),
            table="zones", extra_columns=['col"name']
        ).to_sql()
        assert '"col""name"' in sql

    def test_unsupported_version_raises_error(self):
        expr = SQLiteGeopolyCreateVirtualTable(
            SQLiteDialect(version=(3, 25, 0)),
            table="zones"
        )
        with pytest.raises(UnsupportedFeatureError) as exc:
            expr.to_sql()
        assert "Geopoly" in str(exc.value)


class TestSQLiteGeopolyInjectionSafety:
    """Geopoly expression safety: malicious identifiers must be rejected (pure expressions)."""

    def test_content_table_malicious_identifier_rejected(self):
        with pytest.raises(ValueError, match="Unsafe identifier"):
            SQLiteGeopolyCreateVirtualTable(
                SQLiteDialect(version=(3, 26, 0)),
                table="zones",
                content_table="tab'; DROP TABLE users; --"
            ).to_sql()


class TestSQLiteGeopolyContainsExpressionConstruction:
    """100% coverage of SQLiteGeopolyContainsExpression (pure expressions)."""

    def test_basic(self):
        sql, params = SQLiteGeopolyContainsExpression(
            SQLiteDialect(version=(3, 26, 0)),
            table="zones", longitude=1.5, latitude=2.5
        ).to_sql()
        assert sql == (
            'SELECT * FROM "zones" WHERE geopoly_contains_point(_shape, ?, ?)'
        )
        assert params == (1.5, 2.5)

    def test_negative_coordinates(self):
        sql, params = SQLiteGeopolyContainsExpression(
            SQLiteDialect(version=(3, 26, 0)),
            table="zones", longitude=-73.95, latitude=40.78
        ).to_sql()
        assert params == (-73.95, 40.78)

    def test_zero_coordinates(self):
        sql, params = SQLiteGeopolyContainsExpression(
            SQLiteDialect(version=(3, 26, 0)),
            table="zones", longitude=0.0, latitude=0.0
        ).to_sql()
        assert params == (0.0, 0.0)

    def test_special_chars_in_table_name(self):
        sql, _ = SQLiteGeopolyContainsExpression(
            SQLiteDialect(version=(3, 26, 0)),
            table='my"zones', longitude=1.0, latitude=2.0
        ).to_sql()
        assert '"my""zones"' in sql


class TestSQLiteGeopolyAreaExpressionConstruction:
    """100% coverage of SQLiteGeopolyAreaExpression (pure expressions)."""

    def test_basic(self):
        sql, params = SQLiteGeopolyAreaExpression(
            SQLiteDialect(version=(3, 26, 0)),
            table="zones"
        ).to_sql()
        assert sql == (
            'SELECT *, geopoly_area(_shape) as area FROM "zones"'
        )
        assert params == ()

    def test_special_chars_in_table_name(self):
        sql, _ = SQLiteGeopolyAreaExpression(
            SQLiteDialect(version=(3, 26, 0)),
            table='my"zones'
        ).to_sql()
        assert '"my""zones"' in sql


# =============================================================================
# Part 2: Real-World Scenario Tests — Geopoly with AsyncSQLiteBackend
# =============================================================================

class TestGeopolyScenario:
    """Real Geopoly scenarios executed against in-memory AsyncSQLiteBackend."""

    @pytest_asyncio.fixture
    async def backend(self):
        b = AsyncSQLiteBackend(database=":memory:")
        await b.connect()
        await b.introspect_and_adapt()
        yield b
        await b.disconnect()

    @pytest.mark.asyncio
    async def test_create_and_contains_query(self, backend):
        dialect = backend.dialect
        if not dialect.supports_geopoly():
            pytest.skip("Geopoly not available in this SQLite build")

        sql, _ = SQLiteGeopolyCreateVirtualTable(
            dialect, table="zones", extra_columns=["name"]
        ).to_sql()
        await backend.execute(sql, options=ExecutionOptions(stmt_type=StatementType.DDL))

        insert = ExecutionOptions(stmt_type=StatementType.INSERT)
        await backend.execute(
            "INSERT INTO zones(name, _shape) VALUES (?, geopoly_regular(?, ?, ?, ?))",
            ("hexagon", 0.0, 0.0, 3.0, 6), options=insert
        )

        rows = await backend.fetch_all(
            "SELECT name FROM zones WHERE geopoly_contains_point(_shape, ?, ?)", (0.0, 0.0)
        )
        assert len(rows) == 1
        assert rows[0]["name"] == "hexagon"

    @pytest.mark.asyncio
    async def test_point_outside_polygon(self, backend):
        dialect = backend.dialect
        if not dialect.supports_geopoly():
            pytest.skip("Geopoly not available in this SQLite build")

        sql, _ = SQLiteGeopolyCreateVirtualTable(
            dialect, table="zones", extra_columns=["name"]
        ).to_sql()
        await backend.execute(sql, options=ExecutionOptions(stmt_type=StatementType.DDL))

        insert = ExecutionOptions(stmt_type=StatementType.INSERT)
        await backend.execute(
            "INSERT INTO zones(name, _shape) VALUES (?, geopoly_regular(?, ?, ?, ?))",
            ("hexagon", 0.0, 0.0, 3.0, 6), options=insert
        )

        rows = await backend.fetch_all(
            "SELECT name FROM zones WHERE geopoly_contains_point(_shape, ?, ?)", (10.0, 10.0)
        )
        assert len(rows) == 0

    @pytest.mark.asyncio
    async def test_area_calculation(self, backend):
        dialect = backend.dialect
        if not dialect.supports_geopoly():
            pytest.skip("Geopoly not available in this SQLite build")

        sql, _ = SQLiteGeopolyCreateVirtualTable(
            dialect, table="zones", extra_columns=["name"]
        ).to_sql()
        await backend.execute(sql, options=ExecutionOptions(stmt_type=StatementType.DDL))

        insert = ExecutionOptions(stmt_type=StatementType.INSERT)
        await backend.execute(
            "INSERT INTO zones(name, _shape) VALUES (?, geopoly_regular(?, ?, ?, ?))",
            ("hexagon", 0.0, 0.0, 3.0, 6), options=insert
        )

        rows = await backend.fetch_all("SELECT geopoly_area(_shape) as area FROM zones")
        assert len(rows) == 1
        assert rows[0]["area"] > 0
