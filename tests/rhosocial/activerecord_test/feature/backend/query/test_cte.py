# tests/rhosocial/activerecord_test/feature/backend/query/test_cte.py
"""CTE capability gating and WITH-clause formatting on the dialect layer.

Covers the CTESupport protocol surface (supports_basic/recursive/materialized_cte
version gating) and the pure formatting helpers format_cte / format_with_clause /
format_with_query. Expression-level coverage lives in test_cte_expression.py and
test_with_query_expression.py; real-execution coverage in test_cte_integration.py.
"""

import pytest

from rhosocial.activerecord.backend.dialect import CTESupport
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


class TestCTECapabilityProtocol:
    """CTESupport protocol conformance."""

    def test_dummy_dialect_implements_protocol(self):
        assert isinstance(DummyDialect(), CTESupport)

    def test_sqlite_dialect_implements_protocol(self):
        assert isinstance(SQLiteDialect(), CTESupport)

    def test_dummy_supports_all_cte_features(self):
        d = DummyDialect()
        assert d.supports_basic_cte() is True
        assert d.supports_recursive_cte() is True
        assert d.supports_materialized_cte() is True


class TestSQLiteCTEVersionGating:
    """SQLite feature gates by version (CTE since 3.8.3, MATERIALIZED since 3.35.0)."""

    def test_basic_cte_before_3_8_3(self):
        d = SQLiteDialect(version=(3, 8, 0))
        assert d.supports_basic_cte() is False
        assert d.supports_recursive_cte() is False

    def test_basic_cte_at_3_8_3(self):
        d = SQLiteDialect(version=(3, 8, 3))
        assert d.supports_basic_cte() is True
        assert d.supports_recursive_cte() is True

    def test_materialized_cte_before_3_35_0(self):
        d = SQLiteDialect(version=(3, 34, 0))
        assert d.supports_materialized_cte() is False

    def test_materialized_cte_at_3_35_0(self):
        d = SQLiteDialect(version=(3, 35, 0))
        assert d.supports_materialized_cte() is True


class TestFormatCTE:
    """format_cte name/columns/materialized rendering."""

    def test_basic(self):
        assert DummyDialect().format_cte("monthly", "SELECT 1") == '"monthly" AS (SELECT 1)'

    def test_with_columns(self):
        assert DummyDialect().format_cte("t", "SELECT 1", columns=["a", "b"]) == '"t" ("a", "b") AS (SELECT 1)'

    def test_materialized(self):
        assert DummyDialect().format_cte("t", "SELECT 1", materialized=True) == '"t" AS MATERIALIZED (SELECT 1)'

    def test_not_materialized(self):
        assert DummyDialect().format_cte("t", "SELECT 1", materialized=False) == '"t" AS NOT MATERIALIZED (SELECT 1)'

    def test_identifier_quoted(self):
        assert DummyDialect().format_cte("order data", "SELECT 1") == '"order data" AS (SELECT 1)'


class TestFormatWithClause:
    """format_with_clause / format_with_query rendering."""

    def test_single_cte(self):
        assert DummyDialect().format_with_clause(['a AS (SELECT 1)']) == 'WITH a AS (SELECT 1)'

    def test_multiple_ctes(self):
        parts = ['a AS (SELECT 1)', 'b AS (SELECT 2)']
        assert DummyDialect().format_with_clause(parts) == 'WITH a AS (SELECT 1), b AS (SELECT 2)'

    def test_recursive(self):
        parts = ['a AS (SELECT 1)']
        assert DummyDialect().format_with_clause(parts, has_recursive=True) == 'WITH RECURSIVE a AS (SELECT 1)'

    def test_empty(self):
        assert DummyDialect().format_with_clause([]) == ""

    def test_with_query_combines(self):
        d = DummyDialect()
        assert d.format_with_query(['a AS (SELECT 1)'], 'SELECT * FROM a') == 'WITH a AS (SELECT 1) SELECT * FROM a'

    def test_with_query_no_ctes_returns_main(self):
        assert DummyDialect().format_with_query([], 'SELECT 1') == 'SELECT 1'

    def test_with_query_recursive(self):
        d = DummyDialect()
        assert d.format_with_query(['a AS (SELECT 1)'], 'SELECT * FROM a', has_recursive=True) == (
            'WITH RECURSIVE a AS (SELECT 1) SELECT * FROM a'
        )