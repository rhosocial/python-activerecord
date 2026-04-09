# tests/rhosocial/activerecord_test/feature/backend/sqlite2/test_sqlite_math_enhanced_functions.py
"""
Tests for SQLite-specific enhanced math functions.
These include additional mathematical functions beyond the basic math module.
"""
from rhosocial.activerecord.backend.expression import Column
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
        result = round_(sqlite_dialect_3_8_0, Column(sqlite_dialect_3_8_0, "price"), 2)
        sql, _ = result.to_sql()
        assert "ROUND(" in sql
        # precision is stored as literal in expression, not as param

    def test_round__with_literal(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test round_() with literal value."""
        result = round_(sqlite_dialect_3_8_0, 3.14159, 2)
        sql, _ = result.to_sql()
        assert "ROUND(" in sql

    def test_pow(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test pow() function."""
        result = pow(sqlite_dialect_3_8_0, Column(sqlite_dialect_3_8_0, "base"), 2)
        sql, _ = result.to_sql()
        assert "POW(" in sql

    def test_pow_both_columns(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test pow() with both column references."""
        result = pow(
            sqlite_dialect_3_8_0,
            Column(sqlite_dialect_3_8_0, "x"),
            Column(sqlite_dialect_3_8_0, "y")
        )
        sql, _ = result.to_sql()
        assert "POW(" in sql

    def test_power(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test power() function (alias for POW)."""
        result = power(sqlite_dialect_3_8_0, 2, 3)
        sql, _ = result.to_sql()
        assert "POWER(" in sql

    def test_sqrt(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test sqrt() function."""
        result = sqrt(sqlite_dialect_3_8_0, Column(sqlite_dialect_3_8_0, "value"))
        sql, _ = result.to_sql()
        assert "SQRT(" in sql
        assert '"value"' in sql

    def test_sqrt_with_literal(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test sqrt() with literal value."""
        result = sqrt(sqlite_dialect_3_8_0, 16)
        sql, _ = result.to_sql()
        assert "SQRT(" in sql

    def test_mod(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test mod() function."""
        result = mod(sqlite_dialect_3_8_0, Column(sqlite_dialect_3_8_0, "total"), 10)
        sql, _ = result.to_sql()
        assert "MOD(" in sql

    def test_mod_both_columns(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test mod() with both column references."""
        result = mod(
            sqlite_dialect_3_8_0,
            Column(sqlite_dialect_3_8_0, "dividend"),
            Column(sqlite_dialect_3_8_0, "divisor")
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
        result = ceil(sqlite_dialect_3_38_0, 3.14)
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
        result = floor(sqlite_dialect_3_38_0, 3.14)
        sql, _ = result.to_sql()
        assert "FLOOR(" in sql

    def test_trunc(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test trunc() function."""
        result = trunc(sqlite_dialect_3_8_0, Column(sqlite_dialect_3_8_0, "value"))
        sql, _ = result.to_sql()
        assert "TRUNC(" in sql
        assert '"value"' in sql

    def test_trunc_with_literal(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test trunc() with literal value."""
        result = trunc(sqlite_dialect_3_8_0, 3.14)
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
            Column(sqlite_dialect_3_8_0, "c")
        )
        sql, _ = result.to_sql()
        assert "MAX(" in sql

    def test_max__with_literals(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test max_() with literal values."""
        result = max_(sqlite_dialect_3_8_0, 1, 2, 3)
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
            Column(sqlite_dialect_3_8_0, "c")
        )
        sql, _ = result.to_sql()
        assert "MIN(" in sql

    def test_min__with_literals(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test min_() with literal values."""
        result = min_(sqlite_dialect_3_8_0, 1, 2, 3)
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
        result = avg(sqlite_dialect_3_8_0, 100)
        sql, _ = result.to_sql()
        assert "AVG(" in sql

    def test_round__with_string_integer(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test round_() with string integer value."""
        result = round_(sqlite_dialect_3_8_0, "123", 2)
        sql, _ = result.to_sql()
        assert "ROUND(" in sql

    def test_round__with_string_float(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test round_() with string float value."""
        result = round_(sqlite_dialect_3_8_0, "3.14159", 2)
        sql, _ = result.to_sql()
        assert "ROUND(" in sql

    def test_round__with_string_column_name(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test round_() with non-numeric string treated as column."""
        result = round_(sqlite_dialect_3_8_0, "column_name", 2)
        sql, _ = result.to_sql()
        assert "ROUND(" in sql
        assert '"column_name"' in sql

    def test_pow_with_string_integer(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test pow() with string integer exponent."""
        result = pow(sqlite_dialect_3_8_0, Column(sqlite_dialect_3_8_0, "base"), "2")
        sql, _ = result.to_sql()
        assert "POW(" in sql

    def test_sqrt_with_string_integer(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test sqrt() with string integer value."""
        result = sqrt(sqlite_dialect_3_8_0, "16")
        sql, _ = result.to_sql()
        assert "SQRT(" in sql

    def test_mod_with_string_divisor(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test mod() with string divisor."""
        result = mod(sqlite_dialect_3_8_0, Column(sqlite_dialect_3_8_0, "total"), "10")
        sql, _ = result.to_sql()
        assert "MOD(" in sql

    def test_max__with_string_literals(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test max_() with string numeric values."""
        result = max_(sqlite_dialect_3_8_0, "1", "2", "3")
        sql, _ = result.to_sql()
        assert "MAX(" in sql

    def test_min__with_string_literals(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test min_() with string numeric values."""
        result = min_(sqlite_dialect_3_8_0, "1", "2", "3")
        sql, _ = result.to_sql()
        assert "MIN(" in sql

    def test_avg_with_string_literal(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test avg() with string numeric value."""
        result = avg(sqlite_dialect_3_8_0, "100")
        sql, _ = result.to_sql()
        assert "AVG(" in sql
