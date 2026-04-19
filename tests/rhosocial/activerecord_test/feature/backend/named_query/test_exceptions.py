# tests/rhosocial/activerecord_test/feature/backend/named_query/test_exceptions.py
"""
Tests for named query exceptions.

This test module covers all exception types in the named query system.
"""
import pytest
from rhosocial.activerecord.backend.named_query.exceptions import (
    NamedQueryError,
    NamedQueryNotFoundError,
    NamedQueryModuleNotFoundError,
    NamedQueryInvalidReturnTypeError,
    NamedQueryInvalidParameterError,
    NamedQueryMissingParameterError,
    NamedQueryNotCallableError,
    NamedQueryExplainNotAllowedError,
)


class TestNamedQueryError:
    def test_is_exception(self):
        """Test that NamedQueryError is an Exception subclass."""
        assert issubclass(NamedQueryError, Exception)

    def test_can_be_instantiated(self):
        """Test that NamedQueryError can be raised with a message."""
        with pytest.raises(NamedQueryError):
            raise NamedQueryError("Test error message")


class TestNamedQueryNotFoundError:
    def test_creation_with_name_only(self):
        """Test creation with just the qualified name."""
        err = NamedQueryNotFoundError("myapp.queries.user_active")
        assert err.qualified_name == "myapp.queries.user_active"
        assert "myapp.queries.user_active" in str(err)

    def test_creation_with_message(self):
        """Test creation with additional message."""
        err = NamedQueryNotFoundError("myapp.queries.user_active", "Check exports")
        assert "myapp.queries.user_active" in str(err)
        assert "Check exports" in str(err)

    def test_is_named_query_error(self):
        """Test that it inherits from NamedQueryError."""
        err = NamedQueryNotFoundError("myapp.queries.user_active")
        assert isinstance(err, NamedQueryError)


class TestNamedQueryModuleNotFoundError:
    def test_creation_with_name_only(self):
        """Test creation with just the module name."""
        err = NamedQueryModuleNotFoundError("myapp.queries")
        assert err.module_name == "myapp.queries"
        assert "myapp.queries" in str(err)

    def test_creation_with_message(self):
        """Test creation with additional message."""
        err = NamedQueryModuleNotFoundError("myapp.queries", "Not in PYTHONPATH")
        assert "myapp.queries" in str(err)
        assert "Not in PYTHONPATH" in str(err)

    def test_is_named_query_error(self):
        """Test that it inherits from NamedQueryError."""
        err = NamedQueryModuleNotFoundError("myapp.queries")
        assert isinstance(err, NamedQueryError)


class TestNamedQueryInvalidReturnTypeError:
    def test_creation(self):
        """Test creation with type information."""
        err = NamedQueryInvalidReturnTypeError(
            "myapp.queries.user_active",
            "str",
        )
        assert err.qualified_name == "myapp.queries.user_active"
        assert err.actual_type == "str"
        assert "str" in str(err)
        assert "not BaseExpression" in str(err)

    def test_creation_with_message(self):
        """Test creation with additional message."""
        err = NamedQueryInvalidReturnTypeError(
            "myapp.queries.user_active",
            "str",
            "Use query subcommand",
        )
        assert "Use query subcommand" in str(err)

    def test_is_named_query_error(self):
        """Test that it inherits from NamedQueryError."""
        err = NamedQueryInvalidReturnTypeError("myapp.queries.user_active", "str")
        assert isinstance(err, NamedQueryError)


class TestNamedQueryInvalidParameterError:
    def test_creation_with_name_only(self):
        """Test creation with just the parameter name."""
        err = NamedQueryInvalidParameterError("user_id")
        assert err.param_name == "user_id"
        assert "user_id" in str(err)

    def test_creation_with_message(self):
        """Test creation with additional message."""
        err = NamedQueryInvalidParameterError("user_id", "Unknown parameter")
        assert "user_id" in str(err)
        assert "Unknown parameter" in str(err)

    def test_is_named_query_error(self):
        """Test that it inherits from NamedQueryError."""
        err = NamedQueryInvalidParameterError("user_id")
        assert isinstance(err, NamedQueryError)


class TestNamedQueryMissingParameterError:
    def test_creation_with_name_only(self):
        """Test creation with just the parameter name."""
        err = NamedQueryMissingParameterError("user_id")
        assert err.param_name == "user_id"
        assert "user_id" in str(err)

    def test_creation_with_message(self):
        """Test creation with additional message."""
        err = NamedQueryMissingParameterError("user_id", "Required")
        assert "user_id" in str(err)
        assert "Required" in str(err)

    def test_is_named_query_error(self):
        """Test that it inherits from NamedQueryError."""
        err = NamedQueryMissingParameterError("user_id")
        assert isinstance(err, NamedQueryError)


class TestNamedQueryNotCallableError:
    def test_creation_with_name_only(self):
        """Test creation with just the qualified name."""
        err = NamedQueryNotCallableError("myapp.queries.user_active")
        assert err.qualified_name == "myapp.queries.user_active"
        assert "myapp.queries.user_active" in str(err)

    def test_creation_with_message(self):
        """Test creation with additional message."""
        err = NamedQueryNotCallableError("myapp.queries.user_active", "Not a function")
        assert "myapp.queries.user_active" in str(err)
        assert "Not a function" in str(err)

    def test_is_named_query_error(self):
        """Test that it inherits from NamedQueryError."""
        err = NamedQueryNotCallableError("myapp.queries.user_active")
        assert isinstance(err, NamedQueryError)


class TestNamedQueryExplainNotAllowedError:
    def test_default_message(self):
        """Test creation with default message."""
        err = NamedQueryExplainNotAllowedError()
        assert "EXPLAIN" in str(err)

    def test_custom_message(self):
        """Test creation with custom message."""
        err = NamedQueryExplainNotAllowedError("Custom message")
        assert str(err) == "Custom message"

    def test_is_named_query_error(self):
        """Test that it inherits from NamedQueryError."""
        err = NamedQueryExplainNotAllowedError()
        assert isinstance(err, NamedQueryError)