# tests/rhosocial/activerecord_test/feature/backend/named_query/test_resolver.py
"""
Tests for named query resolver.

This test module covers:
- NamedQueryResolver class
- validate_expression function
- resolve_named_query function
- list_named_queries_in_module function
"""
import types
from unittest.mock import MagicMock, patch
import pytest
from rhosocial.activerecord.backend.named_query.resolver import (
    NamedQueryResolver,
    validate_expression,
    list_named_queries_in_module,
)
from rhosocial.activerecord.backend.named_query.exceptions import (
    NamedQueryNotFoundError,
    NamedQueryModuleNotFoundError,
    NamedQueryInvalidReturnTypeError,
    NamedQueryNotCallableError,
)
from rhosocial.activerecord.backend.schema import StatementType


class DummyCallable:
    """Dummy callable for testing."""

    def __call__(self, dialect, limit: int = 100):
        return MagicMock()


class TestNamedQueryResolverInit:
    """Tests for NamedQueryResolver.__init__."""

    def test_valid_qualified_name(self):
        """Test initialization with valid qualified name."""
        resolver = NamedQueryResolver("myapp.queries.user_active")
        assert resolver.qualified_name == "myapp.queries.user_active"

    def test_invalid_qualified_name_no_dot(self):
        """Test initialization fails without dot."""
        with pytest.raises(NamedQueryNotFoundError) as exc:
            NamedQueryResolver("nodot")
        assert "must be in the format" in str(exc.value)

    def test_valid_qualified_name_nested_module(self):
        """Test initialization with nested module (3 parts)."""
        resolver = NamedQueryResolver("my.app.queries.user_active")
        assert resolver.qualified_name == "my.app.queries.user_active"

    def test_empty_qualified_name(self):
        """Test initialization fails with empty name."""
        with pytest.raises(NamedQueryNotFoundError):
            NamedQueryResolver("")


class TestNamedQueryResolverLoad:
    """Tests for NamedQueryResolver.load()."""

    def test_load_function_success(self, mock_dialect):
        """Test loading a function successfully."""
        module = types.ModuleType("test_queries")

        def test_func(dialect, limit: int = 100):
            pass

        module.test_func = test_func
        with patch("importlib.import_module", return_value=module):
            resolver = NamedQueryResolver("test_queries.test_func").load()
            assert resolver._callable is not None
            assert resolver._target_callable is not None

    def test_load_class_success(self, mock_dialect):
        """Test loading a class successfully."""
        module = types.ModuleType("test_query_classes")
        module.DummyCallable = DummyCallable
        with patch("importlib.import_module", return_value=module):
            resolver = NamedQueryResolver("test_query_classes.DummyCallable").load()
            assert resolver._is_class is True
            assert resolver._instance is not None

    def test_load_module_not_found(self):
        """Test loading fails when module doesn't exist."""
        with pytest.raises(NamedQueryModuleNotFoundError):
            NamedQueryResolver("nonexistent.module.func").load()

    def test_load_attribute_not_found(self):
        """Test loading fails when attribute doesn't exist."""
        module = types.ModuleType("test_queries")
        module.__all__ = []
        with patch("importlib.import_module", return_value=module):
            with pytest.raises(NamedQueryNotFoundError) as exc:
                NamedQueryResolver("test_queries.nonexistent").load()
            assert "not found" in str(exc.value)

    def test_load_not_callable(self):
        """Test loading fails when attribute is not callable."""
        module = types.ModuleType("test_non_callable")
        module.not_callable = "just a string"

        with patch("importlib.import_module", return_value=module):
            with pytest.raises(NamedQueryNotCallableError):
                NamedQueryResolver("test_non_callable.not_callable").load()


class TestNamedQueryResolverSignature:
    """Tests for NamedQueryResolver.get_signature()."""

    def test_get_signature_after_load(self, mock_dialect):
        """Test getting signature after loading."""
        module = types.ModuleType("test_queries")

        def test_func(dialect, limit: int = 100):
            pass

        module.test_func = test_func
        with patch("importlib.import_module", return_value=module):
            resolver = NamedQueryResolver("test_queries.test_func").load()
            sig = resolver.get_signature()
            assert "limit" in sig.parameters

    def test_get_signature_before_load(self):
        """Test getting signature before loading fails."""
        resolver = NamedQueryResolver("myapp.queries.func")
        with pytest.raises(NamedQueryNotCallableError):
            resolver.get_signature()


class TestNamedQueryResolverUserParams:
    """Tests for NamedQueryResolver.get_user_params()."""

    def test_get_user_params_function(self, mock_dialect):
        """Test getting user params for a function."""
        module = types.ModuleType("test_queries")

        def test_func(dialect, limit: int = 100):
            pass

        module.test_func = test_func
        with patch("importlib.import_module", return_value=module):
            resolver = NamedQueryResolver("test_queries.test_func").load()
            params = resolver.get_user_params()
            assert "limit" in params

    def test_get_user_params_excludes_dialect(self, mock_dialect):
        """Test that dialect is excluded from user params."""
        module = types.ModuleType("test_queries")

        def test_func(dialect, limit: int = 100):
            pass

        module.test_func = test_func
        with patch("importlib.import_module", return_value=module):
            resolver = NamedQueryResolver("test_queries.test_func").load()
            params = resolver.get_user_params()
            assert "dialect" not in params


class TestNamedQueryResolverDescribe:
    """Tests for NamedQueryResolver.describe()."""

    def test_describe_function(self, mock_dialect):
        """Test describing a function."""
        module = types.ModuleType("test_queries")

        def test_func(dialect, limit: int = 100):
            """Test function docstring."""

        module.test_func = test_func
        with patch("importlib.import_module", return_value=module):
            resolver = NamedQueryResolver("test_queries.test_func").load()
            info = resolver.describe()
            assert info["qualified_name"] == "test_queries.test_func"
            assert info["is_class"] is False
            assert "docstring" in info
            assert "signature" in info
            assert "parameters" in info

    def test_describe_class(self, mock_dialect):
        """Test describing a class."""
        module = types.ModuleType("test_query_classes")
        module.DummyCallable = DummyCallable
        with patch("importlib.import_module", return_value=module):
            resolver = NamedQueryResolver("test_query_classes.DummyCallable").load()
            info = resolver.describe()
            assert info["is_class"] is True

    def test_describe_before_load(self):
        """Test describe before loading fails."""
        resolver = NamedQueryResolver("myapp.queries.func")
        with pytest.raises(NamedQueryNotCallableError):
            resolver.describe()


class TestNamedQueryResolverExecute:
    """Tests for NamedQueryResolver.execute()."""

    def test_execute_returns_non_expression(self, mock_dialect):
        """Test executing returns non-BaseExpression."""

        def bad_func(dialect):
            return "not an expression"

        module = types.ModuleType("test_bad")
        module.bad_func = bad_func

        with patch("importlib.import_module", return_value=module):
            resolver = NamedQueryResolver("test_bad.bad_func").load()
            with pytest.raises(NamedQueryInvalidReturnTypeError):
                resolver.execute(mock_dialect, {})

    def test_execute_before_load(self, mock_dialect):
        """Test execute before loading fails."""
        resolver = NamedQueryResolver("myapp.queries.func")
        with pytest.raises(NamedQueryNotCallableError):
            resolver.execute(mock_dialect, {})


class TestValidateExpression:
    """Tests for validate_expression function."""

    def test_valid_expression(self, mock_expression):
        """Test validating a valid expression."""
        expr = mock_expression()
        stmt_type = validate_expression(expr, "test.query")
        assert stmt_type == StatementType.SELECT

    def test_invalid_expression(self, mock_non_expression):
        """Test validating an invalid expression."""
        with pytest.raises(NamedQueryInvalidReturnTypeError):
            validate_expression(mock_non_expression, "test.query")


class TestListNamedQueriesInModule:
    """Tests for list_named_queries_in_module function."""

    def test_list_module_not_found(self):
        """Test listing from non-existent module."""
        with pytest.raises(NamedQueryModuleNotFoundError):
            list_named_queries_in_module("nonexistent.module")

    def test_list_with_valid_functions(self):
        """Test listing with valid callables."""
        module = types.ModuleType("test_queries")

        def active_users(dialect, limit: int = 100):
            pass

        def users_by_status(dialect, status: str = "active"):
            pass

        module.active_users = active_users
        module.users_by_status = users_by_status

        with patch("importlib.import_module", return_value=module):
            queries = list_named_queries_in_module("test_queries")
            names = [q["name"] for q in queries]
            assert "active_users" in names
            assert "users_by_status" in names

    def test_list_excludes_no_dialect(self):
        """Test that functions without dialect are excluded."""
        module = types.ModuleType("test_queries")

        def with_dialect(dialect, limit: int = 100):
            pass

        def no_dialect(limit: int = 100):
            pass

        module.with_dialect = with_dialect
        module.no_dialect_param = no_dialect

        with patch("importlib.import_module", return_value=module):
            queries = list_named_queries_in_module("test_queries")
            names = [q["name"] for q in queries]
            assert "with_dialect" in names
            assert "no_dialect_param" not in names