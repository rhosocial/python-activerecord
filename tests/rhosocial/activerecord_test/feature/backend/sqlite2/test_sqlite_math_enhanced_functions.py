# tests/rhosocial/activerecord_test/feature/backend/sqlite2/test_sqlite_math_enhanced_functions.py
"""
Tests for SQLite-specific enhanced math functions.
These include additional mathematical functions beyond the basic math module.

The math functions themselves (``pow``, ``power``, ``sqrt``, ``mod``, ``trunc``,
``ceil``, ``floor``) arrived in SQLite 3.35.0 with the math extension, so they
are built on a dialect that has them; rendering one on an older SQLite is
refused rather than emitted (see
:meth:`SQLDialectBase.check_function_version`).
"""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import Column, Literal
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.functions.math_enhanced import (
    round_,
    pow,
    power,
    sqrt,
    mod,
    ceil,
    floor,
    trunc,
    max_,
    min_,
    avg,
)


class TestSQLiteMathEnhancedFunctions:
    """Tests for SQLite enhanced math functions."""

    def test_round__default(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test round_() with default precision."""
        result = round_(sqlite_dialect_3_8_0, Column(sqlite_dialect_3_8_0, "value"))
        sql, _ = result.to_sql()
        assert "ROUND(" in sql
        assert '"value"' in sql

    def test_round__with_precision(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test round_() with precision."""
        result = round_(sqlite_dialect_3_8_0, Column(sqlite_dialect_3_8_0, "price"), Literal(sqlite_dialect_3_8_0, 2))
        sql, _ = result.to_sql()
        assert "ROUND(" in sql
        # precision is stored as literal in expression, not as param

    def test_round__with_literal(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test round_() with literal value."""
        result = round_(sqlite_dialect_3_8_0, Literal(sqlite_dialect_3_8_0, 3.14159), Literal(sqlite_dialect_3_8_0, 2))
        sql, _ = result.to_sql()
        assert "ROUND(" in sql

    def test_pow(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test pow() function."""
        result = pow(sqlite_dialect_3_35_0, Column(sqlite_dialect_3_35_0, "base"), Literal(sqlite_dialect_3_35_0, 2))
        sql, _ = result.to_sql()
        assert "POW(" in sql

    def test_pow_both_columns(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test pow() with both column references."""
        result = pow(sqlite_dialect_3_35_0, Column(sqlite_dialect_3_35_0, "x"), Column(sqlite_dialect_3_35_0, "y"))
        sql, _ = result.to_sql()
        assert "POW(" in sql

    def test_power(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test power() function (alias for POW)."""
        result = power(sqlite_dialect_3_35_0, Literal(sqlite_dialect_3_35_0, 2), Literal(sqlite_dialect_3_35_0, 3))
        sql, _ = result.to_sql()
        assert "POWER(" in sql

    def test_sqrt(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test sqrt() function."""
        result = sqrt(sqlite_dialect_3_35_0, Column(sqlite_dialect_3_35_0, "value"))
        sql, _ = result.to_sql()
        assert "SQRT(" in sql
        assert '"value"' in sql

    def test_sqrt_with_literal(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test sqrt() with literal value."""
        result = sqrt(sqlite_dialect_3_35_0, Literal(sqlite_dialect_3_35_0, 16))
        sql, _ = result.to_sql()
        assert "SQRT(" in sql

    def test_mod(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test mod() function."""
        result = mod(sqlite_dialect_3_35_0, Column(sqlite_dialect_3_35_0, "total"), Literal(sqlite_dialect_3_35_0, 10))
        sql, _ = result.to_sql()
        assert "MOD(" in sql

    def test_mod_both_columns(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test mod() with both column references."""
        result = mod(
            sqlite_dialect_3_35_0, Column(sqlite_dialect_3_35_0, "dividend"), Column(sqlite_dialect_3_35_0, "divisor")
        )
        sql, _ = result.to_sql()
        assert "MOD(" in sql

    def test_ceil(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test ceil() function (SQLite 3.44.0+)."""
        result = ceil(sqlite_dialect_3_38_0, Column(sqlite_dialect_3_38_0, "value"))
        sql, _ = result.to_sql()
        assert "CEIL(" in sql
        assert '"value"' in sql

    def test_ceil_with_literal(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test ceil() with literal value."""
        result = ceil(sqlite_dialect_3_38_0, Literal(sqlite_dialect_3_38_0, 3.14))
        sql, _ = result.to_sql()
        assert "CEIL(" in sql

    def test_floor(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test floor() function (SQLite 3.44.0+)."""
        result = floor(sqlite_dialect_3_38_0, Column(sqlite_dialect_3_38_0, "value"))
        sql, _ = result.to_sql()
        assert "FLOOR(" in sql
        assert '"value"' in sql

    def test_floor_with_literal(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test floor() with literal value."""
        result = floor(sqlite_dialect_3_38_0, Literal(sqlite_dialect_3_38_0, 3.14))
        sql, _ = result.to_sql()
        assert "FLOOR(" in sql

    def test_trunc(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test trunc() function."""
        result = trunc(sqlite_dialect_3_35_0, Column(sqlite_dialect_3_35_0, "value"))
        sql, _ = result.to_sql()
        assert "TRUNC(" in sql
        assert '"value"' in sql

    def test_trunc_with_literal(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test trunc() with literal value."""
        result = trunc(sqlite_dialect_3_35_0, Literal(sqlite_dialect_3_35_0, 3.14))
        sql, _ = result.to_sql()
        assert "TRUNC(" in sql

    def test_max__two_args(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test max_() with two arguments."""
        result = max_(sqlite_dialect_3_8_0, Column(sqlite_dialect_3_8_0, "a"), Column(sqlite_dialect_3_8_0, "b"))
        sql, _ = result.to_sql()
        assert "MAX(" in sql

    def test_max__multiple_args(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test max_() with multiple arguments."""
        result = max_(
            sqlite_dialect_3_8_0,
            Column(sqlite_dialect_3_8_0, "a"),
            Column(sqlite_dialect_3_8_0, "b"),
            Column(sqlite_dialect_3_8_0, "c"),
        )
        sql, _ = result.to_sql()
        assert "MAX(" in sql

    def test_max__with_literals(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test max_() with literal values."""
        result = max_(sqlite_dialect_3_8_0, Literal(sqlite_dialect_3_8_0, 1), Literal(sqlite_dialect_3_8_0, 2), Literal(sqlite_dialect_3_8_0, 3))
        sql, _ = result.to_sql()
        assert "MAX(" in sql

    def test_min__two_args(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test min_() with two arguments."""
        result = min_(sqlite_dialect_3_8_0, Column(sqlite_dialect_3_8_0, "a"), Column(sqlite_dialect_3_8_0, "b"))
        sql, _ = result.to_sql()
        assert "MIN(" in sql

    def test_min__multiple_args(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test min_() with multiple arguments."""
        result = min_(
            sqlite_dialect_3_8_0,
            Column(sqlite_dialect_3_8_0, "a"),
            Column(sqlite_dialect_3_8_0, "b"),
            Column(sqlite_dialect_3_8_0, "c"),
        )
        sql, _ = result.to_sql()
        assert "MIN(" in sql

    def test_min__with_literals(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test min_() with literal values."""
        result = min_(sqlite_dialect_3_8_0, Literal(sqlite_dialect_3_8_0, 1), Literal(sqlite_dialect_3_8_0, 2), Literal(sqlite_dialect_3_8_0, 3))
        sql, _ = result.to_sql()
        assert "MIN(" in sql

    def test_avg(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test avg() aggregate function."""
        result = avg(sqlite_dialect_3_8_0, Column(sqlite_dialect_3_8_0, "price"))
        sql, _ = result.to_sql()
        assert "AVG(" in sql
        assert '"price"' in sql

    def test_avg_with_literal(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test avg() with literal value."""
        result = avg(sqlite_dialect_3_8_0, Literal(sqlite_dialect_3_8_0, 100))
        sql, _ = result.to_sql()
        assert "AVG(" in sql

    def test_round__with_string_integer(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test round_() with string integer value."""
        result = round_(sqlite_dialect_3_8_0, Literal(sqlite_dialect_3_8_0, "123"), Literal(sqlite_dialect_3_8_0, 2))
        sql, _ = result.to_sql()
        assert "ROUND(" in sql

    def test_round__with_string_float(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test round_() with string float value."""
        result = round_(sqlite_dialect_3_8_0, Literal(sqlite_dialect_3_8_0, "3.14159"), Literal(sqlite_dialect_3_8_0, 2))
        sql, _ = result.to_sql()
        assert "ROUND(" in sql

    def test_round__of_a_column(self, sqlite_dialect: SQLiteDialect):
        """A column is named by the caller, not read out of a string.

        The old helper looked at a string argument and decided: if it parsed as
        a number it was a value, otherwise it was a column name. So
        round_(dialect, "16") squared the number 16 while round_(dialect,
        "cost") read the column -- one function, two meanings, picked by the
        spelling of the argument."""
        result = round_(sqlite_dialect, Column(sqlite_dialect, "column_name"))
        sql, _ = result.to_sql()
        assert "ROUND(" in sql
        assert '"column_name"' in sql

    def test_round__of_numeric_text_is_a_value(self, sqlite_dialect: SQLiteDialect):
        result = result_node = round_(sqlite_dialect, Literal(sqlite_dialect, "3.7"), 2)
        sql, params = result_node.to_sql()
        assert "ROUND(" in sql
        assert params == ("3.7", 2)

    def test_pow_with_string_integer(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test pow() with string integer exponent."""
        result = pow(sqlite_dialect_3_35_0, Column(sqlite_dialect_3_35_0, "base"), Literal(sqlite_dialect_3_35_0, "2"))
        sql, _ = result.to_sql()
        assert "POW(" in sql

    def test_sqrt_with_string_integer(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test sqrt() with string integer value."""
        result = sqrt(sqlite_dialect_3_35_0, Literal(sqlite_dialect_3_35_0, "16"))
        sql, _ = result.to_sql()
        assert "SQRT(" in sql

    def test_mod_with_string_divisor(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test mod() with string divisor."""
        result = mod(
            sqlite_dialect_3_35_0, Column(sqlite_dialect_3_35_0, "total"), Literal(sqlite_dialect_3_35_0, "10")
        )
        sql, _ = result.to_sql()
        assert "MOD(" in sql

    def test_max__with_string_literals(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test max_() with string numeric values."""
        result = max_(sqlite_dialect_3_8_0, Literal(sqlite_dialect_3_8_0, "1"), Literal(sqlite_dialect_3_8_0, "2"), Literal(sqlite_dialect_3_8_0, "3"))
        sql, _ = result.to_sql()
        assert "MAX(" in sql

    def test_min__with_string_literals(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test min_() with string numeric values."""
        result = min_(sqlite_dialect_3_8_0, Literal(sqlite_dialect_3_8_0, "1"), Literal(sqlite_dialect_3_8_0, "2"), Literal(sqlite_dialect_3_8_0, "3"))
        sql, _ = result.to_sql()
        assert "MIN(" in sql

    def test_avg_with_string_literal(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test avg() with string numeric value."""
        result = avg(sqlite_dialect_3_8_0, Literal(sqlite_dialect_3_8_0, "100"))
        sql, _ = result.to_sql()
        assert "AVG(" in sql

    def test_the_math_functions_are_refused_below_their_floor(self, sqlite_dialect_3_34_0: SQLiteDialect):
        """A floor the dialect records is a gate, not a footnote.

        The math functions arrived in 3.35.0, so a 3.34.0 dialect refuses them
        instead of emitting ``SQRT(...)`` and letting the server answer. The
        refusal names the function, the floor and the version in force, so the
        caller can tell an old server from a wrong spelling.
        """
        with pytest.raises(UnsupportedFeatureError) as excinfo:
            sqrt(sqlite_dialect_3_34_0, Column(sqlite_dialect_3_34_0, "value")).to_sql()
        message = str(excinfo.value)
        assert "SQRT" in message
        assert "3.35.0" in message
        assert "3.34.0" in message

    def test_the_floor_excludes_the_functions_that_have_none(
        self, sqlite_dialect_3_8_0: SQLiteDialect
    ):
        """``max_``, ``min_`` and ``avg`` record no floor -- SQLite has always
        had them -- so they render on the oldest dialect here."""
        for factory, args, spelling in (
            (max_, (Literal(sqlite_dialect_3_8_0, 1), Literal(sqlite_dialect_3_8_0, 2)), "MAX("),
            (min_, (Literal(sqlite_dialect_3_8_0, 1), Literal(sqlite_dialect_3_8_0, 2)), "MIN("),
            (avg, (Column(sqlite_dialect_3_8_0, "price"),), "AVG("),
        ):
            sql, _ = factory(sqlite_dialect_3_8_0, *args).to_sql()
            assert spelling in sql
