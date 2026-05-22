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
from rhosocial.activerecord.backend.expression.bases import BaseExpression

from rhosocial.activerecord.backend.named_expression.exceptions import (
    NamedExpressionNotFoundError,
    NamedExpressionModuleNotFoundError,
    NamedExpressionInvalidReturnTypeError,
    NamedExpressionNotCallableError,
    NamedExpressionMissingParameterError,
    NamedExpressionInvalidParameterError,
)


class DummyCallable:
    """Dummy callable for testing."""

    def __call__(self, dialect, limit: int = 100):
        from rhosocial.activerecord.backend.expression import QueryExpression
        return QueryExpression(dialect)


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

    def test_execute_non_expression_class(self, mock_dialect):
        """Test class execute returns non-BaseExpression."""
        def bad_class_func(dialect):
            return "not an expression"

        module = types.ModuleType("test_bad")
        module.bad_class_func = bad_class_func

        with patch("importlib.import_module", return_value=module):
            resolver = NamedExpressionResolver("test_bad.bad_class_func").load()
            with pytest.raises(NamedExpressionInvalidReturnTypeError):
                resolver.execute(mock_dialect, {})

    def test_execute_extra_params(self, mock_dialect):
        from rhosocial.activerecord.backend.expression import QueryExpression
        module = types.ModuleType("test_queries")
        def func(dialect, limit: int = 100):
            return QueryExpression(dialect)
        module.func = func
        with patch("importlib.import_module", return_value=module):
            resolver = NamedExpressionResolver("test_queries.func").load()
            with pytest.raises(NamedExpressionInvalidParameterError):
                resolver.execute(mock_dialect, {"unknown_param": "value"})

    def test_execute_missing_required_param(self, mock_dialect):
        module = types.ModuleType("test_queries")
        def func(dialect, limit): pass
        module.func = func
        with patch("importlib.import_module", return_value=module):
            resolver = NamedExpressionResolver("test_queries.func").load()
            with pytest.raises(NamedExpressionMissingParameterError):
                resolver.execute(mock_dialect, {})


class TestNamedExpressionResolverIsClass:
    """Tests for NamedExpressionResolver.is_class."""

    def test_is_class_property_function(self, mock_dialect):
        module = types.ModuleType("test_queries")
        def func(dialect): pass
        module.func = func
        with patch("importlib.import_module", return_value=module):
            resolver = NamedExpressionResolver("test_queries.func").load()
            assert resolver.is_class is False

    def test_is_class_property_before_load(self):
        resolver = NamedExpressionResolver("myapp.queries.func")
        with pytest.raises(NamedExpressionNotCallableError):
            _ = resolver.is_class


class TestNamedExpressionResolverGetParamSpecs:
    """Tests for NamedExpressionResolver.get_param_specs()."""

    def test_get_param_specs_all_scalar(self, mock_dialect):
        module = types.ModuleType("test_queries")
        def func(dialect, limit: int = 100, offset: int = 0): pass
        module.func = func
        with patch("importlib.import_module", return_value=module):
            resolver = NamedExpressionResolver("test_queries.func").load()
            specs = resolver.get_param_specs()
            assert len(specs) == 2
            assert specs[0]["name"] == "limit"
            assert specs[0]["kind"] == "scalar"
            assert specs[0]["annotated"] is True
            assert specs[0]["has_default"] is True
            assert specs[1]["name"] == "offset"

    def test_get_param_specs_untyped(self, mock_dialect):
        module = types.ModuleType("test_queries")
        def func(dialect, limit=100): pass
        module.func = func
        with patch("importlib.import_module", return_value=module):
            resolver = NamedExpressionResolver("test_queries.func").load()
            specs = resolver.get_param_specs()
            assert specs[0]["annotated"] is False
            assert specs[0]["annotation"] == "<untyped>"


class TestResolveNamedExpression:
    """Tests for resolve_named_expression convenience function."""

    def test_resolve_success(self, mock_dialect):
        from rhosocial.activerecord.backend.named_expression.resolver import resolve_named_expression
        module = types.ModuleType("test_queries")
        def func(dialect, limit: int = 100):
            return None
        module.func = func
        with patch("importlib.import_module", return_value=module):
            try:
                resolve_named_expression("test_queries.func", mock_dialect)
            except NamedExpressionInvalidReturnTypeError:
                pass

    def test_resolve_module_not_found(self):
        from rhosocial.activerecord.backend.named_expression.resolver import resolve_named_expression
        with pytest.raises(NamedExpressionModuleNotFoundError):
            resolve_named_expression("nonexistent.module.func", None)


class TestClassifyProbeUtilities:
    """Tests for internal _classify and _probe_tags utilities."""

    def _dialect(self):
        from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
        return SQLiteDialect()

    def test_classify_clause(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _classify
        from rhosocial.activerecord.backend.expression import RawSQLExpression
        result = _classify(RawSQLExpression(self._dialect(), "SELECT 1"))
        assert result == ["CLAUSE"]

    def test_classify_dql(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _classify
        from rhosocial.activerecord.backend.expression import QueryExpression, Literal
        d = self._dialect()
        q = QueryExpression(d, [Literal(d, 1)])
        result = _classify(q)
        assert result == ["DQL"]

    def test_classify_dml(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _classify
        from rhosocial.activerecord.backend.expression import InsertExpression
        d = self._dialect()
        expr = InsertExpression(d, "t", [Literal(d, 1)])
        result = _classify(expr)
        assert result == ["DML"]

    def test_classify_ddl(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _classify
        from rhosocial.activerecord.backend.expression import CreateTableExpression
        d = self._dialect()
        expr = CreateTableExpression(d, "t")
        result = _classify(expr)
        assert result == ["DDL"]

    def test_classify_tcl(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _classify
        from rhosocial.activerecord.backend.expression import BeginTransactionExpression
        d = self._dialect()
        expr = BeginTransactionExpression(d)
        result = _classify(expr)
        assert result == ["TCL"]

    def test_classify_call(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _classify
        from rhosocial.activerecord.backend.expression import FunctionCall
        d = self._dialect()
        expr = FunctionCall(d, "foo")
        result = _classify(expr)
        assert result == ["CALL"]

    def test_classify_explain(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _classify
        from rhosocial.activerecord.backend.expression import ExplainExpression
        d = self._dialect()
        from rhosocial.activerecord.backend.expression import QueryExpression, Literal
        inner = QueryExpression(d, [Literal(d, 1)])
        expr = ExplainExpression(d, inner)
        result = _classify(expr)
        assert result == ["EXPLAIN"]

    def test_classify_unknown(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _classify
        from rhosocial.activerecord.backend.schema import StatementType
        from rhosocial.activerecord.backend.expression import SQLValueExpression
        d = self._dialect()
        with patch.object(SQLValueExpression(d, 1), 'statement_type', StatementType.OTHER):
            pass

    def test_probe_tags_no_dialect(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _probe_tags
        def f(dialect, x: int = 1): pass
        result = _probe_tags(f, dialect=None)
        assert result == ["?"]

    def test_probe_tags_unresolvable_signature(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _probe_tags
        class NoSig: pass
        result = _probe_tags(NoSig())
        assert result == ["?"]

    def test_probe_tags_required_param_no_dialect(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _probe_tags
        def f(dialect, x): pass
        result = _probe_tags(f, dialect=MagicMock())
        assert result == ["?"]

    def test_probe_tags_callable_raises(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _probe_tags
        def f(dialect, x: int = 1): raise RuntimeError
        result = _probe_tags(f, dialect=MagicMock())
        assert result == ["?"]

    def test_probe_tags_returns_non_expression(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _probe_tags
        def f(dialect, x: int = 1): return "not expression"
        result = _probe_tags(f, dialect=MagicMock())
        assert result == ["?"]

    def test_probe_tags_success(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _probe_tags
        from rhosocial.activerecord.backend.expression import QueryExpression, Literal

        def f(dialect, x: int = 1):
            return QueryExpression(dialect, [Literal(dialect, 1)])
        result = _probe_tags(f, dialect=self._dialect())
        assert result == ["DQL"]

    def test_probe_tags_returns_clause(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _probe_tags
        from rhosocial.activerecord.backend.expression import RawSQLExpression

        def f(dialect, x: int = 1):
            return RawSQLExpression(dialect, "1")
        result = _probe_tags(f, dialect=self._dialect())
        assert result == ["CLAUSE"]

    def test_classify_dql(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _classify
        from rhosocial.activerecord.backend.schema import StatementType
        exec_mock = MagicMock()
        exec_mock.statement_type = StatementType.SELECT
        result = _classify(exec_mock)
        assert result == ["DQL"]

    def test_classify_dml(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _classify
        from rhosocial.activerecord.backend.schema import StatementType
        exec_mock = MagicMock()
        exec_mock.statement_type = StatementType.INSERT
        result = _classify(exec_mock)
        assert result == ["DML"]

    def test_classify_ddl(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _classify
        from rhosocial.activerecord.backend.schema import StatementType
        exec_mock = MagicMock()
        exec_mock.statement_type = StatementType.DDL
        result = _classify(exec_mock)
        assert result == ["DDL"]

    def test_classify_tcl(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _classify
        from rhosocial.activerecord.backend.schema import StatementType
        exec_mock = MagicMock()
        exec_mock.statement_type = StatementType.TCL
        result = _classify(exec_mock)
        assert result == ["TCL"]

    def test_classify_call(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _classify
        from rhosocial.activerecord.backend.schema import StatementType
        exec_mock = MagicMock()
        exec_mock.statement_type = StatementType.CALL
        result = _classify(exec_mock)
        assert result == ["CALL"]

    def test_classify_explain(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _classify
        from rhosocial.activerecord.backend.schema import StatementType
        exec_mock = MagicMock()
        exec_mock.statement_type = StatementType.EXPLAIN
        result = _classify(exec_mock)
        assert result == ["EXPLAIN"]

    def test_classify_unknown(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _classify
        from rhosocial.activerecord.backend.schema import StatementType
        exec_mock = MagicMock()
        exec_mock.statement_type = StatementType.OTHER
        result = _classify(exec_mock)
        assert result == ["OTHER"]

    def test_probe_tags_no_dialect(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _probe_tags
        def f(dialect, x: int = 1): pass
        result = _probe_tags(f, dialect=None)
        assert result == ["?"]

    def test_probe_tags_unresolvable_signature(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _probe_tags
        class NoSig: pass
        result = _probe_tags(NoSig())
        assert result == ["?"]

    def test_probe_tags_required_param_no_dialect(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _probe_tags
        def f(dialect, x): pass
        result = _probe_tags(f, dialect=MagicMock())
        assert result == ["?"]

    def test_probe_tags_callable_raises(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _probe_tags
        def f(dialect, x: int = 1): raise RuntimeError
        result = _probe_tags(f, dialect=MagicMock())
        assert result == ["?"]

    def test_probe_tags_returns_non_expression(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _probe_tags
        def f(dialect, x: int = 1): return "not expression"
        result = _probe_tags(f, dialect=MagicMock())
        assert result == ["?"]

    def test_resolve_annotation_string(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _resolve_annotation
        ns = {"int": int}
        result = _resolve_annotation("int", ns)
        assert result is int

    def test_resolve_annotation_already_type(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _resolve_annotation
        result = _resolve_annotation(str, {})
        assert result is str

    def test_resolve_annotation_bad_string(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _resolve_annotation
        result = _resolve_annotation("NonExistentType", {})
        assert result == "NonExistentType"

    def test_probe_tags_success(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _probe_tags
        from rhosocial.activerecord.backend.schema import StatementType
        from rhosocial.activerecord.backend.expression.bases import BaseExpression

        mock_expr = MagicMock(spec=BaseExpression)
        mock_expr.statement_type = StatementType.SELECT

        def f(dialect, x: int = 1):
            return mock_expr
        result = _probe_tags(f, dialect=MagicMock())
        assert result == ["DQL"]

    def test_probe_tags_returns_clause(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _probe_tags
        from rhosocial.activerecord.backend.expression import RawSQLExpression

        def f(dialect, x: int = 1):
            return RawSQLExpression(dialect, "1")
        result = _probe_tags(f, dialect=MagicMock())
        assert result == ["CLAUSE"]

    def test_classify_param_expression_type(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _classify_param
        import inspect
        from rhosocial.activerecord.backend.expression.bases import BaseExpression
        ns = {"BaseExpression": BaseExpression}
        param = inspect.Parameter(
            "expr", inspect.Parameter.POSITIONAL_OR_KEYWORD,
            annotation="BaseExpression"
        )
        kind, annotated = _classify_param(param, ns)
        assert kind == "expression"
        assert annotated is True

    def test_ann_str_empty(self):
        from rhosocial.activerecord.backend.named_expression.resolver import _ann_str
        import inspect
        param = inspect.Parameter("x", inspect.Parameter.POSITIONAL_OR_KEYWORD)
        result = _ann_str(param)
        assert result == "<untyped>"


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

    def test_list_with_dialect_probing(self):
        """Test listing with dialect for tag probing."""
        from unittest.mock import MagicMock
        module = types.ModuleType("test_queries")

        def active_users(dialect, limit: int = 100):
            return MagicMock()

        module.active_users = active_users

        dialect = MagicMock()
        with patch("importlib.import_module", return_value=module):
            queries = list_named_expressions_in_module("test_queries", dialect)
            assert len(queries) >= 1
            assert "tags" in queries[0]

    def test_list_with_class(self):
        """Test listing with class-based callables."""
        module = types.ModuleType("test_classes")

        class QueryClass:
            def __call__(self, dialect, status: str = "active"):
                pass

        module.QueryClass = QueryClass

        with patch("importlib.import_module", return_value=module):
            queries = list_named_expressions_in_module("test_classes")
            names = [q["name"] for q in queries]
            assert "QueryClass" in names
            assert queries[0]["is_class"] is True
            assert "tags" in queries[0]

    def test_list_class_without_dialect(self):
        """Test class without dialect param is excluded."""
        module = types.ModuleType("test_classes")

        class NoDialectClass:
            def __call__(self, limit: int = 100):
                pass

        module.NoDialectClass = NoDialectClass

        with patch("importlib.import_module", return_value=module):
            queries = list_named_expressions_in_module("test_classes")
            assert len(queries) == 0

    def test_list_class_init_fails(self):
        """Test class that raises during __init__ is skipped."""
        module = types.ModuleType("test_classes")

        class BrokenClass:
            def __init__(self):
                raise RuntimeError("init failed")

            def __call__(self, dialect, x: int = 1):
                pass

        module.BrokenClass = BrokenClass

        with patch("importlib.import_module", return_value=module):
            queries = list_named_expressions_in_module("test_classes")
            assert len(queries) == 0

    def test_list_skips_underscore_prefix(self):
        """Test that _prefixed names are skipped."""
        module = types.ModuleType("test_queries")

        def _internal(dialect, x: int = 1):
            pass

        module._internal = _internal

        with patch("importlib.import_module", return_value=module):
            queries = list_named_expressions_in_module("test_queries")
            assert len(queries) == 0

    def test_list_skips_non_callable_none(self):
        """Test that None-valued attributes are skipped."""
        module = types.ModuleType("test_queries")
        module.something = None

        with patch("importlib.import_module", return_value=module):
            queries = list_named_expressions_in_module("test_queries")
            assert len(queries) == 0

    def test_list_class_with_method_docstring(self):
        """Test class whose __call__ has docstring but class doesn't."""
        module = types.ModuleType("test_queries")

        class DocClass:
            def __call__(self, dialect, x: int = 1):
                """Method docstring."""
                pass

        module.DocClass = DocClass

        with patch("importlib.import_module", return_value=module):
            queries = list_named_expressions_in_module("test_queries")
            assert len(queries) == 1
            assert queries[0]["brief"] == "Method docstring."

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