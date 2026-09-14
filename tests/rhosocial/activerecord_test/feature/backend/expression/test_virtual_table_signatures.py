# tests/rhosocial/activerecord_test/feature/backend/expression/test_virtual_table_signatures.py
"""Tests for virtual table format method signature compliance.

Verifies:
- format_create_virtual_table accepts a CreateVirtualTableExpression
- format_drop_virtual_table accepts a DropVirtualTableExpression
- 4 tests: create/drop × expression construction + SQL output
"""

import pytest

from rhosocial.activerecord.backend.impl.sqlite import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.expression import (
    CreateVirtualTableExpression,
    DropVirtualTableExpression,
)


@pytest.fixture
def dialect():
    return SQLiteDialect(version=(3, 35, 0))


# =============================================================================
# Part 1: CreateVirtualTableExpression
# =============================================================================


class TestCreateVirtualTableExpression:
    """CreateVirtualTableExpression produces correct SQL."""

    def test_create_basic(self, dialect):
        expr = CreateVirtualTableExpression(
            dialect, module="rtree", table_name="places",
            columns=["id", "minx", "maxx", "miny", "maxy"]
        )
        sql, params = expr.to_sql()
        assert "CREATE VIRTUAL TABLE" in sql
        assert "rtree" in sql
        assert '"places"' in sql
        assert params == ()

    def test_create_rejects_malicious_module(self, dialect):
        with pytest.raises(ValueError, match="Unsafe virtual table module"):
            expr = CreateVirtualTableExpression(
                dialect, module="bad'; DROP TABLE x; --",
                table_name="t", columns=["c"]
            )
            expr.to_sql()


# =============================================================================
# Part 2: DropVirtualTableExpression
# =============================================================================


class TestDropVirtualTableExpression:
    """DropVirtualTableExpression produces correct SQL."""

    def test_drop_basic(self, dialect):
        expr = DropVirtualTableExpression(dialect, table_name="my_table")
        sql, params = expr.to_sql()
        assert sql == 'DROP TABLE "my_table"'
        assert params == ()

    def test_drop_if_exists(self, dialect):
        expr = DropVirtualTableExpression(
            dialect, table_name="my_table", if_exists=True
        )
        sql, params = expr.to_sql()
        assert sql == 'DROP TABLE IF EXISTS "my_table"'
        assert params == ()
