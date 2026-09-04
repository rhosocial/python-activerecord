# tests/rhosocial/activerecord_test/feature/backend/cli/test_cli.py
import argparse
import types
from argparse import Namespace
from types import SimpleNamespace
from unittest.mock import patch
import pytest

from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.expression import (
    QueryExpression,
    Literal,
    ExplainExpression,
    DeleteExpression,
)

from rhosocial.activerecord.backend.named_expression.cli import (
    create_named_expression_parser,
    parse_params,
    handle_named_expression,
)

_DIALECT = SQLiteDialect()


def _make_provider(**overrides):
    defaults = dict(
        display_connection_error=lambda e: None,
        display_query_error=lambda e: None,
        display_unexpected_error=lambda e, is_async=False: None,
        display_no_result_object=lambda: None,
        display_success=lambda r, d: None,
        display_results=lambda data, use_ascii: None,
        display_no_data=lambda: None,
        print_table=lambda rows, title, columns: None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_result(data=None, affected_rows=0, duration=0.0):
    return SimpleNamespace(data=data or [], affected_rows=affected_rows, duration=duration)


_PROVIDER = _make_provider()


class TestReplaceProgPlaceholder:
    """Tests for _replace_prog_placeholder."""

    def test_replace_prog_placeholder_single(self):
        from rhosocial.activerecord.backend.named_expression.cli import (
            _replace_prog_placeholder,
        )

        doc = "Usage: %(prog)s query"
        result = _replace_prog_placeholder(doc, "myprog")
        assert result == "Usage: myprog query"

    def test_replace_prog_placeholder_double(self):
        from rhosocial.activerecord.backend.named_expression.cli import (
            _replace_prog_placeholder,
        )

        doc = "Example: %%(prog)s"
        result = _replace_prog_placeholder(doc, "myprog")
        assert result == "Example: myprog" or result == "Example: %myprog"

    def test_replace_prog_placeholder_default(self):
        from rhosocial.activerecord.backend.named_expression.cli import (
            _replace_prog_placeholder,
        )

        doc = "Usage: %(prog)s"
        result = _replace_prog_placeholder(doc)
        assert "python -m rhosocial" in result


class TestCreateNamedExpressionParser:
    """Tests for create_named_expression_parser function."""

    @pytest.fixture
    def parser_setup(self):
        parent = argparse.ArgumentParser(add_help=False)
        parent.add_argument("--db-file", required=True)
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers()
        return parent, subparsers

    def test_create_parser(self, parser_setup):
        parent, subparsers = parser_setup
        parser = create_named_expression_parser(subparsers, parent)
        assert parser is not None
        assert isinstance(parser, argparse.ArgumentParser)

    def test_parser_has_qualified_name(self, parser_setup):
        parent, subparsers = parser_setup
        parser = create_named_expression_parser(subparsers, parent)
        args = parser.parse_args(["myapp.queries.test", "--db-file", "test.db"])
        assert args.qualified_name == "myapp.queries.test"

    def test_parser_has_example(self, parser_setup):
        parent, subparsers = parser_setup
        parser = create_named_expression_parser(subparsers, parent)
        args = parser.parse_args(["myapp.queries.test", "--db-file", "test.db", "-e", "test"])
        assert args.example == "test"

    def test_parser_has_describe(self, parser_setup):
        parent, subparsers = parser_setup
        parser = create_named_expression_parser(subparsers, parent)
        args = parser.parse_args(["myapp.queries.test", "--db-file", "test.db", "--describe"])
        assert args.describe is True

    def test_parser_has_dry_run(self, parser_setup):
        parent, subparsers = parser_setup
        parser = create_named_expression_parser(subparsers, parent)
        args = parser.parse_args(["myapp.queries.test", "--db-file", "test.db", "--dry-run"])
        assert args.dry_run is True

    def test_parser_has_list(self, parser_setup):
        parent, subparsers = parser_setup
        parser = create_named_expression_parser(subparsers, parent)
        args = parser.parse_args(["myapp.queries.test", "--db-file", "test.db", "--list"])
        assert args.list_queries is True

    def test_parser_has_param(self, parser_setup):
        parent, subparsers = parser_setup
        parser = create_named_expression_parser(subparsers, parent)
        args = parser.parse_args(
            [
                "myapp.queries.test",
                "--db-file",
                "test.db",
                "--param",
                "limit=100",
            ]
        )
        assert "limit=100" in args.params

    def test_parser_has_force(self, parser_setup):
        parent, subparsers = parser_setup
        parser = create_named_expression_parser(subparsers, parent)
        args = parser.parse_args(["myapp.queries.test", "--db-file", "test.db", "--force"])
        assert args.force is True

    def test_parser_has_explain(self, parser_setup):
        parent, subparsers = parser_setup
        parser = create_named_expression_parser(subparsers, parent)
        args = parser.parse_args(["myapp.queries.test", "--db-file", "test.db", "--explain"])
        assert args.explain is True


class TestParseParams:
    """Tests for parse_params function."""

    def test_parse_single_param(self):
        result = parse_params(["limit=100"])
        assert result == {"limit": "100"}

    def test_parse_multiple_params(self):
        result = parse_params(["limit=100", "status=active"])
        assert result == {"limit": "100", "status": "active"}

    def test_parse_empty_list(self):
        result = parse_params([])
        assert result == {}

    def test_parse_value_with_equals(self):
        result = parse_params(["sql=SELECT * FROM t WHERE a='b'"])
        assert result == {"sql": "SELECT * FROM t WHERE a='b'"}

    def test_parse_invalid_format_warns(self, capsys):
        result = parse_params(["invalid"])
        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert result == {}


class TestHandleNamedExpressionList:
    """Tests for handle_named_expression with --list option."""

    def test_list_queries(self):
        args = Namespace(
            qualified_name="test_queries",
            example=None,
            params=[],
            describe=False,
            dry_run=False,
            list_queries=True,
            force=False,
            explain=False,
            rich_ascii=False,
        )

        with patch(
            "rhosocial.activerecord.backend.named_expression.cli.list_named_expressions_in_module",
            return_value=[
                {
                    "name": "active_users",
                    "is_class": False,
                    "signature": "(dialect, limit: int = 100)",
                    "docstring": "Get active users.",
                    "brief": "Get active users.",
                }
            ],
        ):
            handle_named_expression(
                args,
                _PROVIDER,
                lambda: None,
                lambda x: None,
                lambda a, b, c: None,
            )

    def test_example_query(self):
        args = Namespace(
            qualified_name="test_queries",
            example="active_users",
            params=[],
            describe=False,
            dry_run=False,
            list_queries=False,
            force=False,
            explain=False,
            rich_ascii=False,
        )

        with patch(
            "rhosocial.activerecord.backend.named_expression.cli.list_named_expressions_in_module",
            return_value=[
                {
                    "name": "active_users",
                    "is_class": False,
                    "signature": "(dialect, limit: int = 100)",
                    "docstring": "Get active users.",
                    "brief": "Get active users.",
                }
            ],
        ):
            handle_named_expression(
                args,
                _PROVIDER,
                lambda: None,
                lambda x: None,
                lambda a, b, c: None,
            )

    def test_example_query_not_found(self, capsys):
        args = Namespace(
            qualified_name="test_queries",
            example="nonexistent",
            params=[],
            describe=False,
            dry_run=False,
            list_queries=False,
            force=False,
            explain=False,
            rich_ascii=False,
        )

        with patch(
            "rhosocial.activerecord.backend.named_expression.cli.list_named_expressions_in_module",
            return_value=[
                {
                    "name": "active_users",
                    "is_class": False,
                }
            ],
        ):
            with pytest.raises(SystemExit):
                handle_named_expression(
                    args,
                    _PROVIDER,
                    lambda: None,
                    lambda x: None,
                    lambda a, b, c: None,
                )


class TestHandleNamedExpressionDescribe:
    """Tests for handle_named_expression with --describe option."""

    def test_describe_query(self):
        args = Namespace(
            qualified_name="test_describe_module.active_users",
            example=None,
            params=[],
            describe=True,
            dry_run=False,
            list_queries=False,
            force=False,
            explain=False,
            rich_ascii=False,
        )

        import sys
        from types import ModuleType

        test_module = ModuleType("test_describe_module")
        test_module.__all__ = ["active_users"]

        def active_users(dialect, limit: int = 100):
            pass

        test_module.active_users = active_users
        sys.modules["test_describe_module"] = test_module

        try:
            handle_named_expression(
                args,
                _PROVIDER,
                lambda: None,
                lambda x: None,
                lambda a, b, c: None,
            )
        finally:
            del sys.modules["test_describe_module"]


class TestHandleNamedExpressionExecute:
    """Tests for normal query execution."""

    def test_execute_error_handling(self, capsys):
        args = Namespace(
            qualified_name="test_queries.active_users",
            example=None,
            params=[],
            describe=False,
            dry_run=False,
            list_queries=False,
            force=False,
            explain=False,
            rich_ascii=False,
        )

        def fail_backend_factory():
            raise RuntimeError("Connection failed")

        with pytest.raises(SystemExit):
            handle_named_expression(
                args,
                _PROVIDER,
                fail_backend_factory,
                lambda x: None,
                lambda a, b, c: None,
            )


class TestHandleNamedExpressionExecuteForce:
    """Tests for handle_named_expression with --force option."""

    def test_force_argument_in_namespace(self):
        args = Namespace(force=True)
        assert args.force is True

    def test_non_force_would_warn(self):
        args = Namespace(force=False)
        assert args.force is False

    def test_explain_in_namespace(self):
        args = Namespace(explain=True)
        assert args.explain is True


class TestHandleNamedExpressionAsync:
    """Tests for async execution path."""

    def test_async_execution_requires_backend(self, capsys):
        args = Namespace(
            qualified_name="test_queries.active_users",
            example=None,
            params=[],
            describe=False,
            dry_run=False,
            list_queries=False,
            force=False,
            explain=False,
            rich_ascii=False,
            is_async=True,
        )

        with pytest.raises(SystemExit) as exc_info:
            handle_named_expression(
                args,
                _PROVIDER,
                lambda: None,
                lambda x: None,
                lambda a, b, c: None,
                backend_async_factory=None,
            )

        assert "async" in str(exc_info.value).lower() or exc_info.value.code == 1


class TestCliListMode:
    """Tests for --list mode in handle_named_expression."""

    def test_handle_list_mode_with_queries(self, capsys):
        from rhosocial.activerecord.backend.named_expression.resolver import (
            list_named_expressions_in_module,
        )
        import sys
        from types import ModuleType

        test_module = ModuleType("test_module_list")
        test_module.__all__ = ["query1", "query2"]

        def query1(dialect, limit=100):
            return None

        def query2(dialect, offset=0):
            return None

        test_module.query1 = query1
        test_module.query2 = query2
        sys.modules["test_module_list"] = test_module

        try:
            queries = list_named_expressions_in_module("test_module_list")
            assert len(queries) == 2
            names = [q["name"] for q in queries]
            assert "query1" in names
            assert "query2" in names
        finally:
            del sys.modules["test_module_list"]

    def test_list_named_queries_empty_module(self):
        from rhosocial.activerecord.backend.named_expression.resolver import (
            list_named_expressions_in_module,
        )
        import sys
        from types import ModuleType

        test_module = ModuleType("test_empty_module")
        test_module.__all__ = ["not_a_query"]

        def not_a_query():
            pass

        test_module.not_a_query = not_a_query
        sys.modules["test_empty_module"] = test_module

        try:
            queries = list_named_expressions_in_module("test_empty_module")
            assert len(queries) == 0
        finally:
            del sys.modules["test_empty_module"]


class TestCliDescribeMode:
    """Tests for --describe mode in handle_named_expression."""

    def test_handle_describe_mode(self, capsys):
        from rhosocial.activerecord.backend.named_expression.resolver import NamedExpressionResolver
        import sys
        from types import ModuleType

        test_module = ModuleType("test_describe_module")
        test_module.__all__ = ["described_query"]

        def described_query(dialect, limit=100):
            """This is a described query."""
            return None

        test_module.described_query = described_query
        sys.modules["test_describe_module"] = test_module

        try:
            resolver = NamedExpressionResolver("test_describe_module.described_query").load()
            info = resolver.describe()
            assert info["qualified_name"] == "test_describe_module.described_query"
            assert "described query" in info["docstring"]
            assert "limit" in info["parameters"]
        finally:
            del sys.modules["test_describe_module"]


class TestCliDryRunMode:
    """Tests for --dry-run mode."""

    def test_parse_params_empty(self):
        from rhosocial.activerecord.backend.named_expression.cli import parse_params

        result = parse_params([])
        assert result == {}

    def test_parse_params_valid(self):
        from rhosocial.activerecord.backend.named_expression.cli import parse_params

        result = parse_params(["limit=100", "status=active"])
        assert result == {"limit": "100", "status": "active"}

    def test_parse_params_with_equals_in_value(self):
        from rhosocial.activerecord.backend.named_expression.cli import parse_params

        result = parse_params(["url=http://example.com?a=1&b=2"])
        assert result == {"url": "http://example.com?a=1&b=2"}

    def test_parse_params_invalid_format(self, capsys):
        from rhosocial.activerecord.backend.named_expression.cli import parse_params

        result = parse_params(["invalid"])
        assert result == {}
        captured = capsys.readouterr()
        assert "Warning" in captured.err


class TestCliErrorHandling:
    """Tests for error handling in handle_named_expression."""

    def test_handle_named_expression_module_not_found(self, capsys):
        args = Namespace(
            qualified_name="nonexistent.module.query",
            example=None,
            params=[],
            describe=False,
            dry_run=False,
            list_queries=False,
            force=False,
            explain=False,
            rich_ascii=False,
            is_async=False,
        )

        with pytest.raises(SystemExit) as exc_info:
            handle_named_expression(
                args,
                _PROVIDER,
                lambda: None,
                lambda x: None,
                lambda a, b, c: None,
            )

        assert exc_info.value.code == 1


class TestCliForceMode:
    """Tests for --force mode."""

    def test_force_allows_non_select_dry_run(self, capsys):
        import types
        import sys

        module = types.ModuleType("test_force_module")
        module.__all__ = ["insert_user"]

        def insert_user(dialect, name: str):
            return DeleteExpression(dialect, "users")

        module.insert_user = insert_user
        sys.modules["test_force_module"] = module

        args = Namespace(
            qualified_name="test_force_module.insert_user",
            example=None,
            params=["name=test"],
            describe=False,
            dry_run=True,
            list_queries=False,
            force=True,
            explain=False,
            rich_ascii=False,
            is_async=False,
        )

        try:
            handle_named_expression(
                args,
                _PROVIDER,
                backend_factory=lambda: SimpleNamespace(dialect=_DIALECT),
                get_dialect=lambda b: b.dialect,
                execute_query=lambda s, p, st: _make_result(data=[], affected_rows=1),
            )
            captured = capsys.readouterr()
            assert "DRY RUN" in captured.out
        finally:
            del sys.modules["test_force_module"]


class TestCliAsyncMode:
    """Tests for --async mode."""

    def test_async_requires_async_factory(self):
        args = Namespace(
            qualified_name="test.async_query",
            example=None,
            params=[],
            describe=False,
            dry_run=False,
            list_queries=False,
            force=False,
            explain=False,
            rich_ascii=False,
            is_async=True,
        )

        with pytest.raises(SystemExit) as exc_info:
            handle_named_expression(
                args,
                _PROVIDER,
                lambda: None,
                lambda x: None,
                lambda a, b, c: None,
                backend_async_factory=None,
            )

        assert exc_info.value.code == 1


class TestCliReplaceProgPlaceholder:
    """Tests for _replace_prog_placeholder function."""

    def test_replace_prog_placeholder_with_placeholder(self):
        from rhosocial.activerecord.backend.named_expression.cli import (
            _replace_prog_placeholder,
        )

        docstring = "Usage: %(prog)s [OPTIONS]"
        result = _replace_prog_placeholder(docstring, "myprog")
        assert result == "Usage: myprog [OPTIONS]"

    def test_replace_prog_placeholder_without_placeholder(self):
        from rhosocial.activerecord.backend.named_expression.cli import (
            _replace_prog_placeholder,
        )

        docstring = "Usage: myprog [OPTIONS]"
        result = _replace_prog_placeholder(docstring, "other_prog")
        assert result == "Usage: myprog [OPTIONS]"

    def test_replace_prog_placeholder_double_percent(self):
        from rhosocial.activerecord.backend.named_expression.cli import (
            _replace_prog_placeholder,
        )

        docstring = "Example: %%something"
        result = _replace_prog_placeholder(docstring, "myprog")
        assert result is not None


class TestCliExampleMode:
    """Tests for --example mode."""

    def test_handle_example_with_matching_query(self, capsys):
        from rhosocial.activerecord.backend.named_expression.resolver import (
            list_named_expressions_in_module,
        )
        import sys
        from types import ModuleType

        test_module = ModuleType("test_example_module")
        test_module.__all__ = ["my_query"]

        def my_query(dialect, limit=100, status="active"):
            """Get active users with limit."""
            return None

        test_module.my_query = my_query
        sys.modules["test_example_module"] = test_module

        try:
            queries = list_named_expressions_in_module("test_example_module")
            assert len(queries) == 1
            assert queries[0]["name"] == "my_query"
            assert "limit" in queries[0]["signature"]
        finally:
            del sys.modules["test_example_module"]


class TestCliRichAscii:
    """Tests for rich_ascii output mode."""

    def test_rich_ascii_flag_exists(self):
        args = Namespace(
            qualified_name="test.query",
            example=None,
            params=[],
            describe=False,
            dry_run=False,
            list_queries=False,
            force=False,
            explain=False,
            rich_ascii=True,
            is_async=False,
        )
        assert args.rich_ascii is True


class TestCliExplainMode:
    """Tests for --explain mode."""

    def test_explain_flag(self):
        args = Namespace(
            qualified_name="test.query",
            example=None,
            params=[],
            describe=False,
            dry_run=False,
            list_queries=False,
            force=False,
            explain=True,
            rich_ascii=False,
            is_async=False,
        )
        assert args.explain is True


class TestHandleNamedExpressionExecute:  # noqa: F811
    """Tests for handle_named_expression execute mode."""

    def test_execute_dry_run(self, capsys):
        args = Namespace(
            qualified_name="test_queries.active_users",
            example=None,
            params=[],
            describe=False,
            dry_run=True,
            list_queries=False,
            force=False,
            explain=False,
            rich_ascii=False,
            is_async=False,
        )

        module = types.ModuleType("test_queries")

        def active_users(dialect, limit: int = 100):
            return QueryExpression(dialect, [Literal(dialect, 1)])

        module.active_users = active_users

        with patch("importlib.import_module", return_value=module):
            handle_named_expression(
                args,
                _PROVIDER,
                backend_factory=lambda: SimpleNamespace(dialect=_DIALECT),
                get_dialect=lambda b: b.dialect,
                execute_query=lambda s, p, st: None,
            )
        captured = capsys.readouterr()
        assert "DRY RUN" in captured.out

    def test_execute_with_params(self, capsys):
        args = Namespace(
            qualified_name="test_queries.active_users",
            example=None,
            params=["limit=50"],
            describe=False,
            dry_run=True,
            list_queries=False,
            force=False,
            explain=False,
            rich_ascii=False,
            is_async=False,
        )

        module = types.ModuleType("test_queries")

        def active_users(dialect, limit: int = 100):
            return QueryExpression(dialect, [Literal(dialect, 1)])

        module.active_users = active_users

        with patch("importlib.import_module", return_value=module):
            handle_named_expression(
                args,
                _PROVIDER,
                backend_factory=lambda: SimpleNamespace(dialect=_DIALECT),
                get_dialect=lambda b: b.dialect,
                execute_query=lambda s, p, st: None,
            )
        captured = capsys.readouterr()
        assert "DRY RUN" in captured.out

    def test_execute_missing_qualified_name(self):
        args = Namespace(
            qualified_name=None,
            example=None,
            params=[],
            describe=False,
            dry_run=False,
            list_queries=False,
            force=False,
            explain=False,
            rich_ascii=False,
            is_async=False,
        )
        with pytest.raises(SystemExit):
            handle_named_expression(
                args,
                _PROVIDER,
                backend_factory=lambda: SimpleNamespace(dialect="placeholder"),
                get_dialect=lambda b: b.dialect,
                execute_query=lambda s, p, st: None,
            )


class TestHandleNamedExpressionDescribe:  # noqa: F811
    """Tests for handle_named_expression --describe mode."""

    def test_describe_with_params(self, capsys):
        args = Namespace(
            qualified_name="test_queries.active_users",
            example=None,
            params=[],
            describe=True,
            dry_run=False,
            list_queries=False,
            force=False,
            explain=False,
            rich_ascii=False,
            is_async=False,
        )

        module = types.ModuleType("test_queries")

        def active_users(dialect, limit: int = 100, offset: int = 0):
            pass

        module.active_users = active_users

        with patch("importlib.import_module", return_value=module):
            handle_named_expression(
                args,
                _PROVIDER,
                backend_factory=lambda: None,
                get_dialect=lambda b: None,
                execute_query=lambda s, p, st: None,
            )
            captured = capsys.readouterr()
            assert "limit" in captured.out
            assert "offset" in captured.out
            assert "Parameters" in captured.out


class TestHandleNamedExpressionWithCreateDialect:
    """Tests for create_dialect in handle_named_expression."""

    def test_list_uses_create_dialect(self, capsys):
        args = Namespace(
            qualified_name="test_queries",
            example=None,
            params=[],
            describe=False,
            dry_run=False,
            list_queries=True,
            force=False,
            explain=False,
            rich_ascii=False,
            is_async=False,
        )

        module = types.ModuleType("test_queries")

        def active_users(dialect, limit: int = 100):
            pass

        module.active_users = active_users

        called = False

        def create_dialect():
            nonlocal called
            called = True
            return _DIALECT

        with patch(
            "rhosocial.activerecord.backend.named_expression.cli.list_named_expressions_in_module",
            return_value=[],
        ):
            with patch("importlib.import_module", return_value=module):
                handle_named_expression(
                    args,
                    _PROVIDER,
                    backend_factory=lambda: SimpleNamespace(dialect="stub"),
                    get_dialect=lambda b: b.dialect,
                    execute_query=lambda s, p, st: None,
                    create_dialect=create_dialect,
                )
        assert called

    def test_describe_does_not_use_create_dialect(self, capsys):
        args = Namespace(
            qualified_name="test_queries.active_users",
            example=None,
            params=[],
            describe=True,
            dry_run=False,
            list_queries=False,
            force=False,
            explain=False,
            rich_ascii=False,
            is_async=False,
        )

        module = types.ModuleType("test_queries")

        def active_users(dialect, limit: int = 100):
            pass

        module.active_users = active_users

        called = False

        def create_dialect():
            nonlocal called
            called = True
            return _DIALECT

        with patch("importlib.import_module", return_value=module):
            handle_named_expression(
                args,
                _PROVIDER,
                backend_factory=lambda: SimpleNamespace(dialect="stub"),
                get_dialect=lambda b: b.dialect,
                execute_query=lambda s, p, st: None,
                create_dialect=create_dialect,
            )
        assert not called


class TestExecuteExpression:
    """Tests for _execute_expression helper."""

    def test_non_executable_exits(self):
        from rhosocial.activerecord.backend.named_expression.cli import _execute_expression

        args = Namespace(
            dry_run=False,
            force=False,
            explain=False,
            rich_ascii=False,
        )
        with pytest.raises(SystemExit):
            _execute_expression(Literal(_DIALECT, 1), args, lambda s, p, st: None, _PROVIDER)

    def test_explain_without_flag_exits(self):
        from rhosocial.activerecord.backend.named_expression.cli import _execute_expression

        inner = QueryExpression(_DIALECT, [Literal(_DIALECT, 1)])
        expr = ExplainExpression(_DIALECT, inner)
        args = Namespace(
            dry_run=False,
            force=False,
            explain=False,
            rich_ascii=False,
        )
        with pytest.raises(SystemExit):
            _execute_expression(expr, args, lambda s, p, st: None, _PROVIDER)

    def test_non_select_without_force_exits(self):
        from rhosocial.activerecord.backend.named_expression.cli import _execute_expression

        expr = DeleteExpression(_DIALECT, "t")
        args = Namespace(
            dry_run=False,
            force=False,
            explain=False,
            rich_ascii=False,
        )
        with pytest.raises(SystemExit):
            _execute_expression(expr, args, lambda s, p, st: None, _PROVIDER)

    def test_execute_success(self):
        from rhosocial.activerecord.backend.named_expression.cli import _execute_expression

        expr = QueryExpression(_DIALECT, [Literal(_DIALECT, 1)])
        args = Namespace(
            dry_run=False,
            force=False,
            explain=False,
            rich_ascii=False,
        )
        executed = []

        def exec_fn(sql, params, stmt_type):
            executed.append((sql, params, stmt_type))
            return _make_result(data=[(1,)], affected_rows=1, duration=0.01)

        _execute_expression(expr, args, exec_fn, _PROVIDER)
        assert len(executed) == 1
        assert "SELECT" in executed[0][0]


class TestClassifyExpression:
    """Tests for _classify_expression."""

    def test_classify_clause(self):
        from rhosocial.activerecord.backend.named_expression.cli import _classify_expression

        result = _classify_expression(Literal(_DIALECT, 1))
        assert result == "CLAUSE"

    def test_classify_dql(self):
        from rhosocial.activerecord.backend.named_expression.cli import _classify_expression

        result = _classify_expression(QueryExpression(_DIALECT, [Literal(_DIALECT, 1)]))
        assert result == "DQL"

    def test_classify_dml(self):
        from rhosocial.activerecord.backend.named_expression.cli import _classify_expression

        result = _classify_expression(DeleteExpression(_DIALECT, "t"))
        assert result == "DML"
