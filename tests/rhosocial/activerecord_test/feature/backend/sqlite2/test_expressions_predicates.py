# tests/rhosocial/activerecord_test/feature/backend/sqlite2/test_expressions_predicates.py
import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, RawSQLExpression, Subquery,
    ComparisonPredicate, LogicalPredicate, InPredicate, BetweenPredicate, IsNullPredicate, LikePredicate
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

class TestPredicateExpressions:
    """Tests for various SQL predicate expressions."""

    @pytest.mark.parametrize("left_data, operator, right_data, expected_sql, expected_params", [
        ((Column, ("age",)), "=", (Literal, (18,)), '"age" = ?', (18,)),
        ((Column, ("price",)), ">", (Literal, (100.0,)), '"price" > ?', (100.0,)),
        ((Column, ("status",)), "!=", (Literal, ("inactive",)), '"status" != ?', ("inactive",)),
        ((RawSQLExpression, ("NOW()",)), "<", (Column, ("end_date",)), 'NOW() < "end_date"', ()),
    ])
    def test_comparison_predicate(self, sqlite_dialect_3_8_0: SQLiteDialect, left_data, operator, right_data, expected_sql, expected_params):
        """Tests comparison predicates (e.g., =, !=, >, <)."""
        left_expr = left_data[0](sqlite_dialect_3_8_0, *left_data[1])
        right_expr = right_data[0](sqlite_dialect_3_8_0, *right_data[1])

        pred = ComparisonPredicate(sqlite_dialect_3_8_0, operator, left_expr, right_expr)
        sql, params = pred.to_sql()
        assert sql == expected_sql
        assert params == expected_params

    def test_comparison_predicate_with_column(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test comparison between two columns."""
        left_col = Column(sqlite_dialect_3_8_0, "age")
        right_col = Column(sqlite_dialect_3_8_0, "min_age")
        pred = ComparisonPredicate(sqlite_dialect_3_8_0, ">", left_col, right_col)
        sql, params = pred.to_sql()
        assert sql == '"age" > "min_age"'
        assert params == ()

    def test_logical_and_predicate(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test logical AND predicate."""
        pred1 = ComparisonPredicate(sqlite_dialect_3_8_0, ">=", Column(sqlite_dialect_3_8_0, "age"), Literal(sqlite_dialect_3_8_0, 18))
        pred2 = ComparisonPredicate(sqlite_dialect_3_8_0, "<", Column(sqlite_dialect_3_8_0, "age"), Literal(sqlite_dialect_3_8_0, 65))
        and_pred = LogicalPredicate(sqlite_dialect_3_8_0, "AND", pred1, pred2)
        sql, params = and_pred.to_sql()
        assert sql == '"age" >= ? AND "age" < ?'
        assert params == (18, 65)

    def test_logical_or_predicate(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test logical OR predicate."""
        pred1 = ComparisonPredicate(sqlite_dialect_3_8_0, "=", Column(sqlite_dialect_3_8_0, "status"), Literal(sqlite_dialect_3_8_0, "active"))
        pred2 = ComparisonPredicate(sqlite_dialect_3_8_0, "=", Column(sqlite_dialect_3_8_0, "status"), Literal(sqlite_dialect_3_8_0, "pending"))
        or_pred = LogicalPredicate(sqlite_dialect_3_8_0, "OR", pred1, pred2)
        sql, params = or_pred.to_sql()
        assert sql == '"status" = ? OR "status" = ?'
        assert params == ("active", "pending")

    def test_logical_not_predicate(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test logical NOT predicate."""
        pred = ComparisonPredicate(sqlite_dialect_3_8_0, "=", Column(sqlite_dialect_3_8_0, "status"), Literal(sqlite_dialect_3_8_0, "inactive"))
        not_pred = LogicalPredicate(sqlite_dialect_3_8_0, "NOT", pred)
        sql, params = not_pred.to_sql()
        assert sql == 'NOT ("status" = ?)'
        assert params == ("inactive",)

    def test_complex_logical_predicate(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test complex nested logical predicate."""
        pred1 = ComparisonPredicate(sqlite_dialect_3_8_0, ">=", Column(sqlite_dialect_3_8_0, "age"), Literal(sqlite_dialect_3_8_0, 18))
        pred2 = ComparisonPredicate(sqlite_dialect_3_8_0, "<", Column(sqlite_dialect_3_8_0, "age"), Literal(sqlite_dialect_3_8_0, 65))
        and_pred = LogicalPredicate(sqlite_dialect_3_8_0, "AND", pred1, pred2)
        pred3 = ComparisonPredicate(sqlite_dialect_3_8_0, "=", Column(sqlite_dialect_3_8_0, "country"), Literal(sqlite_dialect_3_8_0, "US"))
        complex_pred = LogicalPredicate(sqlite_dialect_3_8_0, "OR", and_pred, pred3)
        sql, params = complex_pred.to_sql()
        assert sql == '"age" >= ? AND "age" < ? OR "country" = ?'
        assert params == (18, 65, "US")

    def test_in_predicate_with_list(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test IN predicate with a list of values."""
        pred = InPredicate(sqlite_dialect_3_8_0,
                           Column(sqlite_dialect_3_8_0, "status"),
                           Literal(sqlite_dialect_3_8_0, ["active", "pending", "approved"]))
        sql, params = pred.to_sql()
        assert sql == '"status" IN (?, ?, ?)'
        assert params == ("active", "pending", "approved")

    def test_in_predicate_with_numbers(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test IN predicate with a list of numbers."""
        pred = InPredicate(sqlite_dialect_3_8_0,
                           Column(sqlite_dialect_3_8_0, "id"),
                           Literal(sqlite_dialect_3_8_0, [1, 2, 3, 4, 5]))
        sql, params = pred.to_sql()
        assert sql == '"id" IN (?, ?, ?, ?, ?)'
        assert params == (1, 2, 3, 4, 5)

    def test_in_predicate_with_subquery(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test IN predicate with a subquery."""
        subquery = Subquery(sqlite_dialect_3_8_0, "SELECT id FROM users WHERE verified = ?", (True,))
        pred = InPredicate(sqlite_dialect_3_8_0, Column(sqlite_dialect_3_8_0, "user_id"), subquery)
        sql, params = pred.to_sql()
        assert sql == '"user_id" IN (SELECT id FROM users WHERE verified = ?)'
        assert params == (True,)

    def test_between_predicate_numbers(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test BETWEEN predicate with numbers."""
        pred = BetweenPredicate(sqlite_dialect_3_8_0,
                                Column(sqlite_dialect_3_8_0, "age"),
                                Literal(sqlite_dialect_3_8_0, 18),
                                Literal(sqlite_dialect_3_8_0, 65))
        sql, params = pred.to_sql()
        assert sql == '"age" BETWEEN ? AND ?'
        assert params == (18, 65)

    def test_between_predicate_dates(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test BETWEEN predicate with dates."""
        pred = BetweenPredicate(sqlite_dialect_3_8_0,
                                Column(sqlite_dialect_3_8_0, "created_at"),
                                Literal(sqlite_dialect_3_8_0, "2024-01-01"),
                                Literal(sqlite_dialect_3_8_0, "2024-12-31"))
        sql, params = pred.to_sql()
        assert sql == '"created_at" BETWEEN ? AND ?'
        assert params == ("2024-01-01", "2024-12-31")

    def test_is_null_predicate(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test IS NULL predicate."""
        pred = IsNullPredicate(sqlite_dialect_3_8_0, Column(sqlite_dialect_3_8_0, "deleted_at"))
        sql, params = pred.to_sql()
        assert sql == '"deleted_at" IS NULL'
        assert params == ()

    def test_is_not_null_predicate(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test IS NOT NULL predicate."""
        pred = IsNullPredicate(sqlite_dialect_3_8_0, Column(sqlite_dialect_3_8_0, "deleted_at"), is_not=True)
        sql, params = pred.to_sql()
        assert sql == '"deleted_at" IS NOT NULL'
        assert params == ()

    def test_like_predicate(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test LIKE predicate."""
        pred = LikePredicate(sqlite_dialect_3_8_0, "LIKE",
                             Column(sqlite_dialect_3_8_0, "name"),
                             Literal(sqlite_dialect_3_8_0, "John%"))
        sql, params = pred.to_sql()
        assert sql == '"name" LIKE ?'
        assert params == ("John%",)

    def test_not_like_predicate(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test NOT LIKE predicate."""
        pred = LikePredicate(sqlite_dialect_3_8_0, "NOT LIKE",
                             Column(sqlite_dialect_3_8_0, "email"),
                             Literal(sqlite_dialect_3_8_0, "%@spam.com"))
        sql, params = pred.to_sql()
        assert sql == '"email" NOT LIKE ?'
        assert params == ("%@spam.com",)