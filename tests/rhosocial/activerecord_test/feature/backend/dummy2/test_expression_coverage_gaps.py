# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_expression_coverage_gaps.py
"""
Tests to cover missing lines in expression core/bases/executable/operators modules.
Targets: core.py:69,177 / bases.py:16 / executable.py:35 / operators.py:153
"""

import pytest
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.expression.core import Column, Literal, TableExpression, Subquery
from rhosocial.activerecord.backend.expression.operators import BinaryArithmeticExpression


class TestColumnSchemaName:
    """Cover core.py:69 — Column.to_sql() schema_name branch."""

    def test_column_with_schema_name(self, dummy_dialect):
        col = Column(dummy_dialect, "id", table="users", schema_name="app")
        sql, params = col.to_sql()
        assert '"app"."users"."id"' == sql
        assert params == ()

    def test_column_without_schema_name(self, dummy_dialect):
        col = Column(dummy_dialect, "id", table="users")
        sql, params = col.to_sql()
        assert '"users"."id"' == sql
        assert params == ()


class TestLiteralCastTypes:
    """Cover core.py:39-40 — Literal.to_sql() _cast_types loop."""

    def test_literal_with_single_cast(self, dummy_dialect):
        lit = Literal(dummy_dialect, 42)
        lit.cast("INTEGER")
        sql, params = lit.to_sql()
        assert "CAST" in sql or "INTEGER" in sql

    def test_literal_with_chained_casts(self, dummy_dialect):
        lit = Literal(dummy_dialect, "100")
        lit.cast("money").cast("numeric")
        sql, params = lit.to_sql()
        assert sql  # Verify it doesn't crash


class TestSubqueryCastTypes:
    """Cover core.py:177 — Subquery.to_sql() _cast_types loop.

    Subquery inherits _cast_types from SQLValueExpression but not TypeCastingMixin,
    so we set _cast_types directly to cover the loop.
    """

    def test_subquery_with_cast(self, dummy_dialect):
        subquery = Subquery(dummy_dialect, "SELECT id FROM users")
        subquery._cast_types.append("TEXT")
        sql, params = subquery.to_sql()
        assert "CAST" in sql or "TEXT" in sql


class TestBinaryArithmeticCastTypes:
    """Cover operators.py:153 — BinaryArithmeticExpression _cast_types loop."""

    def test_arithmetic_with_cast(self, dummy_dialect):
        left = Column(dummy_dialect, "price")
        right = Literal(dummy_dialect, 10)
        expr = BinaryArithmeticExpression(dummy_dialect, "+", left, right)
        expr.cast("DECIMAL")
        sql, params = expr.to_sql()
        assert "CAST" in sql or "DECIMAL" in sql


class TestExecutableProtocol:
    """Cover executable.py:35 — Executable protocol statement_type property."""

    def test_executable_protocol_isinstance_check(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.executable import Executable
        from rhosocial.activerecord.backend.expression.statements.dql import QueryExpression
        from rhosocial.activerecord.backend.expression.core import Column

        # QueryExpression implements Executable via statement_type
        query = QueryExpression(dummy_dialect, select=[Column(dummy_dialect, "id")],
                                from_=TableExpression(dummy_dialect, "users"))
        assert isinstance(query, Executable)

    def test_non_executable_is_not_instance(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.executable import Executable
        from rhosocial.activerecord.backend.expression.core import Column

        col = Column(dummy_dialect, "name")
        # Column does NOT implement statement_type
        assert not isinstance(col, Executable)


class TestBasesTypeAliasImport:
    """Cover bases.py:16 — TypeAlias import branch."""

    def test_type_alias_import(self):
        from rhosocial.activerecord.backend.expression.bases import SQLQueryAndParams
        assert SQLQueryAndParams is not None
