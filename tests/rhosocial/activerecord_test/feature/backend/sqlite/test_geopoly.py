# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_geopoly.py
"""Tests for SQLite Geopoly polygon geometry support.

Two test categories:
1. Expression construction tests — cover all Geopoly expression parameter
   combinations, edge cases, and errors.
2. Real-world scenario tests — Geopoly in action with SQLiteBackend.
"""

import pytest

from rhosocial.activerecord.backend.impl.sqlite import (
    SQLiteDialect,
    SQLiteBackend,
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
# Part 1: Expression Construction Tests — Geopoly support & capability
# =============================================================================

class TestGeopolySupport:
    """Geopoly capability detection."""

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


# =============================================================================
# Part 1: Expression Construction Tests — SQLiteGeopolyCreateVirtualTable
# =============================================================================

class TestSQLiteGeopolyCreateVirtualTableConstruction:
    """100% coverage of SQLiteGeopolyCreateVirtualTable."""

    def test_basic(self):
        expr = SQLiteGeopolyCreateVirtualTable(
            SQLiteDialect(version=(3, 26, 0)),
            table_name="zones"
        )
        sql, params = expr.to_sql()
        assert sql == 'CREATE VIRTUAL TABLE "zones" USING geopoly()'
        assert params == ()

    def test_with_content_table(self):
        sql, _ = SQLiteGeopolyCreateVirtualTable(
            SQLiteDialect(version=(3, 26, 0)),
            table_name="zones", content_table="zones_data"
        ).to_sql()
        assert "content='zones_data'" in sql

    def test_with_extra_columns(self):
        sql, _ = SQLiteGeopolyCreateVirtualTable(
            SQLiteDialect(version=(3, 26, 0)),
            table_name="zones", extra_columns=["name", "category"]
        ).to_sql()
        assert sql == (
            'CREATE VIRTUAL TABLE "zones" USING geopoly('
            '"name", "category"'
            ')'
        )

    def test_with_extra_columns_and_content(self):
        sql, _ = SQLiteGeopolyCreateVirtualTable(
            SQLiteDialect(version=(3, 26, 0)),
            table_name="zones", extra_columns=["name"],
            content_table="zones_data"
        ).to_sql()
        assert '"name"' in sql
        assert "content='zones_data'" in sql

    def test_empty_extra_columns(self):
        expr = SQLiteGeopolyCreateVirtualTable(
            SQLiteDialect(version=(3, 26, 0)),
            table_name="zones", extra_columns=[]
        )
        sql, _ = expr.to_sql()
        assert sql == 'CREATE VIRTUAL TABLE "zones" USING geopoly()'

    def test_special_chars_in_extra_columns(self):
        sql, _ = SQLiteGeopolyCreateVirtualTable(
            SQLiteDialect(version=(3, 26, 0)),
            table_name="zones", extra_columns=['col"name']
        ).to_sql()
        assert '"col""name"' in sql

    def test_unsupported_version_raises_error(self):
        expr = SQLiteGeopolyCreateVirtualTable(
            SQLiteDialect(version=(3, 25, 0)),
            table_name="zones"
        )
        with pytest.raises(UnsupportedFeatureError) as exc:
            expr.to_sql()
        assert "Geopoly" in str(exc.value)


# =============================================================================
# Part 1: Expression Construction Tests — SQLiteGeopolyContainsExpression
# =============================================================================

class TestSQLiteGeopolyContainsExpressionConstruction:
    """100% coverage of SQLiteGeopolyContainsExpression."""

    def test_basic(self):
        sql, params = SQLiteGeopolyContainsExpression(
            SQLiteDialect(version=(3, 26, 0)),
            table_name="zones", longitude=1.5, latitude=2.5
        ).to_sql()
        assert sql == (
            'SELECT * FROM "zones" WHERE geopoly_contains_point(_shape, ?, ?)'
        )
        assert params == (1.5, 2.5)

    def test_negative_coordinates(self):
        sql, params = SQLiteGeopolyContainsExpression(
            SQLiteDialect(version=(3, 26, 0)),
            table_name="zones", longitude=-73.95, latitude=40.78
        ).to_sql()
        assert params == (-73.95, 40.78)

    def test_zero_coordinates(self):
        sql, params = SQLiteGeopolyContainsExpression(
            SQLiteDialect(version=(3, 26, 0)),
            table_name="zones", longitude=0.0, latitude=0.0
        ).to_sql()
        assert params == (0.0, 0.0)

    def test_special_chars_in_table_name(self):
        sql, _ = SQLiteGeopolyContainsExpression(
            SQLiteDialect(version=(3, 26, 0)),
            table_name='my"zones', longitude=1.0, latitude=2.0
        ).to_sql()
        assert '"my""zones"' in sql


# =============================================================================
# Part 1: Expression Construction Tests — SQLiteGeopolyAreaExpression
# =============================================================================

class TestSQLiteGeopolyAreaExpressionConstruction:
    """100% coverage of SQLiteGeopolyAreaExpression."""

    def test_basic(self):
        sql, params = SQLiteGeopolyAreaExpression(
            SQLiteDialect(version=(3, 26, 0)),
            table_name="zones"
        ).to_sql()
        assert sql == (
            'SELECT *, geopoly_area(_shape) as area FROM "zones"'
        )
        assert params == ()

    def test_special_chars_in_table_name(self):
        sql, _ = SQLiteGeopolyAreaExpression(
            SQLiteDialect(version=(3, 26, 0)),
            table_name='my"zones'
        ).to_sql()
        assert '"my""zones"' in sql


# =============================================================================
# Part 2: Real-World Scenario Tests — Geopoly with SQLiteBackend
# =============================================================================

class TestGeopolyScenario:
    """Real Geopoly scenarios executed against in-memory SQLite."""

    @pytest.fixture
    def backend(self):
        b = SQLiteBackend(database=":memory:")
        b.connect()
        b.introspect_and_adapt()
        yield b
        b.disconnect()

    def test_create_and_contains_query(self, backend):
        dialect = backend.dialect
        if not dialect.supports_geopoly():
            pytest.skip("Geopoly not available in this SQLite build")

        sql, _ = SQLiteGeopolyCreateVirtualTable(
            dialect, table_name="zones", extra_columns=["name"]
        ).to_sql()
        backend.execute(sql, options=ExecutionOptions(stmt_type=StatementType.DDL))

        insert = ExecutionOptions(stmt_type=StatementType.INSERT)
        backend.execute(
            "INSERT INTO zones(name, _shape) VALUES (?, geopoly_regular(?, ?, ?, ?))",
            ("hexagon", 0.0, 0.0, 3.0, 6), options=insert
        )

        rows = backend.fetch_all("SELECT name FROM zones WHERE geopoly_contains_point(_shape, ?, ?)",
                                 (0.0, 0.0))
        assert len(rows) == 1
        assert rows[0]["name"] == "hexagon"

    def test_point_outside_polygon(self, backend):
        dialect = backend.dialect
        if not dialect.supports_geopoly():
            pytest.skip("Geopoly not available in this SQLite build")

        sql, _ = SQLiteGeopolyCreateVirtualTable(
            dialect, table_name="zones", extra_columns=["name"]
        ).to_sql()
        backend.execute(sql, options=ExecutionOptions(stmt_type=StatementType.DDL))

        insert = ExecutionOptions(stmt_type=StatementType.INSERT)
        backend.execute(
            "INSERT INTO zones(name, _shape) VALUES (?, geopoly_regular(?, ?, ?, ?))",
            ("hexagon", 0.0, 0.0, 3.0, 6), options=insert
        )

        rows = backend.fetch_all("SELECT name FROM zones WHERE geopoly_contains_point(_shape, ?, ?)",
                                 (10.0, 10.0))
        assert len(rows) == 0

    def test_area_calculation(self, backend):
        dialect = backend.dialect
        if not dialect.supports_geopoly():
            pytest.skip("Geopoly not available in this SQLite build")

        sql, _ = SQLiteGeopolyCreateVirtualTable(
            dialect, table_name="zones", extra_columns=["name"]
        ).to_sql()
        backend.execute(sql, options=ExecutionOptions(stmt_type=StatementType.DDL))

        insert = ExecutionOptions(stmt_type=StatementType.INSERT)
        backend.execute(
            "INSERT INTO zones(name, _shape) VALUES (?, geopoly_regular(?, ?, ?, ?))",
            ("hexagon", 0.0, 0.0, 3.0, 6), options=insert
        )

        rows = backend.fetch_all("SELECT geopoly_area(_shape) as area FROM zones")
        assert len(rows) == 1
        assert rows[0]["area"] > 0
