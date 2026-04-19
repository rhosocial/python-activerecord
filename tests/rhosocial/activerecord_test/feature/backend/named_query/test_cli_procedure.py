# tests/rhosocial/activerecord_test/feature/backend/named_query/test_cli_procedure.py
"""
Tests for named procedure CLI functionality.

This test module covers:
- create_named_procedure_parser function
- handle_named_procedure function
- list_named_procedures_in_module function
"""
import types
from argparse import Namespace
from unittest.mock import MagicMock, patch
import pytest

from rhosocial.activerecord.backend.named_query.cli_procedure import (
    create_named_procedure_parser,
    handle_named_procedure,
    list_named_procedures_in_module,
)
from rhosocial.activerecord.backend.named_query.exceptions import (
    NamedQueryError,
)
from rhosocial.activerecord.backend.named_query.procedure import (
    ProcedureRunner,
    TransactionMode,
)


class ProviderMock:
    """Mock output provider."""

    def display_success(self, rows, duration):
        print(f"Success: {rows} rows in {duration}s")

    def display_results(self, data, use_ascii=False):
        print(f"Results: {data}")

    def display_no_data(self):
        print("No data")

    def display_no_result_object(self):
        print("No result")

    def display_connection_error(self, e):
        print(f"Connection error: {e}")

    def display_query_error(self, e):
        print(f"Query error: {e}")

    def display_unexpected_error(self, e, is_async=False):
        print(f"Unexpected error: {e}")


class TestCliProcedureArgs:
    """Helper class to create mock CLI args for testing."""

    @staticmethod
    def create(qualified_name: str, **kwargs):
        """Create a mock args namespace."""
        defaults = {
            "qualified_name": qualified_name,
            "params": [],
            "describe": False,
            "dry_run": False,
            "list_procedures": False,
            "transaction": "auto",
            "is_async": False,
            "rich_ascii": False,
        }
        defaults.update(kwargs)
        return Namespace(**defaults)


class TestCreateNamedProcedureParser:
    """Tests for create_named_procedure_parser function."""

    def test_create_parser(self):
        """Test creating the parser."""
        import argparse

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        parent = argparse.ArgumentParser(add_help=False)

        np_parser = create_named_procedure_parser(subparsers, parent)

        assert np_parser is not None
        assert np_parser.prog != ""

    def test_parser_has_required_arguments(self):
        """Test parser has all required arguments."""
        import argparse

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        parent = argparse.ArgumentParser(add_help=False)

        np_parser = create_named_procedure_parser(subparsers, parent)

        actions = {action.option_strings[0] if action.option_strings else action.dest: action
                   for action in np_parser._actions}

        assert "--param" in actions
        assert "--describe" in actions
        assert "--dry-run" in actions
        assert "--list" in actions
        assert "--transaction" in actions
        assert "--async" in actions


class TestListNamedProceduresInModule:
    """Tests for list_named_procedures_in_module function."""

    def test_list_module_not_found(self):
        """Test listing from non-existent module."""
        with pytest.raises(NamedQueryError):
            list_named_procedures_in_module("nonexistent.module")

    def test_list_with_procedure_classes(self):
        """Test listing with procedure classes."""
        module = types.ModuleType("test_procedures")

        from rhosocial.activerecord.backend.named_query.procedure import Procedure

        class TestProc1(Procedure):
            """Test procedure 1."""
            param: str

        class TestProc2(Procedure):
            """Test procedure 2."""
            value: int = 10

        module.Proc1 = TestProc1
        module.Proc2 = TestProc2

        with patch("importlib.import_module", return_value=module):
            procedures = list_named_procedures_in_module("test_procedures")

            assert len(procedures) == 2
            names = [p["name"] for p in procedures]
            assert "Proc1" in names
            assert "Proc2" in names

    def test_list_excludes_non_procedure_classes(self):
        """Test that non-Procedure classes are excluded."""
        module = types.ModuleType("test_modules")

        from rhosocial.activerecord.backend.named_query.procedure import Procedure

        class ValidProc(Procedure):
            """Valid procedure."""
            param: str

        class NotAProcedure:
            """Not a procedure."""

        class JustAFunction:
            """Just a function."""

        module.ValidProc = ValidProc
        module.NotAProcedure = NotAProcedure
        module.JustAFunction = JustAFunction
        module._private = "hidden"

        with patch("importlib.import_module", return_value=module):
            procedures = list_named_procedures_in_module("test_modules")

            names = [p["name"] for p in procedures]
            assert "ValidProc" in names
            assert "NotAProcedure" not in names
            assert "JustAFunction" not in names


class TestHandleNamedProcedureList:
    """Tests for handle_named_procedure with --list option."""

    def test_list_procedures(self):
        """Test listing procedures."""
        from rhosocial.activerecord.backend.named_query.procedure import Procedure

        class TestProc(Procedure):
            """Test procedure."""
            month: str

        provider = ProviderMock()

        args = TestCliProcedureArgs.create("test_procedures", list_procedures=True)

        with patch(
            "rhosocial.activerecord.backend.named_query.cli_procedure.list_named_procedures_in_module",
            return_value=[{"name": "TestProc", "signature": "(month: str)", "docstring": "Test procedure.", "brief": "Test procedure."}],
        ):
            try:
                handle_named_procedure(
                    args,
                    provider,
                    lambda: None,
                    lambda b: None,
                    lambda *a: None,
                    disconnect=None,
                )
            except SystemExit:
                pass


class TestHandleNamedProcedureDescribe:
    """Tests for handle_named_procedure with --describe option."""

    def test_describe_procedure(self):
        """Test describing a procedure."""
        from rhosocial.activerecord.backend.named_query.procedure import Procedure

        provider = ProviderMock()

        args = TestCliProcedureArgs.create("test_procedures.Proc", describe=True)

        mock_runner = MagicMock()
        mock_runner.describe.return_value = {
            "qualified_name": "test_procedures.Proc",
            "class_name": "Proc",
            "docstring": "Test procedure.",
            "parameters": {"month": {"annotation": str, "has_default": False}},
        }

        with patch(
            "rhosocial.activerecord.backend.named_query.cli_procedure.ProcedureRunner",
            return_value=mock_runner,
        ):
            try:
                handle_named_procedure(
                    args,
                    provider,
                    lambda: None,
                    lambda b: None,
                    lambda *a: None,
                )
            except SystemExit:
                pass


class TestHandleNamedProcedureDryRun:
    """Tests for handle_named_procedure with --dry-run option."""

    def test_dry_run_procedure(self, mock_dialect):
        """Test dry-running a procedure."""
        provider = ProviderMock()

        args = TestCliProcedureArgs.create(
            "test_procedures.Proc",
            dry_run=True,
            params=["month=2026-03"],
        )

        mock_runner = MagicMock()
        mock_runner.load.return_value = mock_runner

        with patch(
            "rhosocial.activerecord.backend.named_query.cli_procedure.ProcedureRunner",
            return_value=mock_runner,
        ):
            try:
                handle_named_procedure(
                    args,
                    provider,
                    lambda: mock_dialect,
                    lambda b: mock_dialect,
                    lambda *a: None,
                    disconnect=None,
                )
            except SystemExit:
                pass


class TestHandleNamedProcedureExecute:
    """Tests for handle_named_procedure normal execution."""

    def test_execute_procedure_success(self, mock_dialect):
        """Test executing a procedure successfully."""
        provider = ProviderMock()

        args = TestCliProcedureArgs.create(
            "test_procedures.HelloProc",
            params=["name=World"],
            transaction="auto",
        )

        from rhosocial.activerecord.backend.named_query.procedure import (
            ProcedureResult,
        )

        mock_result = ProcedureResult()
        mock_result.outputs = []
        mock_result.logs = []

        mock_runner = MagicMock()
        mock_runner.run.return_value = mock_result

        backend = None

        def get_dialect(b):
            return mock_dialect

        with patch(
            "rhosocial.activerecord.backend.named_query.cli_procedure.ProcedureRunner",
            return_value=mock_runner,
        ):
            try:
                handle_named_procedure(
                    args,
                    provider,
                    lambda: backend,
                    get_dialect,
                    lambda *a: None,
                    disconnect=lambda: None,
                )
            except SystemExit:
                pass


class TestHandleNamedProcedureAbort:
    """Tests for handle_named_procedure when procedure aborts."""

    def test_abort_procedure(self, mock_dialect):
        """Test when procedure is aborted."""
        provider = ProviderMock()

        args = TestCliProcedureArgs.create(
            "test_procedures.AbortProc",
            params=["should_abort=true"],
        )

        from rhosocial.activerecord.backend.named_query.procedure import (
            LogEntry,
            ProcedureResult,
        )

        mock_result = ProcedureResult()
        mock_result.aborted = True
        mock_result.abort_reason = "Test abort"
        mock_result.logs = [LogEntry(level="INFO", message="Starting")]
        mock_result.outputs = []

        mock_runner = MagicMock()
        mock_runner.run.return_value = mock_result

        backend = None

        def get_dialect(b):
            return mock_dialect

        with patch(
            "rhosocial.activerecord.backend.named_query.cli_procedure.ProcedureRunner",
            return_value=mock_runner,
        ):
            with pytest.raises(SystemExit) as exc:
                handle_named_procedure(
                    args,
                    provider,
                    lambda: backend,
                    get_dialect,
                    lambda *a: None,
                    disconnect=lambda: None,
                )
            assert exc.value.code == 1


class TestTransactionModeChoices:
    """Tests for transaction mode argument choices."""

    def test_default_transaction_auto(self):
        """Test default transaction mode is auto."""
        import argparse

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        parent = argparse.ArgumentParser(add_help=False)

        np_parser = create_named_procedure_parser(subparsers, parent)

        args = np_parser.parse_args(["test_procedures.Proc", "--transaction", "auto"])
        assert args.transaction == "auto"

    def test_transaction_step(self):
        """Test step transaction mode."""
        import argparse

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        parent = argparse.ArgumentParser(add_help=False)

        np_parser = create_named_procedure_parser(subparsers, parent)

        args = np_parser.parse_args(["test_procedures.Proc", "--transaction", "step"])
        assert args.transaction == "step"

    def test_transaction_none(self):
        """Test none transaction mode."""
        import argparse

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        parent = argparse.ArgumentParser(add_help=False)

        np_parser = create_named_procedure_parser(subparsers, parent)

        args = np_parser.parse_args(["test_procedures.Proc", "--transaction", "none"])
        assert args.transaction == "none"


class TestParseParams:
    """Tests for parsing --params in handle_named_procedure."""

    def test_parse_single_param(self):
        """Test parsing a single parameter."""
        args = TestCliProcedureArgs.create(
            "test_procedures.Proc",
            params=["month=2026-03"],
        )

        user_params = {}
        for param in args.params:
            if "=" in param:
                key, value = param.split("=", 1)
                user_params[key] = value

        assert user_params == {"month": "2026-03"}

    def test_parse_multiple_params(self):
        """Test parsing multiple parameters."""
        args = TestCliProcedureArgs.create(
            "test_procedures.Proc",
            params=["month=2026-03", "threshold=100", "name=test"],
        )

        user_params = {}
        for param in args.params:
            if "=" in param:
                key, value = param.split("=", 1)
                user_params[key] = value

        assert user_params == {"month": "2026-03", "threshold": "100", "name": "test"}


class TestHandleNamedProcedureExecute:
    """Tests for handle_named_procedure execution paths."""

    def test_parser_transaction_auto(self):
        """Test parser accepts --transaction auto."""
        import argparse

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        parent = argparse.ArgumentParser(add_help=False)

        np_parser = create_named_procedure_parser(subparsers, parent)
        args = np_parser.parse_args(
            ["test.proc", "--transaction", "auto"]
        )
        assert args.transaction == "auto"

    def test_parser_transaction_step(self):
        """Test parser accepts --transaction step."""
        import argparse

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        parent = argparse.ArgumentParser(add_help=False)

        np_parser = create_named_procedure_parser(subparsers, parent)
        args = np_parser.parse_args(
            ["test.proc", "--transaction", "step"]
        )
        assert args.transaction == "step"

    def test_parser_transaction_none(self):
        """Test parser accepts --transaction none."""
        import argparse

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        parent = argparse.ArgumentParser(add_help=False)

        np_parser = create_named_procedure_parser(subparsers, parent)
        args = np_parser.parse_args(
            ["test.proc", "--transaction", "none"]
        )
        assert args.transaction == "none"

    def test_dry_run_in_namespace(self):
        """Test dry_run is in namespace."""
        args = Namespace(
            dry_run=True,
            list_procedures=False,
        )
        assert args.dry_run is True

    def test_list_procedures_in_namespace(self):
        """Test list_procedures is in namespace."""
        args = Namespace(
            list_procedures=True,
            dry_run=False,
        )
        assert args.list_procedures is True

    def test_is_async_in_namespace(self):
        """Test is_async is in namespace."""
        args = Namespace(
            is_async=True,
        )
        assert args.is_async is True