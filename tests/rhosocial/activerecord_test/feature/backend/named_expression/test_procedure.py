# tests/rhosocial/activerecord_test/feature/backend/named_expression/test_procedure.py
"""
Tests for named procedure functionality.

This test module covers:
- Procedure base class
- ProcedureContext methods (execute, scalar, rows, bind, log, abort)
- ProcedureRunner execution
- TransactionMode
"""
import types
from typing import List
from unittest.mock import MagicMock, patch
import pytest

from rhosocial.activerecord.backend.named_expression.procedure import (
    Procedure,
    ProcedureContext,
    ProcedureRunner,
    ProcedureResult,
    TransactionMode,
    LogEntry,
    AsyncProcedure,
    AsyncProcedureContext,
    AsyncProcedureRunner,
)
from rhosocial.activerecord.backend.named_expression.exceptions import (
    NamedExpressionError,
)
from rhosocial.activerecord.backend.named_expression.resolver import resolve_named_expression


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

        with pytest.raises(NamedExpressionError) as exc:
            ctx.abort("test_procedures.TestProc", "Test abort reason")
        assert "aborted" in str(exc.value).lower()


class TestProcedureRunnerInit:
    """Tests for ProcedureRunner.__init__()."""

    def test_valid_qualified_name(self):
        """Test initialization with valid qualified name."""
        runner = ProcedureRunner("myapp.procedures.monthly_report")
        assert runner.qualified_name == "myapp.procedures.monthly_report"

    def test_invalid_qualified_name_no_dot(self):
        """Test initialization fails without dot."""
        with pytest.raises(NamedExpressionError) as exc:
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
            with pytest.raises(NamedExpressionError) as exc:
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

    def test_run_simple_procedure(self, mock_dialect, mock_backend):
        """Test running a simple procedure."""
        module = types.ModuleType("test_procedures")

        class HelloProc(Procedure):
            name: str = "World"

            def run(self, ctx: ProcedureContext) -> None:
                ctx.log(f"Hello, {self.name}!")

        module.HelloProc = HelloProc

        with patch("importlib.import_module", return_value=module):
            runner = ProcedureRunner("test_procedures.HelloProc").load()
            result = runner.run(mock_backend, {"name": "Test"})

            assert len(result.logs) == 1
            assert "Hello, Test!" in result.logs[0].message

    def test_run_with_abort(self, mock_dialect, mock_backend):
        """Test running a procedure that aborts."""
        module = types.ModuleType("test_procedures")

        class AbortProc(Procedure):
            should_abort: bool = False

            def run(self, ctx: ProcedureContext) -> None:
                if self.should_abort:
                    ctx.abort("test_procedures.AbortProc", "Test abort")
                ctx.log("After abort")

        module.AbortProc = AbortProc

        with patch("importlib.import_module", return_value=module):
            runner = ProcedureRunner("test_procedures.AbortProc").load()
            result = runner.run(mock_backend, {"should_abort": True})

            assert result.aborted is True
            assert "Test abort" in str(result.abort_reason)

    def test_run_with_bind_and_rows(self, mock_dialect, mock_backend):
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
            result = runner.run(mock_backend, {})

            assert len(result.logs) == 1

    def test_run_rejects_async_backend(self, mock_dialect):
        """Test ProcedureRunner.run() rejects async backend."""
        from unittest.mock import MagicMock
        from rhosocial.activerecord.backend.named_expression import NamedExpressionError

        async_backend = MagicMock()
        async_backend.dialect = mock_dialect

        async def async_execute(sql, params, options):
            return MagicMock(data=[], affected_rows=0)

        async_backend.execute = async_execute

        module = types.ModuleType("test_procedures")

        class HelloProc(Procedure):
            name: str = "World"

            def run(self, ctx: ProcedureContext) -> None:
                ctx.log(f"Hello, {self.name}!")

        module.HelloProc = HelloProc

        with patch("importlib.import_module", return_value=module):
            runner = ProcedureRunner("test_procedures.HelloProc").load()
            with pytest.raises(NamedExpressionError) as exc_info:
                runner.run(async_backend, {"name": "Test"})
            assert "async execute method" in str(exc_info.value)
            assert "ProcedureRunner requires a sync backend" in str(exc_info.value)


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


class TestAsyncProcedureClass:
    """Tests for AsyncProcedure base class - structural tests."""

    def test_get_parameters(self):
        """Test getting parameter info from async class attributes."""

        class TestAsyncProcedure(AsyncProcedure):
            required_param: str
            optional_param: int = 10

        params = TestAsyncProcedure.get_parameters()
        assert "required_param" in params
        assert "optional_param" in params
        assert params["required_param"]["has_default"] is False
        assert params["optional_param"]["has_default"] is True

    def test_is_procedure_class(self):
        """Test that AsyncProcedure is a proper class."""
        assert isinstance(AsyncProcedure, type)


class TestAsyncProcedureContextInit:
    """Tests for AsyncProcedureContext initialization."""

    def test_init_with_defaults(self, mock_dialect):
        """Test initialization with default values."""
        ctx = AsyncProcedureContext(mock_dialect, lambda *a: None)

        assert ctx.dialect is mock_dialect
        assert ctx.bindings == {}


class TestAsyncProcedureRunnerInit:
    """Tests for AsyncProcedureRunner initialization."""

    def test_init_with_qualified_name(self):
        """Test initialization with valid qualified name."""
        runner = AsyncProcedureRunner("myapp.procedures.monthly_report")
        assert runner.qualified_name == "myapp.procedures.monthly_report"

    def test_qualified_name_inherited(self):
        """Test qualified_name property is available."""
        runner = AsyncProcedureRunner("test.proc")
        assert runner.qualified_name == "test.proc"


class TestAsyncProcedureRunnerRun:
    """Tests for AsyncProcedureRunner - structural parity with sync version."""

    def test_async_runner_load_method_exists(self):
        """Test AsyncProcedureRunner has load() method."""
        runner = AsyncProcedureRunner("test.proc")
        assert hasattr(runner, "load")

    def test_async_runner_describe_method_exists(self):
        """Test AsyncProcedureRunner has describe() method."""
        runner = AsyncProcedureRunner("test.proc")
        assert hasattr(runner, "describe")

    def test_async_runner_qualified_name_property(self):
        """Test AsyncProcedureRunner has qualified_name property."""
        runner = AsyncProcedureRunner("test.proc.monthly")
        assert runner.qualified_name == "test.proc.monthly"

    @pytest.mark.asyncio
    async def test_run_rejects_sync_backend(self):
        """Test AsyncProcedureRunner.run() rejects sync backend."""
        import asyncio
        from unittest.mock import MagicMock
        from rhosocial.activerecord.backend.named_expression import NamedExpressionError

        sync_backend = MagicMock()
        sync_backend.dialect = MagicMock()

        sync_backend.execute = MagicMock(return_value=MagicMock(data=[], affected_rows=0))

        module = types.ModuleType("test_procedures")

        class HelloProc(AsyncProcedure):
            name: str = "World"

            async def run(self, ctx: AsyncProcedureContext) -> None:
                ctx.log(f"Hello, {self.name}!")

        module.HelloProc = HelloProc

        with patch("importlib.import_module", return_value=module):
            runner = AsyncProcedureRunner("test_procedures.HelloProc").load()
            with pytest.raises(NamedExpressionError) as exc_info:
                await runner.run(sync_backend, {"name": "Test"})
            assert "sync execute method" in str(exc_info.value)
            assert "AsyncProcedureRunner requires an async backend" in str(exc_info.value)


class TestAsyncProcedureContextExecute:
    """Tests for AsyncProcedureContext - structural tests."""

    @pytest.fixture
    def mock_dialect(self):
        mock = MagicMock()
        mock.__class__.__name__ = "MockDialect"
        return mock

    def test_async_context_init_with_callback(self, mock_dialect):
        """Test AsyncProcedureContext supports async callback."""
        async def async_callback(fqn, dial, params):
            return {}

        ctx = AsyncProcedureContext(mock_dialect, async_callback)
        assert ctx.dialect is mock_dialect

    def test_async_context_bindings_attribute_exists(self, mock_dialect):
        """Test AsyncProcedureContext has bindings attribute."""
        async def async_callback(fqn, dial, params):
            return {}

        ctx = AsyncProcedureContext(mock_dialect, async_callback)
        assert hasattr(ctx, "bindings")

    def test_async_context_log_method_exists(self, mock_dialect):
        """Test AsyncProcedureContext has log() method."""
        async def async_callback(fqn, dial, params):
            return {}

        ctx = AsyncProcedureContext(mock_dialect, async_callback)
        assert hasattr(ctx, "log")

    def test_async_context_abort_method_exists(self, mock_dialect):
        """Test AsyncProcedureContext has abort() method."""
        async def async_callback(fqn, dial, params):
            return {}

        ctx = AsyncProcedureContext(mock_dialect, async_callback)
        assert hasattr(ctx, "abort")


class TestParallelStep:
    """Tests for ParallelStep dataclass."""

    def test_parallel_step_creation(self):
        """Test ParallelStep can be created."""
        from rhosocial.activerecord.backend.named_expression.procedure import ParallelStep

        step = ParallelStep("test.query", {"id": 1})
        assert step.qualified_name == "test.query"
        assert step.params == {"id": 1}

    def test_parallel_step_with_bind(self):
        """Test ParallelStep with bind parameter."""
        from rhosocial.activerecord.backend.named_expression.procedure import ParallelStep

        step = ParallelStep("test.query", {"id": 1}, bind="result", output=True)
        assert step.bind == "result"
        assert step.output is True

    def test_parallel_step_defaults(self):
        """Test ParallelStep has correct defaults."""
        from rhosocial.activerecord.backend.named_expression.procedure import ParallelStep

        step = ParallelStep("test.query")
        assert step.params == {}
        assert step.bind is None
        assert step.output is False


class TestTransactionModeStep:
    """Tests for TransactionMode.STEP behavior."""

    @pytest.fixture
    def mock_dialect(self):
        mock = MagicMock()
        mock.__class__.__name__ = "MockDialect"
        return mock

    @pytest.fixture
    def mock_backend(self):
        backend = MagicMock()
        backend.begin_transaction = MagicMock()
        backend.commit_transaction = MagicMock()
        backend.rollback_transaction = MagicMock()
        return backend

    def test_step_mode_executes_commit_after_each_execute(self, mock_dialect, mock_backend):
        """Test STEP mode calls commit after each execute.

        In STEP mode, ctx.execute() automatically calls begin_transaction before
        and commit_transaction after execution (if in transaction).
        """
        commit_called = []

        def execute_callback(fqn, dial, params):
            return {"data": [], "affected_rows": 0}

        def begin():
            pass

        def commit():
            commit_called.append(1)

        context = ProcedureContext(
            mock_dialect,
            execute_callback,
            TransactionMode.STEP,
            mock_backend,
        )
        context._begin_transaction = begin
        context._commit_transaction = commit
        context._in_transaction = True

        context.execute("test.query")

        assert commit_called


class TestBaseProcedureRunner:
    """Tests for _BaseProcedureRunner shared logic."""

    def test_base_runner_parses_qualified_name(self):
        """Test _BaseProcedureRunner parses qualified name."""
        from rhosocial.activerecord.backend.named_expression.procedure import (
            _BaseProcedureRunner,
        )

        runner = _BaseProcedureRunner("myapp.procedures.monthly_report")
        assert runner._module_name == "myapp.procedures"
        assert runner._class_name == "monthly_report"

    def test_base_runner_invalid_qualified_name(self):
        """Test invalid qualified name raises error."""
        from rhosocial.activerecord.backend.named_expression.procedure import (
            _BaseProcedureRunner,
        )
        from rhosocial.activerecord.backend.named_expression.exceptions import NamedExpressionError

        with pytest.raises(NamedExpressionError):
            _BaseProcedureRunner("invalid")

    def test_sync_runner_inherits_from_base(self):
        """Test ProcedureRunner inherits from _BaseProcedureRunner."""
        from rhosocial.activerecord.backend.named_expression.procedure import (
            ProcedureRunner,
            _BaseProcedureRunner,
        )

        assert issubclass(ProcedureRunner, _BaseProcedureRunner)

    def test_async_runner_inherits_from_base(self):
        """Test AsyncProcedureRunner inherits from _BaseProcedureRunner."""
        from rhosocial.activerecord.backend.named_expression.procedure import (
            AsyncProcedureRunner,
            _BaseProcedureRunner,
        )

        assert issubclass(AsyncProcedureRunner, _BaseProcedureRunner)


class TestProcedureContextParallel:
    """Tests for ProcedureContext.parallel method."""

    def test_parallel_empty_steps(self):
        """Test parallel with no steps returns empty list."""
        from rhosocial.activerecord.backend.named_expression.procedure import (
            ProcedureContext,
            ParallelStep,
        )

        mock_dialect = MagicMock()
        mock_dialect.name = "sqlite"

        def callback(fqn, dial, params):
            return {"result": "ok"}

        ctx = ProcedureContext(mock_dialect, callback)
        result = ctx.parallel()
        assert result == []

    def test_parallel_single_step(self):
        """Test parallel with single step."""
        from rhosocial.activerecord.backend.named_expression.procedure import (
            ProcedureContext,
            ParallelStep,
        )

        mock_dialect = MagicMock()
        mock_dialect.name = "sqlite"

        def callback(fqn, dial, params):
            return {"done": True}

        ctx = ProcedureContext(mock_dialect, callback)
        ctx._trace_index = 0
        ctx._backend = None

        step = ParallelStep("test.q1", {"a": 1})
        result = ctx.parallel(step, max_concurrency=1)

        assert len(result) == 1

    def test_parallel_multiple_steps_serial(self):
        """Test parallel with multiple steps (limit=1 forces serial)."""
        from rhosocial.activerecord.backend.named_expression.procedure import (
            ProcedureContext,
            ParallelStep,
        )

        mock_dialect = MagicMock()
        mock_dialect.name = "sqlite"

        results = []

        def callback(fqn, dial, params):
            results.append(fqn)
            return {"done": True}

        ctx = ProcedureContext(mock_dialect, callback)
        ctx._trace_index = 0

        step1 = ParallelStep("test.q1", {"a": 1})
        step2 = ParallelStep("test.q2", {"b": 2})
        result = ctx.parallel(step1, step2, max_concurrency=1)

        assert len(result) == 2

    def test_parallel_max_concurrency(self):
        """Test parallel respects max_concurrency."""
        from rhosocial.activerecord.backend.named_expression.procedure import (
            ProcedureContext,
            ParallelStep,
        )

        mock_dialect = MagicMock()
        mock_dialect.name = "sqlite"

        def callback(fqn, dial, params):
            return {"result": "ok"}

        ctx = ProcedureContext(mock_dialect, callback)
        ctx._trace_index = 0
        ctx._backend = MagicMock()

        ctx._backend.get_concurrency_limit = MagicMock(return_value=None)

        step1 = ParallelStep("test.q1", {"a": 1})
        step2 = ParallelStep("test.q2", {"b": 2})
        step3 = ParallelStep("test.q3", {"c": 3})
        result = ctx.parallel(step1, step2, step3, max_concurrency=2)

        assert len(result) == 3


class TestProcedureResultDiagram:
    """Tests for ProcedureResult.diagram method."""

    def test_procedure_result_diagram_flowchart(self):
        """Test ProcedureResult.diagram generates flowchart."""
        from rhosocial.activerecord.backend.named_expression.procedure import (
            ProcedureResult,
            TraceEntry,
            StepKind,
        )

        result = ProcedureResult()
        result.static_trace.append(TraceEntry(
            kind=StepKind.SINGLE,
            index=0,
            qualified_name="test.query",
            params={"id": 1},
            status="ok",
        ))

        diagram = result.diagram("flowchart")
        assert "flowchart" in diagram.lower() or "graph" in diagram.lower()

    def test_procedure_result_diagram_sequence(self):
        """Test ProcedureResult.diagram generates sequence diagram."""
        from rhosocial.activerecord.backend.named_expression.procedure import (
            ProcedureResult,
            TraceEntry,
            StepKind,
        )

        result = ProcedureResult()
        result.static_trace.append(TraceEntry(
            kind=StepKind.SINGLE,
            index=0,
            qualified_name="test.query",
            params={"id": 1},
            status="ok",
        ))

        diagram = result.diagram("sequence")
        assert "sequence" in diagram.lower() or "participant" in diagram.lower()


class TestProcedureStaticDiagram:
    """Tests for Procedure.static_diagram class method."""

    def test_static_diagram_flowchart(self):
        """Test Procedure.static_diagram generates flowchart."""
        from rhosocial.activerecord.backend.named_expression.procedure import Procedure

        diagram = Procedure.static_diagram("flowchart", dialect=None)
        assert diagram is not None
        assert len(diagram) > 0

    def test_static_diagram_sequence(self):
        """Test Procedure.static_diagram generates sequence diagram."""
        from rhosocial.activerecord.backend.named_expression.procedure import Procedure

        diagram = Procedure.static_diagram("sequence", dialect=None)
        assert diagram is not None
        assert len(diagram) > 0

    def test_static_diagram_invalid_kind(self):
        """Test static_diagram with invalid kind raises."""
        from rhosocial.activerecord.backend.named_expression.procedure import Procedure

        with pytest.raises(ValueError, match="Unknown diagram kind"):
            Procedure.static_diagram("invalid_kind", dialect=None)


class TestAsyncProcedureContextParallel:
    """Tests for AsyncProcedureContext.parallel method."""

    @pytest.mark.asyncio
    async def test_async_parallel_empty_steps(self):
        """Test async parallel with no steps returns empty list."""
        from rhosocial.activerecord.backend.named_expression.procedure import (
            AsyncProcedureContext,
            ParallelStep,
        )

        mock_dialect = MagicMock()
        mock_dialect.name = "sqlite"

        async def callback(fqn, dial, params):
            return {"result": "ok"}

        ctx = AsyncProcedureContext(mock_dialect, callback)
        result = await ctx.parallel()
        assert result == []

    @pytest.mark.asyncio
    async def test_async_parallel_multiple_steps(self):
        """Test async parallel with multiple steps."""
        from rhosocial.activerecord.backend.named_expression.procedure import (
            AsyncProcedureContext,
            ParallelStep,
        )

        mock_dialect = MagicMock()
        mock_dialect.name = "sqlite"

        results = []

        async def callback(fqn, dial, params):
            results.append(fqn)
            return {"done": True}

        ctx = AsyncProcedureContext(mock_dialect, callback)

        step1 = ParallelStep("test.q1", {"a": 1})
        step2 = ParallelStep("test.q2", {"b": 2})
        result = await ctx.parallel(step1, step2, max_concurrency=1)

        assert len(result) == 2


class TestProcedureGetParameters:
    """Tests for Procedure.get_parameters class method."""

    def test_get_parameters_required_only(self):
        """Test get_parameters with required parameters only."""
        from rhosocial.activerecord.backend.named_expression.procedure import Procedure

        class MonthlyReport(Procedure):
            month: str
            year: int

        params = MonthlyReport.get_parameters()
        assert "month" in params
        assert "year" in params
        assert params["month"]["has_default"] is False
        assert params["year"]["has_default"] is False

    def test_get_parameters_with_defaults(self):
        """Test get_parameters with optional parameters."""
        from rhosocial.activerecord.backend.named_expression.procedure import Procedure

        class ConfigProcedure(Procedure):
            enabled: bool = True
            limit: int = 100

        params = ConfigProcedure.get_parameters()
        assert "enabled" in params
        assert "limit" in params
        assert params["enabled"]["has_default"] is True
        assert params["limit"]["has_default"] is True


class TestAsyncProcedureGetParameters:
    """Tests for AsyncProcedure.get_parameters class method."""

    def test_async_procedure_get_parameters(self):
        """Test AsyncProcedure.get_parameters works."""
        from rhosocial.activerecord.backend.named_expression.procedure import AsyncProcedure

        class AsyncReport(AsyncProcedure):
            month: str
            limit: int = 50

        params = AsyncReport.get_parameters()
        assert "month" in params
        assert "limit" in params
        assert params["month"]["has_default"] is False
        assert params["limit"]["has_default"] is True


class TestResolveConcurrency:
    """Tests for _resolve_concurrency helper."""

    def test_resolve_concurrency_user_override(self):
        """Test user max_concurrency overrides backend hint."""
        from rhosocial.activerecord.backend.named_expression.procedure import (
            _resolve_concurrency,
        )

        result = _resolve_concurrency(None, 5)
        assert result == 5

    def test_resolve_concurrency_no_backend(self):
        """Test returns None when no backend."""
        from rhosocial.activerecord.backend.named_expression.procedure import (
            _resolve_concurrency,
        )

        result = _resolve_concurrency(None, None)
        assert result is None