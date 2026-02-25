# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_returning_clause_to_sql.py
import pytest
from rhosocial.activerecord.backend.expression import Column, Literal, RawSQLExpression, FunctionCall
from rhosocial.activerecord.backend.expression.statements import ReturningClause
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestReturningClauseToSql:
    """Tests for ReturningClause.to_sql method to ensure proper test coverage."""

    def test_returning_clause_with_single_column(self, dummy_dialect: DummyDialect):
        """Tests ReturningClause with a single column expression."""
        returning_clause = ReturningClause(
            dummy_dialect,
            expressions=[Column(dummy_dialect, "id")]
        )
        sql, params = returning_clause.to_sql()
        # The actual SQL depends on the dialect implementation
        # The main goal is to test that to_sql() method is called
        assert "RETURNING" in sql
        assert '"id"' in sql
        assert params == ()

    def test_returning_clause_with_multiple_columns(self, dummy_dialect: DummyDialect):
        """Tests ReturningClause with multiple column expressions."""
        returning_clause = ReturningClause(
            dummy_dialect,
            expressions=[
                Column(dummy_dialect, "id"),
                Column(dummy_dialect, "name"),
                Column(dummy_dialect, "created_at")
            ]
        )
        sql, params = returning_clause.to_sql()
        assert "RETURNING" in sql
        assert '"id"' in sql
        assert '"name"' in sql
        assert '"created_at"' in sql
        assert params == ()

    def test_returning_clause_with_literal(self, dummy_dialect: DummyDialect):
        """Tests ReturningClause with literal expressions."""
        returning_clause = ReturningClause(
            dummy_dialect,
            expressions=[Literal(dummy_dialect, 42), Literal(dummy_dialect, "constant")]
        )
        sql, params = returning_clause.to_sql()
        assert "RETURNING" in sql
        assert params == (42, "constant")

    def test_returning_clause_with_function_calls(self, dummy_dialect: DummyDialect):
        """Tests ReturningClause with function call expressions."""
        returning_clause = ReturningClause(
            dummy_dialect,
            expressions=[
                FunctionCall(dummy_dialect, "NOW"),
                FunctionCall(dummy_dialect, "COUNT", Column(dummy_dialect, "id"))
            ]
        )
        sql, params = returning_clause.to_sql()
        assert "RETURNING" in sql
        assert "NOW()" in sql
        assert 'COUNT("id")' in sql
        assert params == ()

    def test_returning_clause_with_raw_sql_expressions(self, dummy_dialect: DummyDialect):
        """Tests ReturningClause with raw SQL expressions."""
        returning_clause = ReturningClause(
            dummy_dialect,
            expressions=[
                RawSQLExpression(dummy_dialect, "CURRENT_TIMESTAMP"),
                Column(dummy_dialect, "id")
            ]
        )
        sql, params = returning_clause.to_sql()
        assert "RETURNING" in sql
        assert "CURRENT_TIMESTAMP" in sql
        assert '"id"' in sql
        assert params == ()

    def test_returning_clause_with_alias(self, dummy_dialect: DummyDialect):
        """Tests ReturningClause with alias (if supported by dialect)."""
        returning_clause = ReturningClause(
            dummy_dialect,
            expressions=[Column(dummy_dialect, "id")],
            alias="returned_values"
        )
        sql, params = returning_clause.to_sql()
        assert "RETURNING" in sql
        assert '"id"' in sql
        # Alias may or may not be used depending on dialect implementation
        assert params == ()

    def test_returning_clause_with_empty_expressions(self, dummy_dialect: DummyDialect):
        """Tests ReturningClause with empty expressions list."""
        returning_clause = ReturningClause(
            dummy_dialect,
            expressions=[]
        )
        sql, params = returning_clause.to_sql()
        # Even with empty expressions, to_sql should run without error
        # Result might be empty string depending on dialect implementation
        assert isinstance(sql, str)
        assert isinstance(params, tuple)

    def test_returning_clause_with_mixed_expressions(self, dummy_dialect: DummyDialect):
        """Tests ReturningClause with mixed types of expressions."""
        returning_clause = ReturningClause(
            dummy_dialect,
            expressions=[
                Column(dummy_dialect, "id"),
                FunctionCall(dummy_dialect, "UPPER", Column(dummy_dialect, "name")),
                Literal(dummy_dialect, "status"),
                RawSQLExpression(dummy_dialect, "1")
            ]
        )
        sql, params = returning_clause.to_sql()
        assert "RETURNING" in sql
        assert '"id"' in sql
        assert 'UPPER("name")' in sql
        assert params == ("status",)