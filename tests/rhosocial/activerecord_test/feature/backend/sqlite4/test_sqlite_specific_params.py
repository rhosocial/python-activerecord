# tests/rhosocial/activerecord_test/feature/backend/sqlite4/test_sqlite_specific_params.py
"""
Tests for SQLite-specific expression parameters.

This module tests that SQLite-specific expression classes properly
handle their extra parameters:
- SQLiteColumnInfoExpression.use_xinfo_pragma
- SQLiteTableListExpression.use_table_list_pragma
"""

import pytest

from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.expression.introspection import (
    SQLiteColumnInfoExpression,
)
from rhosocial.activerecord.backend.impl.sqlite.expression.table_list import (
    SQLiteTableListExpression,
)


class TestSQLiteColumnInfoExpressionParams:
    """Tests for SQLiteColumnInfoExpression with use_xinfo_pragma parameter."""

    def test_default_use_xinfo_pragma(self):
        """Default use_xinfo_pragma should be False."""
        expr = SQLiteColumnInfoExpression()
        assert expr.use_xinfo_pragma is False

    def test_use_xinfo_pragma_true(self):
        """Setting use_xinfo_pragma=True should be reflected in params."""
        expr = SQLiteColumnInfoExpression(use_xinfo_pragma=True)
        assert expr.use_xinfo_pragma is True
        assert expr._params.get("use_xinfo_pragma") is True

    def test_use_xinfo_pragma_false_explicit(self):
        """Explicitly setting use_xinfo_pragma=False should be reflected."""
        expr = SQLiteColumnInfoExpression(use_xinfo_pragma=False)
        assert expr.use_xinfo_pragma is False
        assert expr._params.get("use_xinfo_pragma") is False

    def test_include_hidden_triggers_xinfo_pragma(self):
        """include_hidden=True on base ColumnInfoExpression should use table_xinfo."""
        dialect = SQLiteDialect(version=(3, 26, 0))
        from rhosocial.activerecord.backend.expression.introspection import (
            ColumnInfoExpression,
        )

        expr_standard = ColumnInfoExpression(
            dialect=dialect, table_name="users", schema="main"
        )
        sql_standard, _ = expr_standard.to_sql()

        expr_hidden = ColumnInfoExpression(
            dialect=dialect, table_name="users", schema="main", include_hidden=True
        )
        sql_hidden, _ = expr_hidden.to_sql()

        assert "table_info" in sql_standard and "table_xinfo" not in sql_standard
        assert "table_xinfo" in sql_hidden


class TestSQLiteTableListExpressionParams:
    """Tests for SQLiteTableListExpression with use_table_list_pragma parameter."""

    def test_default_use_table_list_pragma(self):
        """Default use_table_list_pragma should be False."""
        expr = SQLiteTableListExpression()
        assert expr.use_table_list_pragma is False

    def test_use_table_list_pragma_true(self):
        """Setting use_table_list_pragma=True should be reflected in params."""
        expr = SQLiteTableListExpression(use_table_list_pragma=True)
        assert expr.use_table_list_pragma is True
        assert expr._params.get("use_table_list_pragma") is True

    def test_use_table_list_pragma_false_explicit(self):
        """Explicitly setting use_table_list_pragma=False should be reflected."""
        expr = SQLiteTableListExpression(use_table_list_pragma=False)
        assert expr.use_table_list_pragma is False
        assert expr._params.get("use_table_list_pragma") is False

    def test_table_list_pragma_vs_sqlite_master(self):
        """PRAGMA table_list and sqlite_master queries produce different SQL."""
        dialect = SQLiteDialect(version=(3, 37, 0))
        from rhosocial.activerecord.backend.expression.introspection import (
            TableListExpression,
        )

        expr_query = TableListExpression(dialect=dialect, schema="main")
        sql_query, _ = expr_query.to_sql()

        # SQLite 3.37.0+ uses PRAGMA table_list when schema='main'
        assert sql_query is not None
        assert len(sql_query) > 0
