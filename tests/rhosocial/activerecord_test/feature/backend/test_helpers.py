# tests/rhosocial/activerecord_test/feature/backend/test_helpers.py
import pytest
from rhosocial.activerecord.backend.helpers import format_with_length

class TestFormatWithLength:
    """Tests for the format_with_length helper function."""

    def test_format_with_length_provided(self):
        """Tests that the function correctly formats a type with a given length."""
        base_type = "VARCHAR"
        params = {"length": 255}
        result = format_with_length(base_type, params)
        assert result == "VARCHAR(255)"

    def test_format_with_length_not_provided(self):
        """Tests that the function returns the base type when length is not provided."""
        base_type = "TEXT"
        params = {}
        result = format_with_length(base_type, params)
        assert result == "TEXT"

    def test_format_with_length_zero(self):
        """Tests that the function correctly formats a type with length zero."""
        base_type = "VARCHAR"
        params = {"length": 0}
        result = format_with_length(base_type, params)
        assert result == "VARCHAR(0)"

    def test_format_with_other_params(self):
        """Tests that the function ignores other parameters in the dictionary."""
        base_type = "CHAR"
        params = {"length": 10, "another_param": "ignore"}
        result = format_with_length(base_type, params)
        assert result == "CHAR(10)"

    def test_format_with_length_none(self):
        """Tests that the function returns the base type when length is None."""
        base_type = "TEXT"
        params = {"length": None}
        result = format_with_length(base_type, params)
        assert result == "TEXT"
