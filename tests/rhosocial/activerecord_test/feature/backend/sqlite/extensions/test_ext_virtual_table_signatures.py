# tests/rhosocial/activerecord_test/feature/backend/sqlite/extensions/test_ext_virtual_table_signatures.py
"""Tests for virtual table format method signature compliance.

Verifies:
- format_create_virtual_table_statement accepts a SQLiteCreateVirtualTableStatement
- format_drop_virtual_table_statement accepts a SQLiteDropVirtualTableStatement
- 4 tests: create/drop × expression construction + SQL output
"""

import pytest

from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.expression import (
    SQLiteCreateVirtualTableStatement,
    SQLiteDropVirtualTableStatement,
)
from rhosocial.activerecord.backend.expression.objects import Table


@pytest.fixture
def dialect():
    return SQLiteDialect(version=(3, 35, 0))


# =============================================================================
# Part 1: SQLiteCreateVirtualTableStatement
# =============================================================================


class TestCreateVirtualTableExpression:
    """SQLiteCreateVirtualTableStatement produces correct SQL."""

    def test_create_basic(self, dialect):
        expr = SQLiteCreateVirtualTableStatement(
            dialect, module="rtree", table=Table(dialect, "places"),
            columns=["id", "minx", "maxx", "miny", "maxy"]
        )
        sql, params = expr.to_sql()
        assert "CREATE VIRTUAL TABLE" in sql
        assert "rtree" in sql
        assert '"places"' in sql
        assert params == ()

    def test_create_rejects_malicious_module(self, dialect):
        with pytest.raises(ValueError, match="Unsafe virtual table module"):
            expr = SQLiteCreateVirtualTableStatement(
                dialect, module="bad'; DROP TABLE x; --",
                table=Table(dialect, "t"), columns=["c"]
            )
            expr.to_sql()


# =============================================================================
# Part 2: SQLiteDropVirtualTableStatement
# =============================================================================


class TestDropVirtualTableExpression:
    """SQLiteDropVirtualTableStatement produces correct SQL."""

    def test_drop_basic(self, dialect):
        expr = SQLiteDropVirtualTableStatement(dialect, table=Table(dialect, "my_table"))
        sql, params = expr.to_sql()
        assert sql == 'DROP TABLE "my_table"'
        assert params == ()

    def test_drop_if_exists(self, dialect):
        expr = SQLiteDropVirtualTableStatement(
            dialect, table=Table(dialect, "my_table"), if_exists=True
        )
        sql, params = expr.to_sql()
        assert sql == 'DROP TABLE IF EXISTS "my_table"'
        assert params == ()
