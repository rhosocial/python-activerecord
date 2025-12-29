# tests/rhosocial/activerecord_test/feature/backend/sqlite2/test_sqlite_query_parts.py
import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, FunctionCall, ComparisonPredicate,
    WhereClause, GroupByHavingClause, LimitOffsetClause, OrderByClause, QualifyClause
)
from rhosocial.activerecord.backend.expression.predicates import (
    InPredicate, BetweenPredicate, IsNullPredicate, LikePredicate, LogicalPredicate
)
from rhosocial.activerecord.backend.expression.query_parts import ForUpdateClause
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.expression.statements import (
    ColumnConstraintType, TableConstraintType, ReferentialAction
)


class TestQueryParts:
    """Tests for SQL query clause expressions in query_parts module."""

    def test_where_clause_basic(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test basic WHERE clause generation."""
        condition = Column(sqlite_dialect_3_8_0, "status") == Literal(sqlite_dialect_3_8_0, "active")
        where_clause = WhereClause(sqlite_dialect_3_8_0, condition=condition)

        sql, params = where_clause.to_sql()
        assert sql.startswith("WHERE ")
        assert params == ("active",)

    def test_where_clause_complex(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test complex WHERE clause with multiple conditions."""
        condition1 = Column(sqlite_dialect_3_8_0, "age") >= Literal(sqlite_dialect_3_8_0, 18)
        condition2 = Column(sqlite_dialect_3_8_0, "status") == Literal(sqlite_dialect_3_8_0, "active")
        complex_condition = LogicalPredicate(sqlite_dialect_3_8_0, "AND", condition1, condition2)
        
        where_clause = WhereClause(sqlite_dialect_3_8_0, condition=complex_condition)
        sql, params = where_clause.to_sql()
        assert sql.startswith("WHERE ")
        assert len(params) == 2  # 18 and "active"

    def test_group_by_having_clause(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test GROUP BY with HAVING clause."""
        group_by_columns = [Column(sqlite_dialect_3_8_0, "department")]
        having_condition = FunctionCall(sqlite_dialect_3_8_0, "COUNT", Column(sqlite_dialect_3_8_0, "id")) > Literal(sqlite_dialect_3_8_0, 5)
        
        group_by_having = GroupByHavingClause(
            sqlite_dialect_3_8_0,
            group_by=group_by_columns,
            having=having_condition
        )
        
        sql, params = group_by_having.to_sql()
        assert "GROUP BY" in sql.upper()
        assert "HAVING" in sql.upper()
        assert params == (5,)

    def test_order_by_clause_single(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test ORDER BY clause with single column."""
        order_by = OrderByClause(
            sqlite_dialect_3_8_0,
            expressions=[Column(sqlite_dialect_3_8_0, "name")]
        )
        
        sql, params = order_by.to_sql()
        assert "ORDER BY" in sql.upper()
        assert '"name"' in sql
        assert params == ()

    def test_order_by_clause_multiple(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test ORDER BY clause with multiple columns."""
        order_by = OrderByClause(
            sqlite_dialect_3_8_0,
            expressions=[
                Column(sqlite_dialect_3_8_0, "department"),
                Column(sqlite_dialect_3_8_0, "salary")
            ]
        )
        
        sql, params = order_by.to_sql()
        assert "ORDER BY" in sql.upper()
        assert '"department"' in sql
        assert '"salary"' in sql
        assert params == ()

    def test_limit_offset_clause_basic(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test LIMIT clause."""
        limit_clause = LimitOffsetClause(
            sqlite_dialect_3_8_0,
            limit=10
        )
        
        sql, params = limit_clause.to_sql()
        assert "LIMIT" in sql.upper()
        assert params == (10,)

    def test_limit_offset_clause_with_offset(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test LIMIT with OFFSET."""
        limit_clause = LimitOffsetClause(
            sqlite_dialect_3_8_0,
            limit=10,
            offset=20
        )
        
        sql, params = limit_clause.to_sql()
        assert "LIMIT" in sql.upper()
        assert "OFFSET" in sql.upper()
        assert params == (10, 20)

    def test_limit_offset_clause_offset_only(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test OFFSET only - this should raise an error in SQLite dialects that don't support it."""
        # In SQLite, offset requires limit, so this should raise an error
        with pytest.raises(ValueError, match="OFFSET clause requires LIMIT clause"):
            LimitOffsetClause(
                sqlite_dialect_3_8_0,
                offset=20
            )

    def test_qualify_clause_not_supported(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test that QUALIFY clause is not supported in SQLite."""
        # Check if the capability is correctly reported as not supported
        assert sqlite_dialect_3_8_0.supports_qualify_clause() is False

    def test_for_update_clause_not_supported(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test that FOR UPDATE clause is not supported in SQLite."""
        # Check if the capability is correctly reported as not supported
        assert sqlite_dialect_3_8_0.supports_for_update_skip_locked() is False

    def test_filter_clause_supported(self, sqlite_dialect_3_30_0: SQLiteDialect):
        """Test that FILTER clause is supported in newer SQLite versions."""
        # Verify that the capability check works correctly
        assert sqlite_dialect_3_30_0.supports_filter_clause() is True

    def test_filter_clause_not_supported(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test that FILTER clause is not supported in older SQLite versions."""
        # Verify that the capability check works correctly
        assert sqlite_dialect_3_8_0.supports_filter_clause() is False