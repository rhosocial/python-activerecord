# tests/rhosocial/activerecord_test/feature/backend/named_expression/test_exceptions.py
"""
Tests for named query exceptions.

This test module covers all exception types in the named query system.
"""
from typing import List
import pytest
from rhosocial.activerecord.backend.named_expression.exceptions import (
    NamedExpressionError,
    NamedExpressionNotFoundError,
    NamedExpressionModuleNotFoundError,
    NamedExpressionInvalidReturnTypeError,
    NamedExpressionInvalidParameterError,
    NamedExpressionMissingParameterError,
    NamedExpressionNotCallableError,
    NamedExpressionExplainNotAllowedError,
)


class TestNamedExpressionError:
    def test_is_exception(self):
        """Test that NamedExpressionError is an Exception subclass."""
        assert issubclass(NamedExpressionError, Exception)

    def test_can_be_instantiated(self):
        """Test that NamedExpressionError can be raised with a message."""
        with pytest.raises(NamedExpressionError):
            raise NamedExpressionError("Test error message")


class TestNamedExpressionNotFoundError:
    def test_creation_with_name_only(self):
        """Test creation with just the qualified name."""
        err = NamedExpressionNotFoundError("myapp.queries.user_active")
        assert err.qualified_name == "myapp.queries.user_active"
        assert "myapp.queries.user_active" in str(err)

    def test_creation_with_message(self):
        """Test creation with additional message."""
        err = NamedExpressionNotFoundError("myapp.queries.user_active", "Check exports")
        assert "myapp.queries.user_active" in str(err)
        assert "Check exports" in str(err)

    def test_is_named_expression_error(self):
        """Test that it inherits from NamedExpressionError."""
        err = NamedExpressionNotFoundError("myapp.queries.user_active")
        assert isinstance(err, NamedExpressionError)


class TestNamedExpressionModuleNotFoundError:
    def test_creation_with_name_only(self):
        """Test creation with just the module name."""
        err = NamedExpressionModuleNotFoundError("myapp.queries")
        assert err.module_name == "myapp.queries"
        assert "myapp.queries" in str(err)

    def test_creation_with_message(self):
        """Test creation with additional message."""
        err = NamedExpressionModuleNotFoundError("myapp.queries", "Not in PYTHONPATH")
        assert "myapp.queries" in str(err)
        assert "Not in PYTHONPATH" in str(err)

    def test_is_named_expression_error(self):
        """Test that it inherits from NamedExpressionError."""
        err = NamedExpressionModuleNotFoundError("myapp.queries")
        assert isinstance(err, NamedExpressionError)


class TestNamedExpressionInvalidReturnTypeError:
    def test_creation(self):
        """Test creation with type information."""
        err = NamedExpressionInvalidReturnTypeError(
            "myapp.queries.user_active",
            "str",
        )
        assert err.qualified_name == "myapp.queries.user_active"
        assert err.actual_type == "str"
        assert "str" in str(err)
        assert "not BaseExpression" in str(err)

    def test_creation_with_message(self):
        """Test creation with additional message."""
        err = NamedExpressionInvalidReturnTypeError(
            "myapp.queries.user_active",
            "str",
            "Use query subcommand",
        )
        assert "Use query subcommand" in str(err)

    def test_is_named_expression_error(self):
        """Test that it inherits from NamedExpressionError."""
        err = NamedExpressionInvalidReturnTypeError("myapp.queries.user_active", "str")
        assert isinstance(err, NamedExpressionError)


class TestNamedExpressionInvalidParameterError:
    def test_creation_with_name_only(self):
        """Test creation with just the parameter name."""
        err = NamedExpressionInvalidParameterError("user_id")
        assert err.param_name == "user_id"
        assert "user_id" in str(err)

    def test_creation_with_message(self):
        """Test creation with additional message."""
        err = NamedExpressionInvalidParameterError("user_id", "Unknown parameter")
        assert "user_id" in str(err)
        assert "Unknown parameter" in str(err)

    def test_is_named_expression_error(self):
        """Test that it inherits from NamedExpressionError."""
        err = NamedExpressionInvalidParameterError("user_id")
        assert isinstance(err, NamedExpressionError)


class TestNamedExpressionMissingParameterError:
    def test_creation_with_name_only(self):
        """Test creation with just the parameter name."""
        err = NamedExpressionMissingParameterError("user_id")
        assert err.param_name == "user_id"
        assert "user_id" in str(err)

    def test_creation_with_message(self):
        """Test creation with additional message."""
        err = NamedExpressionMissingParameterError("user_id", "Required")
        assert "user_id" in str(err)
        assert "Required" in str(err)

    def test_is_named_expression_error(self):
        """Test that it inherits from NamedExpressionError."""
        err = NamedExpressionMissingParameterError("user_id")
        assert isinstance(err, NamedExpressionError)


class TestNamedExpressionNotCallableError:
    def test_creation_with_name_only(self):
        """Test creation with just the qualified name."""
        err = NamedExpressionNotCallableError("myapp.queries.user_active")
        assert err.qualified_name == "myapp.queries.user_active"
        assert "myapp.queries.user_active" in str(err)

    def test_creation_with_message(self):
        """Test creation with additional message."""
        err = NamedExpressionNotCallableError("myapp.queries.user_active", "Not a function")
        assert "myapp.queries.user_active" in str(err)
        assert "Not a function" in str(err)

    def test_is_named_expression_error(self):
        """Test that it inherits from NamedExpressionError."""
        err = NamedExpressionNotCallableError("myapp.queries.user_active")
        assert isinstance(err, NamedExpressionError)


class TestNamedExpressionExplainNotAllowedError:
    def test_default_message(self):
        """Test creation with default message."""
        err = NamedExpressionExplainNotAllowedError()
        assert "EXPLAIN" in str(err)

    def test_custom_message(self):
        """Test creation with custom message."""
        err = NamedExpressionExplainNotAllowedError("Custom message")
        assert str(err) == "Custom message"

    def test_is_named_expression_error(self):
        """Test that it inherits from NamedExpressionError."""
        err = NamedExpressionExplainNotAllowedError()
        assert isinstance(err, NamedExpressionError)