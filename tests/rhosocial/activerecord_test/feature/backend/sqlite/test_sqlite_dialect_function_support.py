# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_sqlite_dialect_function_support.py
"""
Test SQLFunctionSupport protocol implementation for SQLite dialect.

This module tests the supports_functions() method and version-dependent
function availability detection in SQLiteDialect.
"""
import pytest
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


class TestSQLiteFunctionSupportBasic:
    """Basic tests for SQLite function support detection."""

    def test_supports_functions_returns_dict(self):
        """Test that supports_functions returns a dictionary."""
        dialect = SQLiteDialect()
        result = dialect.supports_functions()
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_supports_functions_all_values_are_bool(self):
        """Test that all values in the returned dict are booleans."""
        dialect = SQLiteDialect()
        result = dialect.supports_functions()
        for func_name, supported in result.items():
            assert isinstance(supported, bool), f"Value for {func_name} is not bool"

    def test_core_functions_always_supported(self):
        """Test that core functions are marked as supported."""
        dialect = SQLiteDialect()
        result = dialect.supports_functions()
        core_functions = ["count", "sum", "avg", "min", "max", "coalesce", "nullif"]
        for func in core_functions:
            assert func in result, f"Core function {func} not in result"
            assert result[func] is True, f"Core function {func} should be supported"


class TestSQLiteFunctionSupportVersionDependent:
    """Tests for version-dependent function support."""

    def test_json_functions_available_in_all_versions(self):
        """Test that JSON functions are available (via extension or built-in)."""
        dialect = SQLiteDialect()
        result = dialect.supports_functions()

        json_functions = ["json", "json_array", "json_object", "json_extract",
                         "json_type", "json_valid"]
        for func in json_functions:
            assert func in result, f"JSON function {func} not in result"

    def test_iif_requires_version_3_32(self):
        """Test that iif function requires SQLite 3.32+."""
        dialect_old = SQLiteDialect(version=(3, 31, 0))
        result_old = dialect_old.supports_functions()
        assert result_old.get("iif") is False

        dialect_new = SQLiteDialect(version=(3, 32, 0))
        result_new = dialect_new.supports_functions()
        assert result_new.get("iif") is True

    def test_json_array_insert_requires_version_3_53(self):
        """Test that json_array_insert requires SQLite 3.53+."""
        dialect_old = SQLiteDialect(version=(3, 52, 0))
        result_old = dialect_old.supports_functions()
        assert result_old.get("json_array_insert") is False
        assert result_old.get("jsonb_array_insert") is False

        dialect_new = SQLiteDialect(version=(3, 53, 0))
        result_new = dialect_new.supports_functions()
        assert result_new.get("json_array_insert") is True
        assert result_new.get("jsonb_array_insert") is True

    def test_unhex_requires_version_3_45(self):
        """Test that unhex function requires SQLite 3.45+."""
        dialect_old = SQLiteDialect(version=(3, 44, 0))
        result_old = dialect_old.supports_functions()
        assert result_old.get("unhex") is False

        dialect_new = SQLiteDialect(version=(3, 45, 0))
        result_new = dialect_new.supports_functions()
        assert result_new.get("unhex") is True

    def test_math_enhanced_functions_require_version_3_35(self):
        """Test that enhanced math functions require SQLite 3.35+."""
        math_enhanced = ["pow", "power", "sqrt", "mod", "ceil", "floor", "trunc"]

        dialect_old = SQLiteDialect(version=(3, 34, 0))
        result_old = dialect_old.supports_functions()
        for func in math_enhanced:
            assert result_old.get(func) is False

        dialect_new = SQLiteDialect(version=(3, 35, 0))
        result_new = dialect_new.supports_functions()
        for func in math_enhanced:
            assert result_new.get(func) is True

    def test_sign_requires_version_3_21(self):
        """Test that sign function requires SQLite 3.21+."""
        dialect_old = SQLiteDialect(version=(3, 20, 0))
        result_old = dialect_old.supports_functions()
        assert result_old.get("sign") is False

        dialect_new = SQLiteDialect(version=(3, 21, 0))
        result_new = dialect_new.supports_functions()
        assert result_new.get("sign") is True

    def test_always_available_functions(self):
        """Test functions that are available in all SQLite versions."""
        dialect = SQLiteDialect()
        result = dialect.supports_functions()

        always_available = [
            "substr", "printf", "unicode", "hex",
            "date_func", "time_func", "datetime_func", "julianday", "strftime_func",
            "random_func", "abs_sql", "total", "round_",
            "zeroblob", "randomblob",
            "typeof", "quote", "last_insert_rowid", "changes",
        ]
        for func in always_available:
            assert result.get(func) is True, f"{func} should be always available"


class TestSQLiteFunctionSupportPrivateMethod:
    """Tests for the private _is_sqlite_function_supported method."""

    def test_unknown_function_returns_true(self):
        """Test that unknown functions return True (no restriction)."""
        dialect = SQLiteDialect()
        result = dialect._is_sqlite_function_supported("unknown_function_xyz")
        assert result is True

    def test_version_restricted_function_below_minimum(self):
        """Test that version-restricted function returns False below minimum."""
        dialect = SQLiteDialect(version=(3, 30, 0))
        result = dialect._is_sqlite_function_supported("iif")
        assert result is False

    def test_version_restricted_function_at_minimum(self):
        """Test that version-restricted function returns True at minimum."""
        dialect = SQLiteDialect(version=(3, 32, 0))
        result = dialect._is_sqlite_function_supported("iif")
        assert result is True

    def test_version_restricted_function_above_minimum(self):
        """Test that version-restricted function returns True above minimum."""
        dialect = SQLiteDialect(version=(3, 40, 0))
        result = dialect._is_sqlite_function_supported("iif")
        assert result is True


class TestSQLiteFunctionSupportIntegration:
    """Integration tests for function support detection."""

    def test_function_dict_contains_both_core_and_backend_functions(self):
        """Test that the result contains both core and SQLite-specific functions."""
        dialect = SQLiteDialect()
        result = dialect.supports_functions()

        assert any(func in result for func in ["count", "sum", "avg"])
        assert any(func in result for func in ["substr", "instr", "printf"])

    def test_function_support_changes_with_version(self):
        """Test that function support changes across different versions."""
        old_dialect = SQLiteDialect(version=(3, 20, 0))
        new_dialect = SQLiteDialect(version=(3, 55, 0))

        old_result = old_dialect.supports_functions()
        new_result = new_dialect.supports_functions()

        assert old_result.get("sign") is False
        assert new_result.get("sign") is True

        assert old_result.get("ceil") is False
        assert new_result.get("ceil") is True
