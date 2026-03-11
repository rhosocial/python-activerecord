# tests/rhosocial/activerecord_test/feature/backend/sqlite2/test_sqlite_specific_functions.py
"""
Tests for SQLite-specific function factories.

This test file covers SQLite-specific functions:
- String functions: substr, instr, printf, unicode, hex, unhex, trim_sqlite, ltrim, rtrim
- DateTime functions: date_func, time_func, datetime_func, julianday, strftime_func
- Aggregate functions: group_concat, total
- System functions: typeof, quote, random_func, abs_sql, sign, last_insert_rowid, changes, soundex
- Conditional functions: iif
- BLOB functions: zeroblob, randomblob
"""
import pytest
from rhosocial.activerecord.backend.expression import Column, Literal
from rhosocial.activerecord.backend.impl.sqlite.functions import (
    substr, instr, printf, unicode, hex, unhex,
    zeroblob, randomblob, soundex,
    group_concat, total,
    date_func, time_func, datetime_func, julianday, strftime_func,
    typeof, quote, random_func, abs_sql, sign,
    last_insert_rowid, changes,
    trim_sqlite, ltrim, rtrim,
    iif
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


class TestSQLiteStringFunctions:
    """Tests for SQLite-specific string functions."""

    def test_substr_function_basic(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test SUBSTR function with start position only."""
        func = substr(sqlite_dialect_3_35_0, "hello world", 1, 5)
        sql, params = func.to_sql()
        assert "SUBSTR(" in sql
        assert params == ("hello world", 1, 5)

    def test_substr_function_without_length(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test SUBSTR function without length."""
        func = substr(sqlite_dialect_3_35_0, "hello world", 7)
        sql, params = func.to_sql()
        assert "SUBSTR(" in sql
        assert params == ("hello world", 7)

    def test_substr_function_with_column(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test SUBSTR function with column."""
        col = Column(sqlite_dialect_3_35_0, "text")
        func = substr(sqlite_dialect_3_35_0, col, 1, 10)
        sql, params = func.to_sql()
        assert "SUBSTR(" in sql
        assert params == (1, 10)

    def test_instr_function_basic(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test INSTR function with strings."""
        func = instr(sqlite_dialect_3_35_0, "hello world", "world")
        sql, params = func.to_sql()
        assert "INSTR(" in sql
        assert params == ("hello world", "world")

    def test_instr_function_with_column(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test INSTR function with column."""
        col = Column(sqlite_dialect_3_35_0, "text")
        func = instr(sqlite_dialect_3_35_0, col, "search")
        sql, params = func.to_sql()
        assert "INSTR(" in sql
        assert params == ("search",)

    def test_printf_function_basic(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test PRINTF function with format string."""
        func = printf(sqlite_dialect_3_35_0, "Hello %s!", "World")
        sql, params = func.to_sql()
        assert "PRINTF(" in sql
        assert params == ("Hello %s!", "World")

    def test_printf_function_multiple_args(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test PRINTF function with multiple arguments."""
        func = printf(sqlite_dialect_3_35_0, "%s is %d years old", "Alice", 25)
        sql, params = func.to_sql()
        assert "PRINTF(" in sql
        assert params == ("%s is %d years old", "Alice", 25)

    def test_unicode_function_basic(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test UNICODE function."""
        func = unicode(sqlite_dialect_3_35_0, "A")
        sql, params = func.to_sql()
        assert "UNICODE(" in sql
        assert params == ("A",)

    def test_unicode_function_with_column(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test UNICODE function with column."""
        col = Column(sqlite_dialect_3_35_0, "char")
        func = unicode(sqlite_dialect_3_35_0, col)
        sql, params = func.to_sql()
        assert "UNICODE(" in sql
        assert params == ()

    def test_hex_function_basic(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test HEX function."""
        func = hex(sqlite_dialect_3_35_0, "hello")
        sql, params = func.to_sql()
        assert "HEX(" in sql
        assert params == ("hello",)

    def test_hex_function_with_column(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test HEX function with column."""
        col = Column(sqlite_dialect_3_35_0, "data")
        func = hex(sqlite_dialect_3_35_0, col)
        sql, params = func.to_sql()
        assert "HEX(" in sql
        assert params == ()

    def test_unhex_function_basic(self, sqlite_dialect_3_45_0: SQLiteDialect):
        """Test UNHEX function (SQLite 3.45.0+)."""
        func = unhex(sqlite_dialect_3_45_0, "68656C6C6F")
        sql, params = func.to_sql()
        assert "UNHEX(" in sql
        assert params == ("68656C6C6F",)


class TestSQLiteTrimFunctions:
    """Tests for SQLite-specific trim functions."""

    def test_trim_sqlite_basic(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test TRIM function without characters."""
        func = trim_sqlite(sqlite_dialect_3_35_0, "  hello  ")
        sql, params = func.to_sql()
        assert "TRIM(" in sql
        assert params == ("  hello  ",)

    def test_trim_sqlite_with_characters(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test TRIM function with characters."""
        func = trim_sqlite(sqlite_dialect_3_35_0, "xxyhelloxyx", "xy")
        sql, params = func.to_sql()
        assert "TRIM(" in sql
        assert params == ("xxyhelloxyx", "xy")

    def test_ltrim_basic(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test LTRIM function."""
        func = ltrim(sqlite_dialect_3_35_0, "  hello  ")
        sql, params = func.to_sql()
        assert "LTRIM(" in sql
        assert params == ("  hello  ",)

    def test_ltrim_with_characters(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test LTRIM function with characters."""
        func = ltrim(sqlite_dialect_3_35_0, "xyxhello", "xy")
        sql, params = func.to_sql()
        assert "LTRIM(" in sql
        assert params == ("xyxhello", "xy")

    def test_rtrim_basic(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test RTRIM function."""
        func = rtrim(sqlite_dialect_3_35_0, "  hello  ")
        sql, params = func.to_sql()
        assert "RTRIM(" in sql
        assert params == ("  hello  ",)

    def test_rtrim_with_characters(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test RTRIM function with characters."""
        func = rtrim(sqlite_dialect_3_35_0, "helloxyx", "xy")
        sql, params = func.to_sql()
        assert "RTRIM(" in sql
        assert params == ("helloxyx", "xy")


class TestSQLiteDateTimeFunctions:
    """Tests for SQLite-specific date/time functions."""

    def test_date_func_basic(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test DATE function."""
        func = date_func(sqlite_dialect_3_35_0, "now")
        sql, params = func.to_sql()
        assert "DATE(" in sql
        assert params == ("now",)

    def test_date_func_with_modifiers(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test DATE function with modifiers."""
        func = date_func(sqlite_dialect_3_35_0, "now", "+1 day", "-1 month")
        sql, params = func.to_sql()
        assert "DATE(" in sql
        assert params == ("now", "+1 day", "-1 month")

    def test_time_func_basic(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test TIME function."""
        func = time_func(sqlite_dialect_3_35_0, "now")
        sql, params = func.to_sql()
        assert "TIME(" in sql
        assert params == ("now",)

    def test_time_func_with_modifiers(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test TIME function with modifiers."""
        func = time_func(sqlite_dialect_3_35_0, "now", "localtime")
        sql, params = func.to_sql()
        assert "TIME(" in sql
        assert params == ("now", "localtime")

    def test_datetime_func_basic(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test DATETIME function."""
        func = datetime_func(sqlite_dialect_3_35_0, "now")
        sql, params = func.to_sql()
        assert "DATETIME(" in sql
        assert params == ("now",)

    def test_datetime_func_with_modifiers(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test DATETIME function with modifiers."""
        func = datetime_func(sqlite_dialect_3_35_0, "now", "localtime", "+1 hour")
        sql, params = func.to_sql()
        assert "DATETIME(" in sql
        assert params == ("now", "localtime", "+1 hour")

    def test_julianday_basic(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test JULIANDAY function."""
        func = julianday(sqlite_dialect_3_35_0, "now")
        sql, params = func.to_sql()
        assert "JULIANDAY(" in sql
        assert params == ("now",)

    def test_julianday_with_column(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test JULIANDAY function with column."""
        col = Column(sqlite_dialect_3_35_0, "created_at")
        func = julianday(sqlite_dialect_3_35_0, col)
        sql, params = func.to_sql()
        assert "JULIANDAY(" in sql
        assert params == ()

    def test_strftime_func_basic(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test STRFTIME function."""
        func = strftime_func(sqlite_dialect_3_35_0, "%Y-%m-%d", "now")
        sql, params = func.to_sql()
        assert "STRFTIME(" in sql
        assert params == ("%Y-%m-%d", "now")

    def test_strftime_func_with_column(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test STRFTIME function with column."""
        col = Column(sqlite_dialect_3_35_0, "timestamp")
        func = strftime_func(sqlite_dialect_3_35_0, "%H:%M", col)
        sql, params = func.to_sql()
        assert "STRFTIME(" in sql
        assert params == ("%H:%M",)


class TestSQLiteAggregateFunctions:
    """Tests for SQLite-specific aggregate functions."""

    def test_group_concat_basic(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test GROUP_CONCAT function."""
        col = Column(sqlite_dialect_3_35_0, "name")
        func = group_concat(sqlite_dialect_3_35_0, col)
        sql, params = func.to_sql()
        assert "GROUP_CONCAT(" in sql
        assert params == ()

    def test_group_concat_with_separator(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test GROUP_CONCAT function with separator."""
        col = Column(sqlite_dialect_3_35_0, "name")
        func = group_concat(sqlite_dialect_3_35_0, col, ", ")
        sql, params = func.to_sql()
        assert "GROUP_CONCAT(" in sql
        assert params == (", ",)

    def test_group_concat_distinct(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test GROUP_CONCAT function with DISTINCT."""
        col = Column(sqlite_dialect_3_35_0, "name")
        func = group_concat(sqlite_dialect_3_35_0, col, is_distinct=True)
        sql, params = func.to_sql()
        assert "GROUP_CONCAT(DISTINCT" in sql

    def test_total_function(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test TOTAL function."""
        col = Column(sqlite_dialect_3_35_0, "amount")
        func = total(sqlite_dialect_3_35_0, col)
        sql, params = func.to_sql()
        assert "TOTAL(" in sql
        assert params == ()


class TestSQLiteSystemFunctions:
    """Tests for SQLite system functions."""

    def test_typeof_function(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test TYPEOF function."""
        func = typeof(sqlite_dialect_3_35_0, "hello")
        sql, params = func.to_sql()
        assert "TYPEOF(" in sql
        assert params == ("hello",)

    def test_typeof_with_column(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test TYPEOF function with column."""
        col = Column(sqlite_dialect_3_35_0, "value")
        func = typeof(sqlite_dialect_3_35_0, col)
        sql, params = func.to_sql()
        assert "TYPEOF(" in sql
        assert params == ()

    def test_quote_function(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test QUOTE function."""
        func = quote(sqlite_dialect_3_35_0, "hello")
        sql, params = func.to_sql()
        assert "QUOTE(" in sql
        assert params == ("hello",)

    def test_random_function(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test RANDOM function."""
        func = random_func(sqlite_dialect_3_35_0)
        sql, params = func.to_sql()
        assert "RANDOM()" in sql

    def test_abs_sql_function(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test ABS function via abs_sql."""
        func = abs_sql(sqlite_dialect_3_35_0, -42)
        sql, params = func.to_sql()
        assert "ABS(" in sql
        assert params == (-42,)

    def test_sign_function(self, sqlite_dialect_3_44_0: SQLiteDialect):
        """Test SIGN function (SQLite 3.44.0+)."""
        func = sign(sqlite_dialect_3_44_0, 42)
        sql, params = func.to_sql()
        assert "SIGN(" in sql
        assert params == (42,)

    def test_last_insert_rowid_function(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test LAST_INSERT_ROWID function."""
        func = last_insert_rowid(sqlite_dialect_3_35_0)
        sql, params = func.to_sql()
        assert "LAST_INSERT_ROWID()" in sql

    def test_changes_function(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test CHANGES function."""
        func = changes(sqlite_dialect_3_35_0)
        sql, params = func.to_sql()
        assert "CHANGES()" in sql

    def test_soundex_function(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test SOUNDEX function."""
        func = soundex(sqlite_dialect_3_35_0, "Robert")
        sql, params = func.to_sql()
        assert "SOUNDEX(" in sql
        assert params == ("Robert",)


class TestSQLiteBLOBFunctions:
    """Tests for SQLite BLOB functions."""

    def test_zeroblob_function(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test ZEROBLOB function."""
        func = zeroblob(sqlite_dialect_3_35_0, 100)
        sql, params = func.to_sql()
        assert "ZEROBLOB(" in sql
        assert params == (100,)

    def test_randomblob_function(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test RANDOMBLOB function."""
        func = randomblob(sqlite_dialect_3_35_0, 16)
        sql, params = func.to_sql()
        assert "RANDOMBLOB(" in sql
        assert params == (16,)


class TestSQLiteConditionalFunctions:
    """Tests for SQLite conditional functions."""

    def test_iif_function_basic(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test IIF function."""
        col = Column(sqlite_dialect_3_35_0, "active")
        func = iif(sqlite_dialect_3_35_0, col, "yes", "no")
        sql, params = func.to_sql()
        assert "IIF(" in sql
        assert params == ("yes", "no")

    def test_iif_function_with_literal_condition(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test IIF function with literal condition."""
        from rhosocial.activerecord.backend.expression import ComparisonPredicate, Literal as Lit
        col = Column(sqlite_dialect_3_35_0, "value")
        condition = ComparisonPredicate(sqlite_dialect_3_35_0, ">", col, Lit(sqlite_dialect_3_35_0, 10))
        func = iif(sqlite_dialect_3_35_0, condition, "high", "low")
        sql, params = func.to_sql()
        assert "IIF(" in sql
        # params includes the literal value from the condition and the two result values
        assert 10 in params
        assert "high" in params
        assert "low" in params
