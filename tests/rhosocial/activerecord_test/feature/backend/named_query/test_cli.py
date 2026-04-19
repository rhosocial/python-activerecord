# tests/rhosocial/activerecord_test/feature/backend/named_query/test_cli.py
"""
Tests for named query CLI utilities.

This test module covers:
- create_named_query_parser function
- parse_params function
- handle_named_query function
"""
import argparse
from argparse import Namespace
from unittest.mock import MagicMock, patch
import pytest

from rhosocial.activerecord.backend.named_query.cli import (
    create_named_query_parser,
    parse_params,
    handle_named_query,
)


class TestReplaceProgPlaceholder:
    """Tests for _replace_prog_placeholder."""

    def test_replace_prog_placeholder_single(self):
        """Test replacing %(prog)s placeholder."""
        from rhosocial.activerecord.backend.named_query.cli import (
            _replace_prog_placeholder,
        )
        doc = "Usage: %(prog)s query"
        result = _replace_prog_placeholder(doc, "myprog")
        assert result == "Usage: myprog query"

    def test_replace_prog_placeholder_double(self):
        """Test replacing %%%(prog)s placeholder."""
        from rhosocial.activerecord.backend.named_query.cli import (
            _replace_prog_placeholder,
        )
        doc = "Example: %%(prog)s"
        result = _replace_prog_placeholder(doc, "myprog")
        assert result == "Example: myprog" or result == "Example: %myprog"

    def test_replace_prog_placeholder_default(self):
        """Test default prog value."""
        from rhosocial.activerecord.backend.named_query.cli import (
            _replace_prog_placeholder,
        )
        doc = "Usage: %(prog)s"
        result = _replace_prog_placeholder(doc)
        assert "python -m rhosocial" in result


class TestCreateNamedQueryParser:
    """Tests for create_named_query_parser function."""

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
        parser = create_named_query_parser(subparsers, parent)
        assert parser is not None
        assert isinstance(parser, argparse.ArgumentParser)

    def test_parser_has_qualified_name(self, parser_setup):
        """Test parser has qualified_name argument."""
        parent, subparsers = parser_setup
        parser = create_named_query_parser(subparsers, parent)
        args = parser.parse_args(["myapp.queries.test", "--db-file", "test.db"])
        assert args.qualified_name == "myapp.queries.test"

    def test_parser_has_example(self, parser_setup):
        """Test parser has --example/-e argument."""
        parent, subparsers = parser_setup
        parser = create_named_query_parser(subparsers, parent)
        args = parser.parse_args(
            ["myapp.queries.test", "--db-file", "test.db", "-e", "test"]
        )
        assert args.example == "test"

    def test_parser_has_describe(self, parser_setup):
        """Test parser has --describe argument."""
        parent, subparsers = parser_setup
        parser = create_named_query_parser(subparsers, parent)
        args = parser.parse_args(
            ["myapp.queries.test", "--db-file", "test.db", "--describe"]
        )
        assert args.describe is True

    def test_parser_has_dry_run(self, parser_setup):
        """Test parser has --dry-run argument."""
        parent, subparsers = parser_setup
        parser = create_named_query_parser(subparsers, parent)
        args = parser.parse_args(
            ["myapp.queries.test", "--db-file", "test.db", "--dry-run"]
        )
        assert args.dry_run is True

    def test_parser_has_list(self, parser_setup):
        """Test parser has --list argument."""
        parent, subparsers = parser_setup
        parser = create_named_query_parser(subparsers, parent)
        args = parser.parse_args(
            ["myapp.queries.test", "--db-file", "test.db", "--list"]
        )
        assert args.list_queries is True

    def test_parser_has_param(self, parser_setup):
        """Test parser has --param argument."""
        parent, subparsers = parser_setup
        parser = create_named_query_parser(subparsers, parent)
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
        parser = create_named_query_parser(subparsers, parent)
        args = parser.parse_args(
            ["myapp.queries.test", "--db-file", "test.db", "--force"]
        )
        assert args.force is True

    def test_parser_has_explain(self, parser_setup):
        """Test parser has --explain argument."""
        parent, subparsers = parser_setup
        parser = create_named_query_parser(subparsers, parent)
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


class TestHandleNamedQueryList:
    """Tests for handle_named_query with --list option."""

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
        )

        provider = MagicMock()
        with patch(
            "rhosocial.activerecord.backend.named_query.cli.list_named_queries_in_module",
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
            handle_named_query(
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
        )

        provider = MagicMock()
        with patch(
            "rhosocial.activerecord.backend.named_query.cli.list_named_queries_in_module",
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
            handle_named_query(
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
        )

        provider = MagicMock()
        with patch(
            "rhosocial.activerecord.backend.named_query.cli.list_named_queries_in_module",
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
            with pytest.raises(SystemExit):
                handle_named_query(
                    args,
                    provider,
                    lambda: None,
                    lambda x: None,
                    lambda a, b, c: None,
                )


class TestHandleNamedQueryDescribe:
    """Tests for handle_named_query with --describe option."""

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
            "rhosocial.activerecord.backend.named_query.cli.NamedQueryResolver",
            return_value=mock_resolver,
        ):
            handle_named_query(
                args,
                provider,
                lambda: None,
                lambda x: None,
                lambda a, b, c: None,
            )


class TestHandleNamedQueryExecute:
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
            handle_named_query(
                args,
                provider,
                fail_backend_factory,
                lambda x: None,
                lambda a, b, c: None,
            )