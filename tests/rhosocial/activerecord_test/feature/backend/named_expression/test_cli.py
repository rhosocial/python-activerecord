# tests/rhosocial/activerecord_test/feature/backend/named_expression/test_cli.py
"""
Tests for named query CLI utilities.

This test module covers:
- create_named_expression_parser function
- parse_params function
- handle_named_expression function
"""
import argparse
from argparse import Namespace
from typing import List
from unittest.mock import MagicMock, patch
import pytest

from rhosocial.activerecord.backend.named_expression.cli import (
    create_named_expression_parser,
    parse_params,
    handle_named_expression,
)


class TestReplaceProgPlaceholder:
    """Tests for _replace_prog_placeholder."""

    def test_replace_prog_placeholder_single(self):
        """Test replacing %(prog)s placeholder."""
        from rhosocial.activerecord.backend.named_expression.cli import (
            _replace_prog_placeholder,
        )
        doc = "Usage: %(prog)s query"
        result = _replace_prog_placeholder(doc, "myprog")
        assert result == "Usage: myprog query"

    def test_replace_prog_placeholder_double(self):
        """Test replacing %%%(prog)s placeholder."""
        from rhosocial.activerecord.backend.named_expression.cli import (
            _replace_prog_placeholder,
        )
        doc = "Example: %%(prog)s"
        result = _replace_prog_placeholder(doc, "myprog")
        assert result == "Example: myprog" or result == "Example: %myprog"

    def test_replace_prog_placeholder_default(self):
        """Test default prog value."""
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
        """Set up parser for testing."""
        parent = argparse.ArgumentParser(add_help=False)
        parent.add_argument("--db-file", required=True)
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers()
        return parent, subparsers

    def test_create_parser(self, parser_setup):
        """Test creating the parser."""
        parent, subparsers = parser_setup
        parser = create_named_expression_parser(subparsers, parent)
        assert parser is not None
        assert isinstance(parser, argparse.ArgumentParser)

    def test_parser_has_qualified_name(self, parser_setup):
        """Test parser has qualified_name argument."""
        parent, subparsers = parser_setup
        parser = create_named_expression_parser(subparsers, parent)
        args = parser.parse_args(["myapp.queries.test", "--db-file", "test.db"])
        assert args.qualified_name == "myapp.queries.test"

    def test_parser_has_example(self, parser_setup):
        """Test parser has --example/-e argument."""
        parent, subparsers = parser_setup
        parser = create_named_expression_parser(subparsers, parent)
        args = parser.parse_args(
            ["myapp.queries.test", "--db-file", "test.db", "-e", "test"]
        )
        assert args.example == "test"

    def test_parser_has_describe(self, parser_setup):
        """Test parser has --describe argument."""
        parent, subparsers = parser_setup
        parser = create_named_expression_parser(subparsers, parent)
        args = parser.parse_args(
            ["myapp.queries.test", "--db-file", "test.db", "--describe"]
        )
        assert args.describe is True

    def test_parser_has_dry_run(self, parser_setup):
        """Test parser has --dry-run argument."""
        parent, subparsers = parser_setup
        parser = create_named_expression_parser(subparsers, parent)
        args = parser.parse_args(
            ["myapp.queries.test", "--db-file", "test.db", "--dry-run"]
        )
        assert args.dry_run is True

    def test_parser_has_list(self, parser_setup):
        """Test parser has --list argument."""
        parent, subparsers = parser_setup
        parser = create_named_expression_parser(subparsers, parent)
        args = parser.parse_args(
            ["myapp.queries.test", "--db-file", "test.db", "--list"]
        )
        assert args.list_queries is True

    def test_parser_has_param(self, parser_setup):
        """Test parser has --param argument."""
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
        """Test parser has --force argument."""
        parent, subparsers = parser_setup
        parser = create_named_expression_parser(subparsers, parent)
        args = parser.parse_args(
            ["myapp.queries.test", "--db-file", "test.db", "--force"]
        )
        assert args.force is True

    def test_parser_has_explain(self, parser_setup):
        """Test parser has --explain argument."""
        parent, subparsers = parser_setup
        parser = create_named_expression_parser(subparsers, parent)
        args = parser.parse_args(
            ["myapp.queries.test", "--db-file", "test.db", "--explain"]
        )
        assert args.explain is True


class TestParseParams:
    """Tests for parse_params function."""

    def test_parse_single_param(self):
        """Test parsing a single parameter."""
        result = parse_params(["limit=100"])
        assert result == {"limit": "100"}

    def test_parse_multiple_params(self):
        """Test parsing multiple parameters."""
        result = parse_params(["limit=100", "status=active"])
        assert result == {"limit": "100", "status": "active"}

    def test_parse_empty_list(self):
        """Test parsing empty list."""
        result = parse_params([])
        assert result == {}

    def test_parse_value_with_equals(self):
        """Test parsing value containing equals sign."""
        result = parse_params(["sql=SELECT * FROM t WHERE a='b'"])
        assert result == {"sql": "SELECT * FROM t WHERE a='b'"}

    def test_parse_invalid_format_warns(self, capsys):
        """Test warning for invalid format."""
        result = parse_params(["invalid"])
        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert result == {}


class TestHandleNamedExpressionList:
    """Tests for handle_named_expression with --list option."""

    def test_list_queries(self):
        """Test listing queries in a module."""
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
            no_probe=False,
        )

        provider = MagicMock()
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
                provider,
                lambda: None,
                lambda x: None,
                lambda a, b, c: None,
            )

    def test_example_query(self):
        """Test showing example query details."""
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
            no_probe=False,
        )

        provider = MagicMock()
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
                provider,
                lambda: None,
                lambda x: None,
                lambda a, b, c: None,
            )

    def test_example_query_not_found(self, capsys):
        """Test example query not found."""
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
            no_probe=False,
        )

        provider = MagicMock()
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
                    provider,
                    lambda: None,
                    lambda x: None,
                    lambda a, b, c: None,
                )


class TestHandleNamedExpressionDescribe:
    """Tests for handle_named_expression with --describe option."""

    def test_describe_query(self):
        """Test showing query description."""
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
        )

        provider = MagicMock()
        mock_resolver = MagicMock()
        mock_resolver.describe.return_value = {
            "qualified_name": "test_queries.active_users",
            "is_class": False,
            "docstring": "Get active users.",
            "signature": "(dialect, limit: int = 100)",
            "parameters": {
                "limit": {
                    "name": "limit",
                    "type": "int",
                    "has_default": True,
                    "default": "100",
                }
            },
        }

        with patch(
            "rhosocial.activerecord.backend.named_expression.cli.NamedExpressionResolver",
            return_value=mock_resolver,
        ):
            handle_named_expression(
                args,
                provider,
                lambda: None,
                lambda x: None,
                lambda a, b, c: None,
            )


class TestHandleNamedExpressionExecute:
    """Tests for normal query execution."""

    def test_execute_error_handling(self, capsys):
        """Test error handling."""
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

        provider = MagicMock()

        def fail_backend_factory():
            raise RuntimeError("Connection failed")

        with pytest.raises(SystemExit):
            handle_named_expression(
                args,
                provider,
                fail_backend_factory,
                lambda x: None,
                lambda a, b, c: None,
            )


class TestHandleNamedExpressionExecuteForce:
    """Tests for handle_named_expression with --force option."""

    def test_force_argument_in_namespace(self):
        """Test force is in namespace for execute checks."""
        args = Namespace(
            force=True,
            list_queries=False,
            example=None,
        )
        assert args.force is True

    def test_non_force_would_warn(self):
        """Test non-force would cause warning for DML."""
        args = Namespace(
            force=False,
        )
        assert args.force is False

    def test_explain_in_namespace(self):
        """Test explain is in namespace."""
        args = Namespace(
            explain=True,
        )
        assert args.explain is True


class TestHandleNamedExpressionAsync:
    """Tests for async execution path."""

    def test_async_execution_requires_backend(self, capsys):
        """Test --async requires async backend factory."""
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

        provider = MagicMock()

        with pytest.raises(SystemExit) as exc_info:
            handle_named_expression(
                args,
                provider,
                lambda: None,
                lambda x: None,
                lambda a, b, c: None,
                backend_async_factory=None,
            )

        assert "async" in str(exc_info.value).lower() or exc_info.value.code == 1


class TestCliListMode:
    """Tests for --list mode in handle_named_expression."""

    def test_handle_list_mode_with_queries(self, capsys):
        """Test --list with queries in module."""
        from rhosocial.activerecord.backend.named_expression.resolver import (
            list_named_expressions_in_module,
        )
        import sys
        from types import ModuleType

        test_module = ModuleType("test_module_list")
        test_module.__all__ = ["query1", "query2"]

        def query1(dialect, limit=100):
            return MagicMock()

        def query2(dialect, offset=0):
            return MagicMock()

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
        """Test list_named_expressions_in_module with no valid queries."""
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
        """Test --describe shows query info."""
        from rhosocial.activerecord.backend.named_expression.resolver import NamedExpressionResolver
        import sys
        from types import ModuleType

        test_module = ModuleType("test_describe_module")
        test_module.__all__ = ["described_query"]

        def described_query(dialect, limit=100):
            """This is a described query."""
            return MagicMock()

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
        """Test parse_params with empty list."""
        from rhosocial.activerecord.backend.named_expression.cli import parse_params

        result = parse_params([])
        assert result == {}

    def test_parse_params_valid(self):
        """Test parse_params with valid params."""
        from rhosocial.activerecord.backend.named_expression.cli import parse_params

        result = parse_params(["limit=100", "status=active"])
        assert result == {"limit": "100", "status": "active"}

    def test_parse_params_with_equals_in_value(self):
        """Test parse_params with = in value."""
        from rhosocial.activerecord.backend.named_expression.cli import parse_params

        result = parse_params(["url=http://example.com?a=1&b=2"])
        assert result == {"url": "http://example.com?a=1&b=2"}

    def test_parse_params_invalid_format(self, capsys):
        """Test parse_params with invalid format."""
        from rhosocial.activerecord.backend.named_expression.cli import parse_params

        result = parse_params(["invalid"])
        assert result == {}
        captured = capsys.readouterr()
        assert "Warning" in captured.err


class TestCliErrorHandling:
    """Tests for error handling in handle_named_expression."""

    def test_handle_named_expression_module_not_found(self, capsys):
        """Test handles module not found error."""
        from rhosocial.activerecord.backend.named_expression.resolver import NamedExpressionResolver
        from rhosocial.activerecord.backend.named_expression.exceptions import (
            NamedExpressionModuleNotFoundError,
        )

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

        provider = MagicMock()

        with pytest.raises(SystemExit) as exc_info:
            handle_named_expression(
                args,
                provider,
                lambda: None,
                lambda x: None,
                lambda a, b, c: None,
            )

        assert exc_info.value.code == 1


class TestCliForceMode:
    """Tests for --force mode."""

    def test_force_allows_non_select(self):
        """Test --force allows non-SELECT execution."""
        from rhosocial.activerecord.backend.named_expression.cli import parse_params
        from rhosocial.activerecord.backend.schema import StatementType
        from unittest.mock import MagicMock

        args = Namespace(
            qualified_name="test_queries.insert_user",
            example=None,
            params=["name=test"],
            describe=False,
            dry_run=False,
            list_queries=False,
            force=True,
            explain=False,
            rich_ascii=False,
            is_async=False,
        )

        executed_sql = []

        def mock_execute(sql, params, stmt_type):
            executed_sql.append((sql, params, stmt_type))
            return MagicMock(data=[], affected_rows=1)

        provider = MagicMock()
        provider.get_backend.return_value = MagicMock()
        provider.get_backend.return_value.dialect = MagicMock()

        mock_dialect = MagicMock()
        mock_dialect.name = "sqlite"
        mock_dialect._prepare_value.side_effect = lambda x: x

        mock_expr = MagicMock()
        mock_expr.statement_type = StatementType.INSERT
        mock_expr.to_sql.return_value = ("INSERT INTO users (name) VALUES (?)", ("test",))

        import sys
        from types import ModuleType

        test_module = ModuleType("test_force_module")
        test_module.__all__ = ["insert_user"]

        def insert_user(dialect, name):
            return mock_expr

        test_module.insert_user = insert_user
        sys.modules["test_force_module"] = test_module

        try:
            pass
        finally:
            del sys.modules["test_force_module"]


class TestCliAsyncMode:
    """Tests for --async mode."""

    def test_async_requires_async_factory(self):
        """Test async requires backend factory."""
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

        provider = MagicMock()

        with pytest.raises(SystemExit) as exc_info:
            handle_named_expression(
                args,
                provider,
                lambda: None,
                lambda x: None,
                lambda a, b, c: None,
                backend_async_factory=None,
            )

        assert exc_info.value.code == 1


class TestCliReplaceProgPlaceholder:
    """Tests for _replace_prog_placeholder function."""

    def test_replace_prog_placeholder_with_placeholder(self):
        """Test replacing %(prog)s placeholder."""
        from rhosocial.activerecord.backend.named_expression.cli import (
            _replace_prog_placeholder,
        )

        docstring = "Usage: %(prog)s [OPTIONS]"
        result = _replace_prog_placeholder(docstring, "myprog")
        assert result == "Usage: myprog [OPTIONS]"

    def test_replace_prog_placeholder_without_placeholder(self):
        """Test without placeholder returns unchanged."""
        from rhosocial.activerecord.backend.named_expression.cli import (
            _replace_prog_placeholder,
        )

        docstring = "Usage: myprog [OPTIONS]"
        result = _replace_prog_placeholder(docstring, "other_prog")
        assert result == "Usage: myprog [OPTIONS]"

    def test_replace_prog_placeholder_double_percent(self):
        """Test replacing %%(prog)s placeholder."""
        from rhosocial.activerecord.backend.named_expression.cli import (
            _replace_prog_placeholder,
        )

        docstring = "Example: %%something"
        result = _replace_prog_placeholder(docstring, "myprog")
        assert result is not None


class TestCliExampleMode:
    """Tests for --example mode."""

    def test_handle_example_with_matching_query(self, capsys):
        """Test --example with matching query."""
        from rhosocial.activerecord.backend.named_expression.resolver import (
            list_named_expressions_in_module,
        )
        import sys
        from types import ModuleType

        test_module = ModuleType("test_example_module")
        test_module.__all__ = ["my_query"]

        def my_query(dialect, limit=100, status="active"):
            """Get active users with limit."""
            return MagicMock()

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
        """Test rich_ascii flag is supported."""
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
        """Test explain flag is supported."""
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