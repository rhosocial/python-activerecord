# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_expressions_functions.py
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

    @pytest.mark.parametrize("func_name, args_data, is_distinct, expected_sql, expected_params", [
        ("LENGTH", ["some_text"], False, "LENGTH(?)", ("some_text",)),
        ("CONCAT", [("Column", "first"), " ", ("Column", "last")], False, 'CONCAT("first", ?, "last")', (" ",)),
        ("COALESCE", [("Column", "col1"), "default"], False, 'COALESCE("col1", ?)', ("default",)),
        ("MAX", [("Column", "price")], False, 'MAX("price")', ()),
        ("COUNT", ["*"], True, "COUNT(DISTINCT ?)", ("*",)),
    ])
    def test_function_with_args(self, dummy_dialect: DummyDialect, func_name, args_data, is_distinct, expected_sql, expected_params):
        """Tests function calls with various arguments and distinct flag."""
        dialect_args = []
        for arg_data in args_data:
            if isinstance(arg_data, tuple) and arg_data[0] == "Column":
                dialect_args.append(Column(dummy_dialect, arg_data[1]))
            elif isinstance(arg_data, str) and arg_data == "*":
                dialect_args.append(Literal(dummy_dialect, arg_data))
            else:
                dialect_args.append(Literal(dummy_dialect, arg_data))

        func_call = FunctionCall(dummy_dialect, func_name, *dialect_args, is_distinct=is_distinct)
        sql, params = func_call.to_sql()
        assert sql == expected_sql
        assert params == expected_params

    def test_count_star(self, dummy_dialect: DummyDialect):
        """Test COUNT(*) function."""
        agg_call = count(dummy_dialect, "*")
        sql, params = agg_call.to_sql()
        assert sql == "COUNT(*)"
        assert params == ()

    def test_count_column_with_alias(self, dummy_dialect: DummyDialect):
        """Test COUNT(column) with alias."""
        agg_call = count(dummy_dialect, Column(dummy_dialect, "id"), alias="total")
        sql, params = agg_call.to_sql()
        assert sql == 'COUNT("id") AS "total"'
        assert params == ()

    def test_sum_column(self, dummy_dialect: DummyDialect):
        """Test SUM(column) function."""
        agg_call = sum_(dummy_dialect, Column(dummy_dialect, "amount"))
        sql, params = agg_call.to_sql()
        assert sql == 'SUM("amount")'
        assert params == ()

    def test_avg_distinct_with_alias(self, dummy_dialect: DummyDialect):
        """Test AVG(DISTINCT column) with alias."""
        agg_call = avg(dummy_dialect, Column(dummy_dialect, "score"), is_distinct=True, alias="avg_score")
        sql, params = agg_call.to_sql()
        assert sql == 'AVG(DISTINCT "score") AS "avg_score"'
        assert params == ()

    def test_aggregate_function_with_filter_clause(self, dummy_dialect: DummyDialect):
        """Tests an aggregate function with a FILTER (WHERE ...) clause."""
        # COUNT with a single filter
        active_count = count(dummy_dialect, "*", alias="active_count").filter(
            Column(dummy_dialect, "status") == Literal(dummy_dialect, "active")
        )
        sql, params = active_count.to_sql()
        assert sql == 'COUNT(*) FILTER (WHERE "status" = ?) AS "active_count"'
        assert params == ("active",)

        # SUM with multiple chained filters (combined with AND)
        high_value_sum = sum_(dummy_dialect, Column(dummy_dialect, "amount"), alias="high_value_sum").filter(
            Column(dummy_dialect, "category") == Literal(dummy_dialect, "sales")
        ).filter(
            Column(dummy_dialect, "priority") == Literal(dummy_dialect, True)
        )
        sql, params = high_value_sum.to_sql()
        assert sql == 'SUM("amount") FILTER (WHERE "category" = ? AND "priority" = ?) AS "high_value_sum"'
        assert params == ("sales", True)