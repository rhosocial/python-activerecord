import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, RawSQLExpression, Subquery,
    ComparisonPredicate, LogicalPredicate, InPredicate, BetweenPredicate, IsNullPredicate, LikePredicate
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

class TestPredicateExpressions:
    """Tests for various SQL predicate expressions."""

    @pytest.mark.parametrize("left_data, operator, right_data, expected_sql, expected_params", [
        ((Column, ("age",)), "=", (Literal, (18,)), '"age" = ?', (18,)),
        ((Column, ("price",)), ">", (Literal, (100.0,)), '"price" > ?', (100.0,)),
        ((Column, ("status",)), "!=", (Literal, ("inactive",)), '"status" != ?', ("inactive",)),
        ((RawSQLExpression, ("NOW()",)), "<", (Column, ("end_date",)), 'NOW() < "end_date"', ()),
    ])
    def test_comparison_predicate(self, dummy_dialect: DummyDialect, left_data, operator, right_data, expected_sql, expected_params):
        """Tests comparison predicates (e.g., =, !=, >, <)."""
        left_expr = left_data[0](dummy_dialect, *left_data[1])
        right_expr = right_data[0](dummy_dialect, *right_data[1])
        
        pred = ComparisonPredicate(dummy_dialect, operator, left_expr, right_expr)
        sql, params = pred.to_sql()
        assert sql == expected_sql
        assert params == expected_params

    @pytest.mark.parametrize("expr_data, op, pattern_data, expected_sql, expected_params", [
        ((Column, ("name",)), "LIKE", (Literal, ("J%",)), '"name" LIKE ?', ("J%",)),
        ((Column, ("email",)), "ILIKE", (Literal, ("%@example.com",)), '"email" ILIKE ?', ("%@example.com",)),
        ((Column, ("description",)), "NOT LIKE", (Literal, ("%bad%",)), '"description" NOT LIKE ?', ("%bad%",)),
    ])
    def test_like_predicate(self, dummy_dialect: DummyDialect, expr_data, op, pattern_data, expected_sql, expected_params):
        """Tests LIKE and ILIKE predicates."""
        expr = expr_data[0](dummy_dialect, *expr_data[1])
        pattern = pattern_data[0](dummy_dialect, *pattern_data[1])
        
        pred = LikePredicate(dummy_dialect, op, expr, pattern)
        sql, params = pred.to_sql()
        assert sql == expected_sql
        assert params == expected_params

    def test_in_predicate_with_list(self, dummy_dialect: DummyDialect):
        """Tests IN predicate with a list of values."""
        pred = InPredicate(dummy_dialect, Column(dummy_dialect, "status"), Literal(dummy_dialect, ["active", "pending"]))
        sql, params = pred.to_sql()
        assert sql == '"status" IN (?, ?)'
        assert params == ("active", "pending")

    def test_in_predicate_with_subquery(self, dummy_dialect: DummyDialect):
        """Tests IN predicate with a subquery."""
        subquery = Subquery(dummy_dialect, "SELECT id FROM active_users WHERE last_login > ?", ("2024-01-01",))
        pred = InPredicate(dummy_dialect, Column(dummy_dialect, "user_id"), subquery)
        sql, params = pred.to_sql()
        assert sql == '"user_id" IN (SELECT id FROM active_users WHERE last_login > ?)'
        assert params == ("2024-01-01",)

    def test_in_predicate_empty_list(self, dummy_dialect: DummyDialect):
        """Tests IN predicate with an empty list."""
        pred = InPredicate(dummy_dialect, Column(dummy_dialect, "category"), Literal(dummy_dialect, []))
        sql, params = pred.to_sql()
        assert sql == '"category" IN ()'
        assert params == ()

    @pytest.mark.parametrize("expr_data, lower_data, upper_data, expected_sql, expected_params", [
        ((Column, ("quantity",)), (Literal, (10,)), (Literal, (20,)), '"quantity" BETWEEN ? AND ?', (10, 20)),
        ((RawSQLExpression, ("order_date",)), (Literal, ("2023-01-01",)), (Literal, ("2023-12-31",)), 'order_date BETWEEN ? AND ?', ("2023-01-01", "2023-12-31")),
    ])
    def test_between_predicate(self, dummy_dialect: DummyDialect, expr_data, lower_data, upper_data, expected_sql, expected_params):
        """Tests BETWEEN predicate."""
        expr = expr_data[0](dummy_dialect, *expr_data[1])
        lower_bound = lower_data[0](dummy_dialect, *lower_data[1])
        upper_bound = upper_data[0](dummy_dialect, *upper_data[1])

        pred = BetweenPredicate(dummy_dialect, expr, lower_bound, upper_bound)
        sql, params = pred.to_sql()
        assert sql == expected_sql
        assert params == expected_params

    @pytest.mark.parametrize("expr_data, is_not, expected_sql, expected_params", [
        ((Column, ("deleted_at",)), False, '"deleted_at" IS NULL', ()),
        ((Column, ("optional_field",)), True, '"optional_field" IS NOT NULL', ()),
    ])
    def test_is_null_predicate(self, dummy_dialect: DummyDialect, expr_data, is_not, expected_sql, expected_params):
        """Tests IS NULL and IS NOT NULL predicates."""
        expr = expr_data[0](dummy_dialect, *expr_data[1])
        
        pred = IsNullPredicate(dummy_dialect, expr, is_not=is_not)
        sql, params = pred.to_sql()
        assert sql == expected_sql
        assert params == expected_params

    def test_logical_and_predicate(self, dummy_dialect: DummyDialect):
        """Tests logical AND predicate."""
        pred1 = ComparisonPredicate(dummy_dialect, ">", Column(dummy_dialect, "age"), Literal(dummy_dialect, 18))
        pred2 = ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "status"), Literal(dummy_dialect, "active"))
        logical_and = LogicalPredicate(dummy_dialect, "AND", pred1, pred2)
        sql, params = logical_and.to_sql()
        assert sql == '"age" > ? AND "status" = ?'
        assert params == (18, "active")

    def test_logical_or_predicate(self, dummy_dialect: DummyDialect):
        """Tests logical OR predicate."""
        pred1 = ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "country"), Literal(dummy_dialect, "US"))
        pred2 = ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "country"), Literal(dummy_dialect, "CA"))
        logical_or = LogicalPredicate(dummy_dialect, "OR", pred1, pred2)
        sql, params = logical_or.to_sql()
        assert sql == '"country" = ? OR "country" = ?'
        assert params == ("US", "CA")

    def test_logical_not_predicate(self, dummy_dialect: DummyDialect):
        """Tests logical NOT predicate."""
        pred = ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "is_admin"), Literal(dummy_dialect, True))
        logical_not = LogicalPredicate(dummy_dialect, "NOT", pred)
        sql, params = logical_not.to_sql()
        assert sql == 'NOT ("is_admin" = ?)'
        assert params == (True,)

    def test_complex_logical_predicate(self, dummy_dialect: DummyDialect):
        """Tests complex nested logical predicates."""
        age_pred = ComparisonPredicate(dummy_dialect, ">", Column(dummy_dialect, "age"), Literal(dummy_dialect, 25))
        status_pred = ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "status"), Literal(dummy_dialect, "active"))
        name_like_pred = LikePredicate(dummy_dialect, "LIKE", Column(dummy_dialect, "name"), Literal(dummy_dialect, "J%"))

        # (age > 25 AND status = 'active') OR (name LIKE 'J%')
        and_pred = LogicalPredicate(dummy_dialect, "AND", age_pred, status_pred)
        composite_pred = LogicalPredicate(dummy_dialect, "OR", and_pred, name_like_pred)

        sql, params = composite_pred.to_sql()
        assert sql == '"age" > ? AND "status" = ? OR "name" LIKE ?'
        assert params == (25, "active", "J%")

