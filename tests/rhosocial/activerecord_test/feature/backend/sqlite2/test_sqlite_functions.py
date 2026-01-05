"""
SQLite-specific tests for function factories including concat_op
"""
import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, concat_op, QueryExpression, TableExpression,
    # Import other functions to test
    count, sum_, avg, min_, max_,
    lower, upper, concat, coalesce, length, substring,
    replace, initcap, left, right, lpad, rpad, reverse, strpos,
    abs_, round_, ceil, floor, sqrt, power, exp, log, sin, cos, tan,
    now, current_date, current_time, year, month, day, hour, minute, second,
    date_part, date_trunc, nullif, greatest, least, case,
    row_number, rank, dense_rank, lag, lead, first_value, last_value, nth_value
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


class TestSQLiteConcatOp:
    """Tests for the concat_op function with SQLite dialect."""

    def test_concat_op_two_literals(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test concat_op with two literal values."""
        result = concat_op(sqlite_dialect_3_8_0, "Hello", "World")
        sql, params = result.to_sql()
        assert "||" in sql
        assert params == ("Hello", "World")

    def test_concat_op_two_columns(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test concat_op with two columns."""
        col1 = Column(sqlite_dialect_3_8_0, "first_name")
        col2 = Column(sqlite_dialect_3_8_0, "last_name")
        result = concat_op(sqlite_dialect_3_8_0, col1, col2)
        sql, params = result.to_sql()
        assert "||" in sql
        assert '"first_name"' in sql
        assert '"last_name"' in sql
        assert params == ()

    def test_concat_op_mixed_args(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test concat_op with mixed arguments."""
        col = Column(sqlite_dialect_3_8_0, "name")
        result = concat_op(sqlite_dialect_3_8_0, "Prefix_", col, "_Suffix")
        sql, params = result.to_sql()
        assert "||" in sql
        assert params == ("Prefix_", "_Suffix")

    def test_concat_op_three_strings(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test concat_op with three strings."""
        result = concat_op(sqlite_dialect_3_8_0, "A", "B", "C")
        sql, params = result.to_sql()
        assert "||" in sql
        assert params == ("A", "B", "C")
        # Should have two || operators for three elements
        assert sql.count("||") == 2

    def test_concat_op_in_query_context(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test concat_op used within a query context."""
        # Create a simple query that uses concat_op
        full_name_expr = concat_op(
            sqlite_dialect_3_8_0,
            Column(sqlite_dialect_3_8_0, "first_name"),
            Literal(sqlite_dialect_3_8_0, " "),
            Column(sqlite_dialect_3_8_0, "last_name")
        )

        query = QueryExpression(
            sqlite_dialect_3_8_0,
            select=[full_name_expr],
            from_=TableExpression(sqlite_dialect_3_8_0, "users")
        )

        sql, params = query.to_sql()

        # Verify that both concat_op and query functionality work together
        assert "||" in sql  # Concatenation operator
        assert "users" in sql  # Table reference
        assert params == (" ",)  # Space parameter from concat_op

    def test_concat_op_error_less_than_two_args(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test concat_op raises error with less than two arguments."""
        with pytest.raises(ValueError, match="requires at least 2 expressions"):
            concat_op(sqlite_dialect_3_8_0, "SingleArg")


class TestSQLiteFunctionFactories:
    """Tests for other SQLite function factories."""

    def test_concat_function(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test CONCAT function."""
        func = concat(sqlite_dialect_3_8_0, "first_name", "last_name")
        sql, params = func.to_sql()
        assert "CONCAT(" in sql
        assert params == ("first_name", "last_name")

    def test_length_function(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test LENGTH function."""
        func = length(sqlite_dialect_3_8_0, "name")
        sql, params = func.to_sql()
        assert "LENGTH(" in sql

    def test_substring_function(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test SUBSTRING function."""
        func = substring(sqlite_dialect_3_8_0, "text", 1, 5)
        sql, params = func.to_sql()
        assert "SUBSTRING(" in sql
        assert params == ("text", 1, 5)

    def test_lower_function(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test LOWER function."""
        func = lower(sqlite_dialect_3_8_0, "name")
        sql, params = func.to_sql()
        assert "LOWER(" in sql
        assert params == ("name",)

    def test_upper_function(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test UPPER function."""
        func = upper(sqlite_dialect_3_8_0, "name")
        sql, params = func.to_sql()
        assert "UPPER(" in sql
        assert params == ("name",)

    def test_abs_function(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test ABS function."""
        func = abs_(sqlite_dialect_3_8_0, -5)
        sql, params = func.to_sql()
        assert "ABS(" in sql
        assert params == (-5,)

    def test_round_function(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test ROUND function."""
        func = round_(sqlite_dialect_3_8_0, 3.14159)
        sql, params = func.to_sql()
        assert "ROUND(" in sql
        assert params == (3.14159,)

    def test_count_function(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test COUNT function."""
        func = count(sqlite_dialect_3_8_0, "id")
        sql, params = func.to_sql()
        assert "COUNT(" in sql
        assert params == ()