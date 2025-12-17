import pytest
from rhosocial.activerecord.backend.expression import FunctionCall, Column, Literal, count, sum_, avg, RawSQLExpression
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

class TestFunctionExpressions:
    """Tests for SQL function call expressions."""

    def test_function_no_args(self, dummy_dialect: DummyDialect):
        """Tests a function call with no arguments (e.g., NOW())."""
        func_call = FunctionCall(dummy_dialect, "NOW")
        sql, params = func_call.to_sql()
        assert sql == "NOW()"
        assert params == ()

    @pytest.mark.parametrize("func_name, args, is_distinct, expected_sql, expected_params", [
        ("LENGTH", [Literal(None, "some_text")], False, "LENGTH(?)", ("some_text",)),
        ("CONCAT", [Column(None, "first"), Literal(None, " "), Column(None, "last")], False, "CONCAT(\"first\", ?, \"last\")", (" ",)),
        ("COALESCE", [Column(None, "col1"), Literal(None, "default")], False, "COALESCE(\"col1\", ?)", ("default",)),
        ("MAX", [Column(None, "price")], False, "MAX(\"price\")", ())
        ("COUNT", [Literal(None, "*")], True, "COUNT(DISTINCT *)", ())
    ])
    def test_function_with_args(self, dummy_dialect: DummyDialect, func_name, args, is_distinct, expected_sql, expected_params):
        """Tests function calls with various arguments and distinct flag."""
        # Update args with the dialect instance
        dialect_args = []
        for arg in args:
            if isinstance(arg, (Literal, Column, RawSQLExpression)):
                arg.dialect = dummy_dialect
            dialect_args.append(arg)

        func_call = FunctionCall(dummy_dialect, func_name, *dialect_args, is_distinct=is_distinct)
        sql, params = func_call.to_sql()
        assert sql == expected_sql
        assert params == expected_params

    @pytest.mark.parametrize("agg_func, arg_expr, alias, is_distinct, expected_sql, expected_params", [
        (count, Literal(None, "*"), None, False, "COUNT(*)", ())
        (count, Column(None, "id"), "total", False, "COUNT(\"id\") AS \"total\"", ())
        (sum_, Column(None, "amount"), None, False, "SUM(\"amount\")", ())
        (avg, Column(None, "score"), "avg_score", True, "AVG(DISTINCT \"score\") AS \"avg_score\"", ())
    ])
    def test_aggregate_function_factories(self, dummy_dialect: DummyDialect, agg_func, arg_expr, alias, is_distinct, expected_sql, expected_params):
        """Tests aggregate function factories (count, sum_, avg) with various configurations."""
        if arg_expr:
            arg_expr.dialect = dummy_dialect # Assign dialect to argument expression

        # Create the aggregate function using the factory
        agg_call = agg_func(dummy_dialect, arg_expr, alias=alias, is_distinct=is_distinct)
        sql, params = agg_call.to_sql()
        assert sql == expected_sql
        assert params == expected_params

    def test_aggregate_function_with_filter_clause(self, dummy_dialect: DummyDialect):
        """Tests an aggregate function with a FILTER (WHERE ...) clause."""
        # COUNT with a single filter
        active_count = count(dummy_dialect, Literal(dummy_dialect, "*"), alias="active_count").filter(
            Column(dummy_dialect, "status") == Literal(dummy_dialect, "active")
        )
        sql, params = active_count.to_sql()
        assert sql == "COUNT(*) FILTER (WHERE (\"status\" = ?)) AS \"active_count\""
        assert params == ("active",)

        # SUM with multiple chained filters (combined with AND)
        high_value_sum = sum_(dummy_dialect, Column(dummy_dialect, "amount"), alias="high_value_sum").filter(
            Column(dummy_dialect, "category") == Literal(dummy_dialect, "sales")
        ).filter(
            Column(dummy_dialect, "priority") == Literal(dummy_dialect, True)
        )
        sql, params = high_value_sum.to_sql()
        assert sql == "SUM(\"amount\") FILTER (WHERE (((\"category\" = ?)) AND (((\"priority\" = ?))))) AS \"high_value_sum\""
        assert params == ("sales", True)
