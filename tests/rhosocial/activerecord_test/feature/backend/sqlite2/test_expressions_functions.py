# tests/rhosocial/activerecord_test/feature/backend/sqlite2/test_expressions_functions.py
import pytest
from rhosocial.activerecord.backend.expression import FunctionCall, Column, Literal, count, sum_, avg, RawSQLExpression
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

class TestFunctionExpressions:
    """Tests for SQL function call expressions."""

    def test_function_no_args(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Tests a function call with no arguments (e.g., NOW())."""
        func_call = FunctionCall(sqlite_dialect_3_8_0, "NOW")
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
    def test_function_with_args(self, sqlite_dialect_3_8_0: SQLiteDialect, func_name, args_data, is_distinct, expected_sql, expected_params):
        """Tests function calls with various arguments and distinct flag."""
        dialect_args = []
        for arg in args_data:
            if arg[0] == "Column":
                dialect_args.append(Column(sqlite_dialect_3_8_0, arg[1]))
            else:
                dialect_args.append(Literal(sqlite_dialect_3_8_0, arg))
        
        func_call = FunctionCall(sqlite_dialect_3_8_0, func_name, *dialect_args, is_distinct=is_distinct)
        sql, params = func_call.to_sql()
        assert sql == expected_sql
        assert params == expected_params

    def test_function_with_alias(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Tests a function call with alias."""
        func_call = FunctionCall(sqlite_dialect_3_8_0, "COUNT", Column(sqlite_dialect_3_8_0, "id"), alias="total")
        sql, params = func_call.to_sql()
        assert sql == 'COUNT("id") AS "total"'
        assert params == ()

    def test_function_multiple_args(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Tests a function call with multiple arguments."""
        func_call = FunctionCall(
            sqlite_dialect_3_8_0,
            "CONCAT",
            Column(sqlite_dialect_3_8_0, "first_name"),
            Literal(sqlite_dialect_3_8_0, " "),
            Column(sqlite_dialect_3_8_0, "last_name")
        )
        sql, params = func_call.to_sql()
        assert sql == 'CONCAT("first_name", ?, "last_name")'
        assert params == (" ",)

    def test_count_function(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Tests the count function factory."""
        func_call = count(sqlite_dialect_3_8_0, Column(sqlite_dialect_3_8_0, "id"))
        sql, params = func_call.to_sql()
        assert sql == 'COUNT("id")'
        assert params == ()

    def test_count_star(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Tests the count function factory with star."""
        func_call = count(sqlite_dialect_3_8_0, "*")
        sql, params = func_call.to_sql()
        assert sql == 'COUNT(*)'
        assert params == ()

    def test_sum_function(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Tests the sum function factory."""
        func_call = sum_(sqlite_dialect_3_8_0, Column(sqlite_dialect_3_8_0, "amount"))
        sql, params = func_call.to_sql()
        assert sql == 'SUM("amount")'
        assert params == ()

    def test_avg_function(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Tests the avg function factory."""
        func_call = avg(sqlite_dialect_3_8_0, Column(sqlite_dialect_3_8_0, "price"))
        sql, params = func_call.to_sql()
        assert sql == 'AVG("price")'
        assert params == ()

    def test_function_with_distinct(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Tests a function call with distinct flag."""
        func_call = FunctionCall(sqlite_dialect_3_8_0, "COUNT", Column(sqlite_dialect_3_8_0, "user_id"), is_distinct=True)
        sql, params = func_call.to_sql()
        assert sql == 'COUNT(DISTINCT "user_id")'
        assert params == ()

    def test_function_with_raw_sql_arg(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Tests a function call with RawSQLExpression as argument."""
        raw_sql = RawSQLExpression(sqlite_dialect_3_8_0, "CURRENT_TIMESTAMP")
        func_call = FunctionCall(sqlite_dialect_3_8_0, "DATE", raw_sql)
        sql, params = func_call.to_sql()
        assert sql == 'DATE(CURRENT_TIMESTAMP)'
        assert params == ()