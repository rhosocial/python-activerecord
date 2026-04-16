# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_sql_standard_functions.py
"""
Tests for SQL standard functions added to the common functions module.

This test file covers:
- Math functions: mod, sign, truncate
- String functions: chr_, ascii, octet_length, bit_length, position, overlay, translate, repeat, space
- DateTime functions: current_timestamp, localtimestamp, extract
- User functions: current_user, session_user, system_user
"""
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import (
    mod, sign, truncate, chr_, ascii, octet_length, bit_length,
    position, overlay, translate, repeat, space,
    current_timestamp, localtimestamp, extract,
    current_user, session_user, system_user
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestSQLStandardMathFunctions:
    """Tests for SQL standard math functions."""

    def test_mod_function_basic(self, dummy_dialect: DummyDialect):
        """Test MOD function with basic values."""
        func = mod(dummy_dialect, 10, 3)
        sql, params = func.to_sql()
        assert "MOD(" in sql
        assert params == (10, 3)

    def test_mod_function_with_columns(self, dummy_dialect: DummyDialect):
        """Test MOD function with column expressions."""
        col1 = Column(dummy_dialect, "dividend")
        col2 = Column(dummy_dialect, "divisor")
        func = mod(dummy_dialect, col1, col2)
        sql, params = func.to_sql()
        assert "MOD(" in sql
        assert params == ()

    def test_sign_function_positive(self, dummy_dialect: DummyDialect):
        """Test SIGN function with positive number."""
        func = sign(dummy_dialect, 42)
        sql, params = func.to_sql()
        assert "SIGN(" in sql
        assert params == (42,)

    def test_sign_function_negative(self, dummy_dialect: DummyDialect):
        """Test SIGN function with negative number."""
        func = sign(dummy_dialect, -10)
        sql, params = func.to_sql()
        assert "SIGN(" in sql
        assert params == (-10,)

    def test_sign_function_zero(self, dummy_dialect: DummyDialect):
        """Test SIGN function with zero."""
        func = sign(dummy_dialect, 0)
        sql, params = func.to_sql()
        assert "SIGN(" in sql
        assert params == (0,)

    def test_sign_function_with_column(self, dummy_dialect: DummyDialect):
        """Test SIGN function with column."""
        col = Column(dummy_dialect, "value")
        func = sign(dummy_dialect, col)
        sql, params = func.to_sql()
        assert "SIGN(" in sql
        assert params == ()

    def test_truncate_function_basic(self, dummy_dialect: DummyDialect):
        """Test TRUNCATE function without precision."""
        func = truncate(dummy_dialect, 3.14159)
        sql, params = func.to_sql()
        assert "TRUNCATE(" in sql
        assert params == (3.14159,)

    def test_truncate_function_with_precision(self, dummy_dialect: DummyDialect):
        """Test TRUNCATE function with precision."""
        func = truncate(dummy_dialect, 3.14159, 2)
        sql, params = func.to_sql()
        assert "TRUNCATE(" in sql
        assert params == (3.14159, 2)

    def test_truncate_function_with_column(self, dummy_dialect: DummyDialect):
        """Test TRUNCATE function with column."""
        col = Column(dummy_dialect, "price")
        func = truncate(dummy_dialect, col, 2)
        sql, params = func.to_sql()
        assert "TRUNCATE(" in sql
        assert params == (2,)


class TestSQLStandardStringFunctions:
    """Tests for SQL standard string functions."""

    def test_chr_function_basic(self, dummy_dialect: DummyDialect):
        """Test CHR function with integer code."""
        func = chr_(dummy_dialect, 65)
        sql, params = func.to_sql()
        assert "CHR(" in sql
        assert params == (65,)

    def test_chr_function_with_column(self, dummy_dialect: DummyDialect):
        """Test CHR function with column."""
        col = Column(dummy_dialect, "char_code")
        func = chr_(dummy_dialect, col)
        sql, params = func.to_sql()
        assert "CHR(" in sql
        assert params == ()

    def test_ascii_function_basic(self, dummy_dialect: DummyDialect):
        """Test ASCII function with string."""
        func = ascii(dummy_dialect, "A")
        sql, params = func.to_sql()
        assert "ASCII(" in sql
        assert params == ("A",)

    def test_ascii_function_with_column(self, dummy_dialect: DummyDialect):
        """Test ASCII function with column."""
        col = Column(dummy_dialect, "first_char")
        func = ascii(dummy_dialect, col)
        sql, params = func.to_sql()
        assert "ASCII(" in sql
        assert params == ()

    def test_octet_length_function_basic(self, dummy_dialect: DummyDialect):
        """Test OCTET_LENGTH function with string."""
        func = octet_length(dummy_dialect, "hello")
        sql, params = func.to_sql()
        assert "OCTET_LENGTH(" in sql
        assert params == ("hello",)

    def test_octet_length_function_with_column(self, dummy_dialect: DummyDialect):
        """Test OCTET_LENGTH function with column."""
        col = Column(dummy_dialect, "text_data")
        func = octet_length(dummy_dialect, col)
        sql, params = func.to_sql()
        assert "OCTET_LENGTH(" in sql
        assert params == ()

    def test_bit_length_function_basic(self, dummy_dialect: DummyDialect):
        """Test BIT_LENGTH function with string."""
        func = bit_length(dummy_dialect, "hello")
        sql, params = func.to_sql()
        assert "BIT_LENGTH(" in sql
        assert params == ("hello",)

    def test_bit_length_function_with_column(self, dummy_dialect: DummyDialect):
        """Test BIT_LENGTH function with column."""
        col = Column(dummy_dialect, "text_data")
        func = bit_length(dummy_dialect, col)
        sql, params = func.to_sql()
        assert "BIT_LENGTH(" in sql
        assert params == ()

    def test_position_function_basic(self, dummy_dialect: DummyDialect):
        """Test POSITION function with strings."""
        func = position(dummy_dialect, "world", "hello world")
        sql, params = func.to_sql()
        assert "POSITION(" in sql
        assert params == ("world", "hello world")

    def test_position_function_with_column(self, dummy_dialect: DummyDialect):
        """Test POSITION function with column."""
        col = Column(dummy_dialect, "text")
        func = position(dummy_dialect, "search", col)
        sql, params = func.to_sql()
        assert "POSITION(" in sql
        assert params == ("search",)

    def test_overlay_function_basic(self, dummy_dialect: DummyDialect):
        """Test OVERLAY function without length."""
        func = overlay(dummy_dialect, "hello world", "xxx", 1)
        sql, params = func.to_sql()
        assert "OVERLAY(" in sql
        assert params == ("hello world", "xxx", 1)

    def test_overlay_function_with_length(self, dummy_dialect: DummyDialect):
        """Test OVERLAY function with length."""
        func = overlay(dummy_dialect, "hello world", "xx", 1, 2)
        sql, params = func.to_sql()
        assert "OVERLAY(" in sql
        assert params == ("hello world", "xx", 1, 2)

    def test_overlay_function_with_column(self, dummy_dialect: DummyDialect):
        """Test OVERLAY function with column."""
        col = Column(dummy_dialect, "text")
        func = overlay(dummy_dialect, col, "new", 5, 3)
        sql, params = func.to_sql()
        assert "OVERLAY(" in sql
        assert params == ("new", 5, 3)

    def test_translate_function_basic(self, dummy_dialect: DummyDialect):
        """Test TRANSLATE function with strings."""
        func = translate(dummy_dialect, "hello", "el", "ip")
        sql, params = func.to_sql()
        assert "TRANSLATE(" in sql
        assert params == ("hello", "el", "ip")

    def test_translate_function_with_column(self, dummy_dialect: DummyDialect):
        """Test TRANSLATE function with column."""
        col = Column(dummy_dialect, "text")
        func = translate(dummy_dialect, col, "abc", "xyz")
        sql, params = func.to_sql()
        assert "TRANSLATE(" in sql
        assert params == ("abc", "xyz")

    def test_repeat_function_basic(self, dummy_dialect: DummyDialect):
        """Test REPEAT function with string and count."""
        func = repeat(dummy_dialect, "ab", 3)
        sql, params = func.to_sql()
        assert "REPEAT(" in sql
        assert params == ("ab", 3)

    def test_repeat_function_with_column(self, dummy_dialect: DummyDialect):
        """Test REPEAT function with column."""
        col = Column(dummy_dialect, "pattern")
        func = repeat(dummy_dialect, col, 5)
        sql, params = func.to_sql()
        assert "REPEAT(" in sql
        assert params == (5,)

    def test_space_function_basic(self, dummy_dialect: DummyDialect):
        """Test SPACE function with count."""
        func = space(dummy_dialect, 5)
        sql, params = func.to_sql()
        assert "SPACE(" in sql
        assert params == (5,)


class TestSQLStandardDateTimeFunctions:
    """Tests for SQL standard date/time functions."""

    def test_current_timestamp_function_basic(self, dummy_dialect: DummyDialect):
        """Test CURRENT_TIMESTAMP function without precision."""
        func = current_timestamp(dummy_dialect)
        sql, params = func.to_sql()
        assert sql == "CURRENT_TIMESTAMP"
        assert params == ()

    def test_current_timestamp_function_with_precision(self, dummy_dialect: DummyDialect):
        """Test CURRENT_TIMESTAMP function with precision."""
        func = current_timestamp(dummy_dialect, 6)
        sql, params = func.to_sql()
        assert "CURRENT_TIMESTAMP(" in sql
        assert params == (6,)

    def test_localtimestamp_function_basic(self, dummy_dialect: DummyDialect):
        """Test LOCALTIMESTAMP function without precision."""
        func = localtimestamp(dummy_dialect)
        sql, params = func.to_sql()
        assert sql == "LOCALTIMESTAMP"
        assert params == ()

    def test_localtimestamp_function_with_precision(self, dummy_dialect: DummyDialect):
        """Test LOCALTIMESTAMP function with precision."""
        func = localtimestamp(dummy_dialect, 6)
        sql, params = func.to_sql()
        assert "LOCALTIMESTAMP(" in sql
        assert params == (6,)

    def test_extract_function_basic(self, dummy_dialect: DummyDialect):
        """Test EXTRACT function with field and column."""
        col = Column(dummy_dialect, "created_at")
        func = extract(dummy_dialect, "YEAR", col)
        sql, params = func.to_sql()
        assert "EXTRACT(" in sql
        assert params == ("YEAR",)

    def test_extract_function_with_literal(self, dummy_dialect: DummyDialect):
        """Test EXTRACT function with literal date."""
        func = extract(dummy_dialect, "MONTH", "CURRENT_DATE")
        sql, params = func.to_sql()
        assert "EXTRACT(" in sql
        assert params == ("MONTH", "CURRENT_DATE")


class TestSQLStandardUserFunctions:
    """Tests for SQL standard user functions."""

    def test_current_user_function(self, dummy_dialect: DummyDialect):
        """Test CURRENT_USER function."""
        func = current_user(dummy_dialect)
        sql, params = func.to_sql()
        assert sql == "CURRENT_USER"
        assert params == ()

    def test_session_user_function(self, dummy_dialect: DummyDialect):
        """Test SESSION_USER function."""
        func = session_user(dummy_dialect)
        sql, params = func.to_sql()
        assert sql == "SESSION_USER"
        assert params == ()

    def test_system_user_function(self, dummy_dialect: DummyDialect):
        """Test SYSTEM_USER function."""
        func = system_user(dummy_dialect)
        sql, params = func.to_sql()
        assert sql == "SYSTEM_USER"
        assert params == ()
