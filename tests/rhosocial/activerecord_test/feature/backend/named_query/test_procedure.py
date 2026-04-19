# tests/rhosocial/activerecord_test/feature/backend/named_query/test_procedure.py
"""
Tests for named procedure functionality.

This test module covers:
- Procedure base class
- ProcedureContext methods (execute, scalar, rows, bind, log, abort)
- ProcedureRunner execution
- TransactionMode
"""
import types
from unittest.mock import MagicMock, patch
import pytest

from rhosocial.activerecord.backend.named_query.procedure import (
    Procedure,
    ProcedureContext,
    ProcedureRunner,
    ProcedureResult,
    TransactionMode,
    LogEntry,
)
from rhosocial.activerecord.backend.named_query.exceptions import (
    NamedQueryError,
)
from rhosocial.activerecord.backend.named_query.resolver import resolve_named_query


class TestProcedureClass:
    """Tests for Procedure base class."""

    def test_get_parameters(self):
        """Test getting parameter info from class attributes."""

        class TestProcedure(Procedure):
            required_param: str
            optional_param: int = 10

        params = TestProcedure.get_parameters()
        assert "required_param" in params
        assert "optional_param" in params
        assert params["required_param"]["has_default"] is False
        assert params["optional_param"]["has_default"] is True

    def test_run_not_implemented(self):
        """Test that run() raises NotImplementedError."""

        class EmptyProcedure(Procedure):
            pass

        proc = EmptyProcedure()
        ctx = MagicMock()
        with pytest.raises(NotImplementedError):
            proc.run(ctx)


class TestProcedureContextInit:
    """Tests for ProcedureContext initialization."""

    def test_init_with_defaults(self, mock_dialect):
        """Test initialization with default values."""
        ctx = ProcedureContext(mock_dialect, lambda *a: None)

        assert ctx.dialect is mock_dialect
        assert ctx.bindings == {}

    def test_init_with_transaction_mode(self, mock_dialect):
        """Test initialization with custom transaction mode."""
        callback = lambda *a: None
        ctx = ProcedureContext(mock_dialect, callback, TransactionMode.STEP)

        assert ctx._transaction_mode == TransactionMode.STEP


class TestProcedureContextBind:
    """Tests for ProcedureContext.bind()."""

    def test_bind_data(self, mock_dialect):
        """Test binding arbitrary data."""
        ctx = ProcedureContext(mock_dialect, lambda *a: None)

        ctx.bind("my_var", {"key": "value"})
        assert "my_var" in ctx.bindings
        assert ctx.bindings["my_var"]["data"] == [{"key": "value"}]

    def test_bind_empty_data(self, mock_dialect):
        """Test binding empty data."""
        ctx = ProcedureContext(mock_dialect, lambda *a: None)

        ctx.bind("empty_var", None)
        assert "empty_var" in ctx.bindings


class TestProcedureContextScalar:
    """Tests for ProcedureContext.scalar()."""

    def test_scalar_existing_column(self, mock_dialect):
        """Test extracting scalar from bound data."""
        ctx = ProcedureContext(mock_dialect, lambda *a: None)
        ctx.bind("test_data", [{"id": 1, "count": 42}])

        result = ctx.scalar("test_data", "count")
        assert result == 42

    def test_scalar_missing_variable(self, mock_dialect):
        """Test scalar with missing variable."""
        ctx = ProcedureContext(mock_dialect, lambda *a: None)

        with pytest.raises(ValueError) as exc:
            ctx.scalar("nonexistent", "id")
        assert "not found" in str(exc.value)

    def test_scalar_empty_data(self, mock_dialect):
        """Test scalar with empty data."""
        ctx = ProcedureContext(mock_dialect, lambda *a: None)
        ctx.bind("empty_data", [])

        result = ctx.scalar("empty_data", "id")
        assert result is None


class TestProcedureContextRows:
    """Tests for ProcedureContext.rows()."""

    def test_rows_iteration(self, mock_dialect):
        """Test iterating over rows."""
        ctx = ProcedureContext(mock_dialect, lambda *a: None)
        test_data = [{"id": 1}, {"id": 2}, {"id": 3}]
        ctx.bind("iter_data", test_data)

        rows = list(ctx.rows("iter_data"))
        assert len(rows) == 3

    def test_rows_missing_variable(self, mock_dialect):
        """Test rows with missing variable."""
        ctx = ProcedureContext(mock_dialect, lambda *a: None)

        with pytest.raises(ValueError):
            list(ctx.rows("nonexistent"))


class TestProcedureContextLog:
    """Tests for ProcedureContext.log()."""

    def test_log_message(self, mock_dialect):
        """Test logging a message."""
        ctx = ProcedureContext(mock_dialect, lambda *a, **kw: {"data": []})

        ctx.log("Test message", "INFO")
        assert len(ctx._logs) == 1
        assert ctx._logs[0].level == "INFO"
        assert ctx._logs[0].message == "Test message"

    def test_log_different_levels(self, mock_dialect):
        """Test logging with different levels."""
        ctx = ProcedureContext(mock_dialect, lambda *a, **kw: {"data": []})

        ctx.log("Debug message", "DEBUG")
        ctx.log("Warning message", "WARNING")
        ctx.log("Error message", "ERROR")

        assert len(ctx._logs) == 3
        assert ctx._logs[0].level == "DEBUG"


class TestProcedureContextAbort:
    """Tests for ProcedureContext.abort()."""

    def test_abort_raises_error(self, mock_dialect):
        """Test that abort raises an error."""
        ctx = ProcedureContext(mock_dialect, lambda *a: None)

        with pytest.raises(NamedQueryError) as exc:
            ctx.abort("Test abort reason")
        assert "aborted" in str(exc.value).lower()


class TestProcedureRunnerInit:
    """Tests for ProcedureRunner.__init__()."""

    def test_valid_qualified_name(self):
        """Test initialization with valid qualified name."""
        runner = ProcedureRunner("myapp.procedures.monthly_report")
        assert runner.qualified_name == "myapp.procedures.monthly_report"

    def test_invalid_qualified_name_no_dot(self):
        """Test initialization fails without dot."""
        with pytest.raises(NamedQueryError) as exc:
            ProcedureRunner("NoProcedure")
        assert "Invalid qualified name" in str(exc.value)


class TestProcedureRunnerLoad:
    """Tests for ProcedureRunner.load()."""

    def test_load_success(self):
        """Test loading a procedure class."""
        module = types.ModuleType("test_procedures")

        class TestProc(Procedure):
            param: str = "default"

        module.TestProc = TestProc

        with patch("importlib.import_module", return_value=module):
            runner = ProcedureRunner("test_procedures.TestProc").load()
            assert runner._procedure_class is not None

    def test_load_not_a_procedure(self):
        """Test loading fails when class doesn't inherit Procedure."""
        module = types.ModuleType("test_procedures")

        class NotAProcedure:
            pass

        module.NotAProcedure = NotAProcedure

        with patch("importlib.import_module", return_value=module):
            runner = ProcedureRunner("test_procedures.NotAProcedure")
            with pytest.raises(NamedQueryError) as exc:
                runner.load()
            assert "must inherit from Procedure" in str(exc.value)

    def test_load_module_not_found(self):
        """Test loading fails when module doesn't exist."""
        with pytest.raises(Exception):
            ProcedureRunner("nonexistent.module.Proc").load()


class TestProcedureRunnerDescribe:
    """Tests for ProcedureRunner.describe()."""

    def test_describe(self):
        """Test getting procedure description."""
        module = types.ModuleType("test_procedures")

        class DocProcedure(Procedure):
            """Test procedure docstring."""
            month: str

        module.DocProcedure = DocProcedure

        with patch("importlib.import_module", return_value=module):
            runner = ProcedureRunner("test_procedures.DocProcedure").load()
            info = runner.describe()

            assert info["qualified_name"] == "test_procedures.DocProcedure"
            assert "docstring" in info
            assert "parameters" in info


class TestProcedureRunnerRun:
    """Tests for ProcedureRunner.run()."""

    def test_run_simple_procedure(self, mock_dialect):
        """Test running a simple procedure."""
        module = types.ModuleType("test_procedures")

        class HelloProc(Procedure):
            name: str = "World"

            def run(self, ctx: ProcedureContext) -> None:
                ctx.log(f"Hello, {self.name}!")

        module.HelloProc = HelloProc

        with patch("importlib.import_module", return_value=module):
            runner = ProcedureRunner("test_procedures.HelloProc").load()
            result = runner.run(mock_dialect, {"name": "Test"})

            assert len(result.logs) == 1
            assert "Hello, Test!" in result.logs[0].message

    def test_run_with_abort(self, mock_dialect):
        """Test running a procedure that aborts."""
        module = types.ModuleType("test_procedures")

        class AbortProc(Procedure):
            should_abort: bool = False

            def run(self, ctx: ProcedureContext) -> None:
                if self.should_abort:
                    ctx.abort("Test abort")
                ctx.log("After abort")

        module.AbortProc = AbortProc

        with patch("importlib.import_module", return_value=module):
            runner = ProcedureRunner("test_procedures.AbortProc").load()
            result = runner.run(mock_dialect, {"should_abort": True})

            assert result.aborted is True
            assert "Test abort" in str(result.abort_reason)

    def test_run_with_bind_and_rows(self, mock_dialect):
        """Test running procedure with bind and rows."""
        module = types.ModuleType("test_procedures")

        class BindRowsProc(Procedure):
            def run(self, ctx: ProcedureContext) -> None:
                ctx.bind("items", [{"id": 1}, {"id": 2}])

                count = sum(1 for _ in ctx.rows("items"))
                ctx.log(f"Count: {count}")

        module.BindRowsProc = BindRowsProc

        with patch("importlib.import_module", return_value=module):
            runner = ProcedureRunner("test_procedures.BindRowsProc").load()
            result = runner.run(mock_dialect, {})

            assert len(result.logs) == 1


class TestTransactionMode:
    """Tests for TransactionMode enum."""

    def test_auto_value(self):
        assert TransactionMode.AUTO.value == "auto"

    def test_step_value(self):
        assert TransactionMode.STEP.value == "step"

    def test_none_value(self):
        assert TransactionMode.NONE.value == "none"


class TestProcedureResult:
    """Tests for ProcedureResult dataclass."""

    def test_default_values(self):
        """Test default values."""
        result = ProcedureResult()

        assert result.outputs == []
        assert result.logs == []
        assert result.aborted is False
        assert result.abort_reason is None

    def test_with_values(self):
        """Test with custom values."""
        logs = [LogEntry(level="INFO", message="test")]
        result = ProcedureResult(logs=logs, aborted=True, abort_reason="error")

        assert result.logs == logs
        assert result.aborted is True
        assert result.abort_reason == "error"