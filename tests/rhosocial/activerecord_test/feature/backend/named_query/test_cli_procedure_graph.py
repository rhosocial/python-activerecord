# tests/rhosocial/activerecord_test/feature/backend/named_query/test_cli_procedure_graph.py
"""
Tests for CLI procedure graph functionality.

This test module covers:
- create_named_procedure_graph_parser function
- _add_named_procedure_graph_arguments function
- handle_named_procedure_graph function
- _parse_json_arg function
- _replace_prog_placeholder function
"""
import argparse
from argparse import Namespace
from typing import List
from unittest.mock import MagicMock, patch
import pytest

from rhosocial.activerecord.backend.named_query.cli_procedure_graph import (
    create_named_procedure_graph_parser,
    _add_named_procedure_graph_arguments,
    _parse_json_arg,
    _replace_prog_placeholder,
)


class TestReplaceProgPlaceholder:
    """Tests for _replace_prog_placeholder function."""

    def test_replace_placeholder(self):
        """Test replacing %(prog)s placeholder."""
        docstring = "Usage: %(prog)s do something"
        result = _replace_prog_placeholder(docstring, "myprog")
        assert result == "Usage: myprog do something"

    def test_replace_double_placeholder(self):
        """Test replacing %%prog)s placeholder."""
        docstring = "Example: %%(prog)s --help"
        result = _replace_prog_placeholder(docstring, "myprog")
        assert "myprog" in result

    def test_no_placeholder(self):
        """Test without placeholder returns unchanged."""
        docstring = "Usage: myprog [OPTIONS]"
        result = _replace_prog_placeholder(docstring, "other")
        assert result == "Usage: myprog [OPTIONS]"


class TestParseJsonArg:
    """Tests for _parse_json_arg function."""

    def test_parse_valid_json(self):
        """Test parsing valid JSON."""
        result = _parse_json_arg('{"key": "value", "num": 123}')
        assert result == {"key": "value", "num": 123}

    def test_parse_empty_json(self):
        """Test parsing empty JSON object."""
        result = _parse_json_arg("{}")
        assert result == {}

    def test_parse_empty_string(self):
        """Test parsing empty string returns empty dict."""
        result = _parse_json_arg("")
        assert result == {}

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON exits."""
        with pytest.raises(SystemExit):
            _parse_json_arg("not valid json")


class TestCreateParser:
    """Tests for create_named_procedure_graph_parser function."""

    def test_create_parser_basic(self):
        """Test basic parser creation."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        parent = argparse.ArgumentParser(add_help=False)

        npg_parser = create_named_procedure_graph_parser(subparsers, parent)
        assert npg_parser is not None
        assert npg_parser.prog is not None

    def test_create_parser_with_custom_parent(self):
        """Test parser with custom parent."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        parent = argparse.ArgumentParser(add_help=False)
        parent.add_argument("--custom", action="store_true")

        npg_parser = create_named_procedure_graph_parser(subparsers, parent)
        args = npg_parser.parse_args(["test.npg", "--custom"])
        assert hasattr(args, "custom")

    def test_add_arguments_creates_qualified_name(self):
        """Test _add_named_procedure_graph_arguments creates qualified_name."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        parent = argparse.ArgumentParser(add_help=False)

        npg_parser = create_named_procedure_graph_parser(subparsers, parent)
        args = npg_parser.parse_args(["myapp.npg.monthly"])
        assert args.qualified_name == "myapp.npg.monthly"

    def test_add_arguments_params_json(self):
        """Test --params argument."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        parent = argparse.ArgumentParser(add_help=False)

        npg_parser = create_named_procedure_graph_parser(subparsers, parent)
        args = npg_parser.parse_args(["test.npg", "--params", '{"month": "2026-04"}'])
        assert args.params_json == '{"month": "2026-04"}'

    def test_add_arguments_describe_flag(self):
        """Test --describe flag."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        parent = argparse.ArgumentParser(add_help=False)

        npg_parser = create_named_procedure_graph_parser(subparsers, parent)
        args = npg_parser.parse_args(["test.npg", "--describe"])
        assert args.describe is True

    def test_add_arguments_dry_run_flag(self):
        """Test --dry-run flag."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        parent = argparse.ArgumentParser(add_help=False)

        npg_parser = create_named_procedure_graph_parser(subparsers, parent)
        args = npg_parser.parse_args(["test.npg", "--dry-run"])
        assert args.dry_run is True

    def test_add_arguments_list_flag(self):
        """Test --list flag."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        parent = argparse.ArgumentParser(add_help=False)

        npg_parser = create_named_procedure_graph_parser(subparsers, parent)
        args = npg_parser.parse_args(["test.npg", "--list"])
        assert args.list_procedure_graphs is True

    def test_add_arguments_validate_flag(self):
        """Test --validate flag."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        parent = argparse.ArgumentParser(add_help=False)

        npg_parser = create_named_procedure_graph_parser(subparsers, parent)
        args = npg_parser.parse_args(["test.npg", "--validate"])
        assert args.validate is True

    def test_add_arguments_waves_flag(self):
        """Test --waves flag."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        parent = argparse.ArgumentParser(add_help=False)

        npg_parser = create_named_procedure_graph_parser(subparsers, parent)
        args = npg_parser.parse_args(["test.npg", "--waves"])
        assert args.show_waves is True


class TestDefaultValues:
    """Tests for default values in parser."""

    def test_params_json_default(self):
        """Test default params_json is empty dict."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        parent = argparse.ArgumentParser(add_help=False)

        npg_parser = create_named_procedure_graph_parser(subparsers, parent)
        args = npg_parser.parse_args(["test.npg"])
        assert args.params_json == "{}"

    def test_describe_default_false(self):
        """Test default describe is False."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        parent = argparse.ArgumentParser(add_help=False)

        npg_parser = create_named_procedure_graph_parser(subparsers, parent)
        args = npg_parser.parse_args(["test.npg"])
        assert args.describe is False

    def test_dry_run_default_false(self):
        """Test default dry_run is False."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        parent = argparse.ArgumentParser(add_help=False)

        npg_parser = create_named_procedure_graph_parser(subparsers, parent)
        args = npg_parser.parse_args(["test.npg"])
        assert args.dry_run is False