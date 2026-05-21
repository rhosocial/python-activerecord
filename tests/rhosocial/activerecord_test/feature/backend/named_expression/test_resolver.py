# tests/rhosocial/activerecord_test/feature/backend/named_expression/test_resolver.py
"""
Tests for named expression resolver.

This test module covers:
- NamedExpressionResolver class
- resolve_named_expression function
- list_named_expressions_in_module function
"""
import types
from typing import List
from unittest.mock import MagicMock, patch
import pytest
from rhosocial.activerecord.backend.named_expression.resolver import (
    NamedExpressionResolver,
    list_named_expressions_in_module,
)
from rhosocial.activerecord.backend.named_expression.exceptions import (
    NamedExpressionNotFoundError,
    NamedExpressionModuleNotFoundError,
    NamedExpressionInvalidReturnTypeError,
    NamedExpressionNotCallableError,
)



class DummyCallable:
    """Dummy callable for testing."""

    def __call__(self, dialect, limit: int = 100):
        return MagicMock()


class TestNamedExpressionResolverInit:
    """Tests for NamedExpressionResolver.__init__."""

    def test_valid_qualified_name(self):
        """Test initialization with valid qualified name."""
        resolver = NamedExpressionResolver("myapp.queries.user_active")
        assert resolver.qualified_name == "myapp.queries.user_active"

    def test_invalid_qualified_name_no_dot(self):
        """Test initialization fails without dot."""
        with pytest.raises(NamedExpressionNotFoundError) as exc:
            NamedExpressionResolver("nodot")
        assert "must be in the format" in str(exc.value)

    def test_valid_qualified_name_nested_module(self):
        """Test initialization with nested module (3 parts)."""
        resolver = NamedExpressionResolver("my.app.queries.user_active")
        assert resolver.qualified_name == "my.app.queries.user_active"

    def test_empty_qualified_name(self):
        """Test initialization fails with empty name."""
        with pytest.raises(NamedExpressionNotFoundError):
            NamedExpressionResolver("")


class TestNamedExpressionResolverLoad:
    """Tests for NamedExpressionResolver.load()."""

    def test_load_function_success(self, mock_dialect):
        """Test loading a function successfully."""
        module = types.ModuleType("test_queries")

        def test_func(dialect, limit: int = 100):
            pass

        module.test_func = test_func
        with patch("importlib.import_module", return_value=module):
            resolver = NamedExpressionResolver("test_queries.test_func").load()
            assert resolver._callable is not None
            assert resolver._target_callable is not None

    def test_load_class_success(self, mock_dialect):
        """Test loading a class successfully."""
        module = types.ModuleType("test_query_classes")
        module.DummyCallable = DummyCallable
        with patch("importlib.import_module", return_value=module):
            resolver = NamedExpressionResolver("test_query_classes.DummyCallable").load()
            assert resolver._is_class is True
            assert resolver._instance is not None

    def test_load_module_not_found(self):
        """Test loading fails when module doesn't exist."""
        with pytest.raises(NamedExpressionModuleNotFoundError):
            NamedExpressionResolver("nonexistent.module.func").load()

    def test_load_attribute_not_found(self):
        """Test loading fails when attribute doesn't exist."""
        module = types.ModuleType("test_queries")
        module.__all__ = []
        with patch("importlib.import_module", return_value=module):
            with pytest.raises(NamedExpressionNotFoundError) as exc:
                NamedExpressionResolver("test_queries.nonexistent").load()
            assert "not found" in str(exc.value)

    def test_load_not_callable(self):
        """Test loading fails when attribute is not callable."""
        module = types.ModuleType("test_non_callable")
        module.not_callable = "just a string"

        with patch("importlib.import_module", return_value=module):
            with pytest.raises(NamedExpressionNotCallableError):
                NamedExpressionResolver("test_non_callable.not_callable").load()


class TestNamedExpressionResolverSignature:
    """Tests for NamedExpressionResolver.get_signature()."""

    def test_get_signature_after_load(self, mock_dialect):
        """Test getting signature after loading."""
        module = types.ModuleType("test_queries")

        def test_func(dialect, limit: int = 100):
            pass

        module.test_func = test_func
        with patch("importlib.import_module", return_value=module):
            resolver = NamedExpressionResolver("test_queries.test_func").load()
            sig = resolver.get_signature()
            assert "limit" in sig.parameters

    def test_get_signature_before_load(self):
        """Test getting signature before loading fails."""
        resolver = NamedExpressionResolver("myapp.queries.func")
        with pytest.raises(NamedExpressionNotCallableError):
            resolver.get_signature()


class TestNamedExpressionResolverUserParams:
    """Tests for NamedExpressionResolver.get_user_params()."""

    def test_get_user_params_function(self, mock_dialect):
        """Test getting user params for a function."""
        module = types.ModuleType("test_queries")

        def test_func(dialect, limit: int = 100):
            pass

        module.test_func = test_func
        with patch("importlib.import_module", return_value=module):
            resolver = NamedExpressionResolver("test_queries.test_func").load()
            params = resolver.get_user_params()
            assert "limit" in params

    def test_get_user_params_excludes_dialect(self, mock_dialect):
        """Test that dialect is excluded from user params."""
        module = types.ModuleType("test_queries")

        def test_func(dialect, limit: int = 100):
            pass

        module.test_func = test_func
        with patch("importlib.import_module", return_value=module):
            resolver = NamedExpressionResolver("test_queries.test_func").load()
            params = resolver.get_user_params()
            assert "dialect" not in params


class TestNamedExpressionResolverDescribe:
    """Tests for NamedExpressionResolver.describe()."""

    def test_describe_function(self, mock_dialect):
        """Test describing a function."""
        module = types.ModuleType("test_queries")

        def test_func(dialect, limit: int = 100):
            """Test function docstring."""

        module.test_func = test_func
        with patch("importlib.import_module", return_value=module):
            resolver = NamedExpressionResolver("test_queries.test_func").load()
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
            resolver = NamedExpressionResolver("test_query_classes.DummyCallable").load()
            info = resolver.describe()
            assert info["is_class"] is True

    def test_describe_before_load(self):
        """Test describe before loading fails."""
        resolver = NamedExpressionResolver("myapp.queries.func")
        with pytest.raises(NamedExpressionNotCallableError):
            resolver.describe()


class TestNamedExpressionResolverExecute:
    """Tests for NamedExpressionResolver.execute()."""

    def test_execute_returns_non_expression(self, mock_dialect):
        """Test executing returns non-BaseExpression."""

        def bad_func(dialect):
            return "not an expression"

        module = types.ModuleType("test_bad")
        module.bad_func = bad_func

        with patch("importlib.import_module", return_value=module):
            resolver = NamedExpressionResolver("test_bad.bad_func").load()
            with pytest.raises(NamedExpressionInvalidReturnTypeError):
                resolver.execute(mock_dialect, {})

    def test_execute_before_load(self, mock_dialect):
        """Test execute before loading fails."""
        resolver = NamedExpressionResolver("myapp.queries.func")
        with pytest.raises(NamedExpressionNotCallableError):
            resolver.execute(mock_dialect, {})


class TestListNamedExpressionsInModule:
    """Tests for list_named_expressions_in_module function."""

    def test_list_module_not_found(self):
        """Test listing from non-existent module."""
        with pytest.raises(NamedExpressionModuleNotFoundError):
            list_named_expressions_in_module("nonexistent.module")

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
            queries = list_named_expressions_in_module("test_queries")
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
            queries = list_named_expressions_in_module("test_queries")
            names = [q["name"] for q in queries]
            assert "with_dialect" in names
            assert "no_dialect_param" not in names