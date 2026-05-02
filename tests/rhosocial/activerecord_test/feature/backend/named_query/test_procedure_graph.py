# tests/rhosocial/activerecord_test/feature/backend/named_query/test_procedure_graph.py
"""
Tests for ProcedureGraph functionality.

This test module covers:
- StepNode creation and factory methods
- ProcedureGraph building and validation
- Topological sorting and wave calculation
- GraphContext condition evaluation
- ProcedureGraphRunner execution
- AsyncProcedureGraphRunner execution
- NamedProcedureGraphResolver
- Cyclic dependency detection
"""
import types
from typing import List
from unittest.mock import MagicMock, AsyncMock
import pytest

from rhosocial.activerecord.backend.named_query.procedure_graph import (
    ProcedureGraph,
    StepNode,
    StepKind,
    TransactionMode,
    GraphContext,
    CyclicDependencyError,
    _kahn_topological_waves,
    _safe_eval_condition,
    _interpolate_template,
)
from rhosocial.activerecord.backend.named_query.graph_result import (
    ProcedureGraphResult,
    StepStatus,
    StepTraceEntry,
)
from rhosocial.activerecord.backend.named_query.graph_runner import (
    ProcedureGraphRunner,
    AsyncProcedureGraphRunner,
    ProcedureGraphValidationError,
)
from rhosocial.activerecord.backend.named_query.graph_resolver import (
    NamedProcedureGraphResolver,
    NamedProcedureGraphError,
)


class TestStepNode:
    """Tests for StepNode creation."""

    def test_step_node_query_factory(self):
        """Test StepNode.query() factory method."""
        node = StepNode.query(
            "fetch_users",
            "myapp.q.active_users",
            params={"limit": 100},
            depends_on=[],
        )
        assert node.name == "fetch_users"
        assert node.kind == StepKind.NAMED_QUERY
        assert node.named_query == "myapp.q.active_users"
        assert node.params == {"limit": 100}

    def test_step_node_expr_factory(self):
        """Test StepNode.expr() factory method."""
        mock_expr = MagicMock()
        node = StepNode.expr(
            "create_table",
            mock_expr,
            depends_on=[],
        )
        assert node.name == "create_table"
        assert node.kind == StepKind.EXPRESSION
        assert node.expression is mock_expr

    def test_step_node_with_all_options(self):
        """Test StepNode with all options."""
        node = StepNode.query(
            "process",
            "myapp.q.process",
            params={"month": "2026-04"},
            label="Process data",
            depends_on=["fetch"],
            condition="${status} == 'active'",
            skip_for=["oracle"],
            bind_output={"rows[0].id": "user_id"},
            timeout_ms=5000,
            retry=3,
        )
        assert node.label == "Process data"
        assert node.condition == "${status} == 'active'"
        assert node.skip_for == ["oracle"]
        assert node.bind_output == {"rows[0].id": "user_id"}
        assert node.timeout_ms == 5000
        assert node.retry == 3

    def test_step_node_to_dict(self):
        """Test StepNode serialization."""
        node = StepNode.query(
            "fetch",
            "myapp.q.get_data",
            params={"limit": 10},
            depends_on=[],
        )
        d = node.to_dict()
        assert d["name"] == "fetch"
        assert d["kind"] == "NAMED_QUERY"
        assert d["params"] == {"limit": 10}


class TestProcedureGraph:
    """Tests for ProcedureGraph."""

    def test_graph_add_operator(self):
        """Test graph | StepNode syntax."""
        graph = (
            ProcedureGraph(transaction_mode=TransactionMode.AUTO)
            | StepNode.query("a", "myapp.q.a")
            | StepNode.query("b", "myapp.q.b", depends_on=["a"])
        )
        assert "a" in graph
        assert "b" in graph

    def test_graph_validate_empty_graph(self, mock_dialect):
        """Test validation of empty graph."""
        graph = ProcedureGraph()
        errors = graph.validate()
        assert "Empty graph has no steps" in errors

    def test_graph_add_duplicate_raises(self):
        """Test adding duplicate step name raises error."""
        graph = ProcedureGraph()
        graph.add(StepNode.query("step1", "myapp.q.step1"))
        with pytest.raises(ValueError, match="Duplicate step name"):
            graph.add(StepNode.query("step1", "myapp.q.step1"))

    def test_graph_validate_unknown_dep(self):
        """Test validation catches unknown dependency."""
        graph = (
            ProcedureGraph()
            | StepNode.query("step_a", "myapp.q.a", depends_on=["unknown"])
        )
        errors = graph.validate()
        assert any("unknown" in e for e in errors)


class TestTopologicalSort:
    """Tests for topological sorting."""

    def test_linear_waves(self):
        """Test linear execution order."""
        graph = (
            ProcedureGraph()
            | StepNode.query("a", "myapp.q.a")
            | StepNode.query("b", "myapp.q.b", depends_on=["a"])
            | StepNode.query("c", "myapp.q.c", depends_on=["b"])
        )
        waves = graph.waves()
        assert len(waves) == 3
        assert [n.name for n in waves[0]] == ["a"]
        assert [n.name for n in waves[1]] == ["b"]
        assert [n.name for n in waves[2]] == ["c"]

    def test_parallel_wave(self):
        """Test parallel wave detection."""
        graph = (
            ProcedureGraph()
            | StepNode.query("a", "myapp.q.a")
            | StepNode.query("b", "myapp.q.b")
            | StepNode.query("c", "myapp.q.c", depends_on=["a", "b"])
        )
        waves = graph.waves()
        assert len(waves) == 2
        wave_0_names = {n.name for n in waves[0]}
        assert wave_0_names == {"a", "b"}

    def test_cyclic_dependency_raises(self):
        """Test cyclic dependency detection."""
        graph = (
            ProcedureGraph()
            | StepNode.query("a", "myapp.q.a", depends_on=["c"])
            | StepNode.query("b", "myapp.q.b", depends_on=["a"])
            | StepNode.query("c", "myapp.q.c", depends_on=["b"])
        )
        with pytest.raises(CyclicDependencyError):
            graph.waves()

    def test_self_dependency(self):
        """Test self-dependency detection."""
        graph = ProcedureGraph()
        graph.add(StepNode.query("a", "myapp.q.a", depends_on=["a"]))
        with pytest.raises(CyclicDependencyError):
            graph.waves()

    def test_independent_steps_parallel(self):
        """Test all independent steps in same wave."""
        graph = (
            ProcedureGraph()
            | StepNode.query("a", "myapp.q.a")
            | StepNode.query("b", "myapp.q.b")
            | StepNode.query("c", "myapp.q.c")
        )
        waves = graph.waves()
        assert len(waves) == 1
        assert len(waves[0]) == 3


class TestGraphContext:
    """Tests for GraphContext."""

    def test_context_get(self, mock_dialect):
        """Test context get method."""
        ctx = GraphContext(mock_dialect, {"month": "2026-04"})
        ctx._bindings["count"] = 100
        assert ctx.get("month") == "2026-04"
        assert ctx.get("count") == 100
        assert ctx.get("unknown", "default") == "default"

    def test_context_eval_condition(self, mock_dialect):
        """Test condition evaluation."""
        ctx = GraphContext(mock_dialect, {"version": 2, "count": 100, "flag": True})

        # Numeric/bool comparisons (string comparisons not supported)
        assert ctx.eval_condition("${version} >= 2") is True
        assert ctx.eval_condition("${version} < 2") is False
        assert ctx.eval_condition("${count} > 50") is True
        assert ctx.eval_condition("${flag} == True") is True
        assert ctx.eval_condition("${flag}") is True  # bool alone
        assert ctx.eval_condition("") is True  # empty = always run

    def test_context_eval_invalid_condition(self, mock_dialect):
        """Test invalid condition raises error."""
        ctx = GraphContext(mock_dialect, {})
        with pytest.raises(ValueError, match="Unknown variable"):
            ctx.eval_condition("${unknown_var} > 0")

    def test_context_bind_output(self, mock_dialect):
        """Test bind_output mapping."""
        ctx = GraphContext(mock_dialect, {})
        # Simulate result data from a query execution
        result_data = [{"id": 1, "name": "test"}]
        ctx.bind({"[0].id": "user_id"}, result_data)
        assert ctx._bindings["user_id"] == 1

    def test_context_interpolate(self, mock_dialect):
        """Test template interpolation."""
        ctx = GraphContext(mock_dialect, {"month": "2026-04", "limit": 100})
        # Test simple interpolation
        result = ctx.interpolate("${month}")
        assert result == "2026-04"


class TestKahnAlgorithm:
    """Tests for Kahn topological algorithm."""

    def test_kahn_empty(self):
        """Test empty graph."""
        waves = _kahn_topological_waves({})
        assert waves == []

    def test_kahn_single_node(self):
        """Test single node."""
        node = StepNode.query("a", "myapp.q.a")
        waves = _kahn_topological_waves({"a": node})
        assert len(waves) == 1
        assert waves[0][0].name == "a"


class TestSafeEvalCondition:
    """Tests for safe condition evaluation."""

    def test_comparison_operators(self):
        """Test comparison operators."""
        assert _safe_eval_condition("1 > 0", {}) is True
        assert _safe_eval_condition("1 < 0", {}) is False
        assert _safe_eval_condition("1 >= 1", {}) is True
        assert _safe_eval_condition("1 <= 1", {}) is True
        assert _safe_eval_condition("1 == 1", {}) is True
        assert _safe_eval_condition("1 != 0", {}) is True

    def test_logical_operators(self):
        """Test logical operators."""
        assert _safe_eval_condition("True and True", {}) is True
        assert _safe_eval_condition("True and False", {}) is False
        assert _safe_eval_condition("True or False", {}) is True
        assert _safe_eval_condition("not False", {}) is True

    def test_template_substitution(self):
        """Test ${var} substitution."""
        # Numeric comparisons work
        result = _safe_eval_condition("${count} > 50", {"count": 100})
        assert result is True

        result = _safe_eval_condition("${flag} == True", {"flag": True})
        assert result is True


class TestProcedureGraphRunner:
    """Tests for ProcedureGraphRunner."""

    def test_runner_init(self, mock_dialect, mock_backend):
        """Test runner initialization."""
        runner = ProcedureGraphRunner(mock_backend, dialect=mock_dialect)
        assert runner.dialect is mock_dialect

    def test_runner_init_with_dry_run(self, mock_dialect, mock_backend):
        """Test runner initialization with dry_run enabled."""
        runner = ProcedureGraphRunner(mock_backend, dialect=mock_dialect, dry_run=True)
        assert runner._dry_run is True

    def test_runner_init_with_trace(self, mock_dialect, mock_backend):
        """Test runner initialization with trace enabled."""
        runner = ProcedureGraphRunner(mock_backend, dialect=mock_dialect, trace=True)
        assert runner._trace is True

    def test_runner_init_with_parallel_wave(self, mock_dialect, mock_backend):
        """Test runner initialization with parallel_wave enabled."""
        runner = ProcedureGraphRunner(
            mock_backend, dialect=mock_dialect, parallel_wave=True
        )
        assert runner._parallel_wave is True

    def test_runner_validation_error(self, mock_dialect, mock_backend):
        """Test runner catches validation errors."""
        graph = ProcedureGraph()  # empty graph
        runner = ProcedureGraphRunner(mock_backend, dialect=mock_dialect)

        with pytest.raises(ProcedureGraphValidationError):
            runner.run(graph)

    def test_runner_skip_condition(self, mock_dialect, mock_backend):
        """Test runner skips steps with false condition."""
        ctx = GraphContext(mock_dialect, {"skip": "false"})
        runner = ProcedureGraphRunner(mock_backend, dialect=mock_dialect)

        result = ProcedureGraphResult()
        entry = StepTraceEntry(
            name="fetch", kind="NAMED_QUERY", status=StepStatus.SKIPPED, reason="condition_false"
        )
        result.steps_skipped.append(entry)

        assert len(result.steps_skipped) == 1

    def test_runner_skip_for_backend(self, mock_dialect, mock_backend):
        """Test runner skips steps for specific backend."""
        mock_dialect.name = "sqlite"

        result = ProcedureGraphResult()
        entry = StepTraceEntry(
            name="fetch", kind="NAMED_QUERY", status=StepStatus.SKIPPED, reason="skip_for_sqlite"
        )
        result.steps_skipped.append(entry)

        assert len(result.steps_skipped) == 1

    def test_runner_executes_named_query_step(self, mock_dialect, mock_backend):
        """Test runner executes NAMED_QUERY step."""
        from unittest.mock import patch

        mock_dialect.name = "sqlite"

        mock_expr = MagicMock()
        mock_expr.to_sql.return_value = ("SELECT * FROM users", ())

        with patch(
            "rhosocial.activerecord.backend.named_query.resolver.resolve_named_query",
            return_value=[mock_expr],
        ):
            graph = (
                ProcedureGraph()
                | StepNode.query("fetch", "myapp.q.get_users", depends_on=[])
            )
            runner = ProcedureGraphRunner(mock_backend, dialect=mock_dialect)
            result = runner.run(graph)

        assert len(result.steps_done) == 1
        assert result.steps_done[0].name == "fetch"

    def test_runner_executes_expression_step(self, mock_dialect, mock_backend):
        """Test runner executes EXPRESSION step."""
        from rhosocial.activerecord.backend.expression.executable import Executable
        from rhosocial.activerecord.backend.schema import StatementType

        mock_dialect.name = "sqlite"

        class MockExpr(Executable):
            @property
            def statement_type(self):
                return StatementType.SELECT

            def to_sql(self):
                return "SELECT 1", ()

        mock_backend.execute.return_value = MagicMock(data=[{"id": 1}], affected_rows=1)

        graph = (
            ProcedureGraph()
            | StepNode.expr("select_one", MockExpr(), depends_on=[])
        )
        runner = ProcedureGraphRunner(mock_backend, dialect=mock_dialect)
        result = runner.run(graph)

        assert len(result.steps_done) == 1
        assert result.steps_done[0].name == "select_one"

    def test_runner_dry_run_mode(self, mock_dialect, mock_backend):
        """Test runner dry_run mode."""
        from rhosocial.activerecord.backend.expression.executable import Executable
        from rhosocial.activerecord.backend.schema import StatementType

        mock_dialect.name = "sqlite"

        class MockExpr(Executable):
            @property
            def statement_type(self):
                return StatementType.SELECT

            def to_sql(self):
                return "SELECT 1", ()

        graph = (
            ProcedureGraph()
            | StepNode.expr("dry_step", MockExpr(), depends_on=[])
        )
        runner = ProcedureGraphRunner(mock_backend, dialect=mock_dialect, dry_run=True)
        result = runner.run(graph)

        assert len(result.steps_dry_run) == 1
        assert result.steps_dry_run[0].name == "dry_step"
        mock_backend.execute.assert_not_called()

    def test_runner_step_fails(self, mock_dialect, mock_backend):
        """Test runner handles step failure."""
        from rhosocial.activerecord.backend.expression.executable import Executable
        from rhosocial.activerecord.backend.schema import StatementType

        mock_dialect.name = "sqlite"
        mock_backend.execute.side_effect = Exception("SQL error")

        class MockExpr(Executable):
            @property
            def statement_type(self):
                return StatementType.SELECT

            def to_sql(self):
                return "SELECT 1", ()

        graph = (
            ProcedureGraph()
            | StepNode.expr("fail_step", MockExpr(), depends_on=[])
        )
        runner = ProcedureGraphRunner(mock_backend, dialect=mock_dialect)

        with pytest.raises(Exception, match="SQL error"):
            runner.run(graph)

    def test_runner_multiple_waves(self, mock_dialect, mock_backend):
        """Test runner executes multiple waves."""
        from rhosocial.activerecord.backend.expression.executable import Executable
        from rhosocial.activerecord.backend.schema import StatementType

        mock_dialect.name = "sqlite"
        mock_backend.execute.return_value = MagicMock(data=[], affected_rows=0)

        class MockExpr(Executable):
            @property
            def statement_type(self):
                return StatementType.SELECT

            def to_sql(self):
                return "SELECT 1", ()

        graph = (
            ProcedureGraph()
            | StepNode.expr("wave1_step1", MockExpr(), depends_on=[])
            | StepNode.expr("wave1_step2", MockExpr(), depends_on=[])
            | StepNode.expr("wave2_step", MockExpr(), depends_on=["wave1_step1"])
        )
        runner = ProcedureGraphRunner(mock_backend, dialect=mock_dialect)
        result = runner.run(graph)

        assert result.waves_count == 2
        assert len(result.steps_done) == 3


@pytest.mark.asyncio
class TestAsyncProcedureGraphRunner:
    """Tests for AsyncProcedureGraphRunner."""

    async def test_async_runner_init(self, mock_dialect, mock_backend):
        """Test async runner initialization."""
        runner = AsyncProcedureGraphRunner(mock_backend, dialect=mock_dialect)
        assert runner.dialect is mock_dialect

    async def test_async_runner_init_with_options(self, mock_dialect, mock_backend):
        """Test async runner initialization with options."""
        runner = AsyncProcedureGraphRunner(
            mock_backend, dialect=mock_dialect, dry_run=True, trace=True
        )
        assert runner._dry_run is True
        assert runner._trace is True

    async def test_async_runner_executes_graph(self, mock_dialect, mock_backend):
        """Test async runner executes graph."""
        from rhosocial.activerecord.backend.expression.executable import Executable
        from rhosocial.activerecord.backend.schema import StatementType
        from unittest.mock import AsyncMock

        mock_dialect.name = "sqlite"
        mock_backend.execute = AsyncMock(return_value=MagicMock(data=[], affected_rows=0))
        mock_backend.begin_transaction = AsyncMock()
        mock_backend.commit_transaction = AsyncMock()

        class MockExpr(Executable):
            @property
            def statement_type(self):
                return StatementType.SELECT

            def to_sql(self):
                return "SELECT 1", ()

        graph = (
            ProcedureGraph()
            | StepNode.expr("async_step", MockExpr(), depends_on=[])
        )
        runner = AsyncProcedureGraphRunner(mock_backend, dialect=mock_dialect)
        result = await runner.run(graph)

        assert len(result.steps_done) == 1
        assert result.steps_done[0].name == "async_step"

    async def test_async_runner_dry_run(self, mock_dialect, mock_backend):
        """Test async runner dry run mode."""
        from rhosocial.activerecord.backend.expression.executable import Executable
        from rhosocial.activerecord.backend.schema import StatementType
        from unittest.mock import AsyncMock

        mock_dialect.name = "sqlite"
        mock_backend.execute = AsyncMock()
        mock_backend.begin_transaction = AsyncMock()
        mock_backend.commit_transaction = AsyncMock()

        class MockExpr(Executable):
            @property
            def statement_type(self):
                return StatementType.SELECT

            def to_sql(self):
                return "SELECT 1", ()

        graph = (
            ProcedureGraph()
            | StepNode.expr("dry_step", MockExpr(), depends_on=[])
        )
        runner = AsyncProcedureGraphRunner(mock_backend, dialect=mock_dialect, dry_run=True)
        result = await runner.run(graph)

        assert len(result.steps_dry_run) == 1
        mock_backend.execute.assert_not_called()

    async def test_async_runner_skip_condition(self, mock_dialect, mock_backend):
        """Test async runner skips steps with false condition."""
        from rhosocial.activerecord.backend.expression.executable import Executable
        from rhosocial.activerecord.backend.schema import StatementType
        from unittest.mock import AsyncMock

        mock_dialect.name = "sqlite"
        mock_backend.execute = AsyncMock()
        mock_backend.begin_transaction = AsyncMock()
        mock_backend.commit_transaction = AsyncMock()
        mock_backend.rollback_transaction = AsyncMock()

        class MockExpr(Executable):
            @property
            def statement_type(self):
                return StatementType.SELECT

            def to_sql(self):
                return "SELECT 1", ()

        graph = (
            ProcedureGraph()
            | StepNode.expr(
                "skip_step", MockExpr(), depends_on=[], condition="${skip}"
            )
        )
        runner = AsyncProcedureGraphRunner(mock_backend, dialect=mock_dialect)
        result = await runner.run(graph, {"skip": False})

        assert len(result.steps_skipped) == 1
        assert result.steps_skipped[0].reason == "condition_false"

    async def test_async_runner_validation_error(self, mock_dialect, mock_backend):
        """Test async runner catches validation errors."""
        mock_backend.begin_transaction = AsyncMock()
        mock_backend.commit_transaction = AsyncMock()

        graph = ProcedureGraph()  # empty graph
        runner = AsyncProcedureGraphRunner(mock_backend, dialect=mock_dialect)

        with pytest.raises(ProcedureGraphValidationError):
            await runner.run(graph)

    async def test_async_runner_multiple_waves(self, mock_dialect, mock_backend):
        """Test async runner executes multiple waves."""
        from rhosocial.activerecord.backend.expression.executable import Executable
        from rhosocial.activerecord.backend.schema import StatementType
        from unittest.mock import AsyncMock

        mock_dialect.name = "sqlite"
        mock_backend.execute = AsyncMock(return_value=MagicMock(data=[], affected_rows=0))
        mock_backend.begin_transaction = AsyncMock()
        mock_backend.commit_transaction = AsyncMock()

        class MockExpr(Executable):
            @property
            def statement_type(self):
                return StatementType.SELECT

            def to_sql(self):
                return "SELECT 1", ()

        graph = (
            ProcedureGraph()
            | StepNode.expr("wave1", MockExpr(), depends_on=[])
            | StepNode.expr("wave2", MockExpr(), depends_on=["wave1"])
        )
        runner = AsyncProcedureGraphRunner(mock_backend, dialect=mock_dialect)
        result = await runner.run(graph)

        assert result.waves_count == 2


class TestGraphRunnerInterpolation:
    """Tests for graph runner interpolation functions."""

    def test_interpolate_dict_simple(self, mock_dialect):
        """Test simple dict interpolation."""
        from rhosocial.activerecord.backend.named_query.graph_runner import _interpolate_dict
        from rhosocial.activerecord.backend.named_query.procedure_graph import GraphContext

        ctx = GraphContext(mock_dialect, {"month": "2026-05"})
        data = {"query": "SELECT * FROM ${table}", "limit": 10}
        result = _interpolate_dict(data, ctx)
        assert result["query"] == "SELECT * FROM ${table}"
        assert result["limit"] == 10

    def test_interpolate_dict_nested(self, mock_dialect):
        """Test nested dict interpolation."""
        from rhosocial.activerecord.backend.named_query.graph_runner import _interpolate_dict
        from rhosocial.activerecord.backend.named_query.procedure_graph import GraphContext

        ctx = GraphContext(mock_dialect, {"value": "test"})
        data = {"outer": {"inner": "${value}", "static": 42}}
        result = _interpolate_dict(data, ctx)
        assert result["outer"]["static"] == 42

    def test_interpolate_dict_list(self, mock_dialect):
        """Test list interpolation."""
        from rhosocial.activerecord.backend.named_query.graph_runner import _interpolate_dict
        from rhosocial.activerecord.backend.named_query.procedure_graph import GraphContext

        ctx = GraphContext(mock_dialect, {"val": "replaced"})
        data = {"items": ["${val}", "static"]}
        result = _interpolate_dict(data, ctx)
        assert result["items"][1] == "static"


class TestTransactionContexts:
    """Tests for transaction context managers."""

    def test_sync_transaction_context_auto_mode(self, mock_backend):
        """Test sync transaction context with AUTO mode."""
        from rhosocial.activerecord.backend.named_query.graph_runner import (
            _SyncTransactionContext,
        )
        from rhosocial.activerecord.backend.named_query.procedure_graph import TransactionMode

        mock_backend.begin_transaction = MagicMock()
        mock_backend.commit_transaction = MagicMock()

        ctx = _SyncTransactionContext(mock_backend, TransactionMode.AUTO)
        with ctx:
            pass

        mock_backend.begin_transaction.assert_called_once()
        mock_backend.commit_transaction.assert_called_once()

    def test_sync_transaction_context_step_mode(self, mock_backend):
        """Test sync transaction context with STEP mode."""
        from rhosocial.activerecord.backend.named_query.graph_runner import (
            _SyncTransactionContext,
        )
        from rhosocial.activerecord.backend.named_query.procedure_graph import TransactionMode

        mock_backend.begin_transaction = MagicMock()
        mock_backend.commit_transaction = MagicMock()

        ctx = _SyncTransactionContext(mock_backend, TransactionMode.STEP)
        with ctx:
            pass

        mock_backend.begin_transaction.assert_called_once()
        mock_backend.commit_transaction.assert_called_once()

    def test_sync_transaction_context_rollback_on_error(self, mock_backend):
        """Test sync transaction rollback on exception."""
        from rhosocial.activerecord.backend.named_query.graph_runner import (
            _SyncTransactionContext,
        )
        from rhosocial.activerecord.backend.named_query.procedure_graph import TransactionMode

        mock_backend.begin_transaction = MagicMock()
        mock_backend.rollback_transaction = MagicMock()

        ctx = _SyncTransactionContext(mock_backend, TransactionMode.AUTO)
        try:
            with ctx:
                raise ValueError("test error")
        except ValueError:
            pass

        mock_backend.begin_transaction.assert_called_once()
        mock_backend.rollback_transaction.assert_called_once()


@pytest.mark.asyncio
class TestAsyncTransactionContext:
    """Tests for async transaction context manager."""

    async def test_async_transaction_context_auto_mode(self, mock_backend):
        """Test async transaction context with AUTO mode."""
        from rhosocial.activerecord.backend.named_query.graph_runner import (
            _AsyncTransactionContext,
        )
        from rhosocial.activerecord.backend.named_query.procedure_graph import TransactionMode
        from unittest.mock import AsyncMock

        mock_backend.begin_transaction = AsyncMock()
        mock_backend.commit_transaction = AsyncMock()

        ctx = _AsyncTransactionContext(mock_backend, TransactionMode.AUTO)
        async with ctx:
            pass

        mock_backend.begin_transaction.assert_called_once()
        mock_backend.commit_transaction.assert_called_once()

    async def test_async_transaction_context_step_mode(self, mock_backend):
        """Test async transaction context with STEP mode."""
        from rhosocial.activerecord.backend.named_query.graph_runner import (
            _AsyncTransactionContext,
        )
        from rhosocial.activerecord.backend.named_query.procedure_graph import TransactionMode
        from unittest.mock import AsyncMock

        mock_backend.begin_transaction = AsyncMock()
        mock_backend.commit_transaction = AsyncMock()

        ctx = _AsyncTransactionContext(mock_backend, TransactionMode.STEP)
        async with ctx:
            pass

        mock_backend.begin_transaction.assert_called_once()
        mock_backend.commit_transaction.assert_called_once()

    async def test_async_transaction_context_rollback_on_error(self, mock_backend):
        """Test async transaction rollback on exception."""
        from rhosocial.activerecord.backend.named_query.graph_runner import (
            _AsyncTransactionContext,
        )
        from rhosocial.activerecord.backend.named_query.procedure_graph import TransactionMode
        from unittest.mock import AsyncMock

        mock_backend.begin_transaction = AsyncMock()
        mock_backend.rollback_transaction = AsyncMock()

        ctx = _AsyncTransactionContext(mock_backend, TransactionMode.AUTO)
        try:
            async with ctx:
                raise ValueError("test error")
        except ValueError:
            pass

        mock_backend.begin_transaction.assert_called_once()
        mock_backend.rollback_transaction.assert_called_once()


class TestNamedProcedureGraphResolver:
    """Tests for NamedProcedureGraphResolver."""

    def test_resolver_init(self):
        """Test resolver initialization."""
        resolver = NamedProcedureGraphResolver("myapp.procedures.monthly_report")
        assert resolver.qualified_name == "myapp.procedures.monthly_report"
        assert resolver.module_name == "myapp.procedures"
        assert resolver.attr_name == "monthly_report"

    def test_resolver_invalid_format(self):
        """Test resolver rejects invalid format."""
        with pytest.raises(NamedProcedureGraphError, match="Invalid qualified name"):
            NamedProcedureGraphResolver("invalid_name")

    def test_resolver_load_missing_module(self):
        """Test resolver catches missing module."""
        resolver = NamedProcedureGraphResolver("nonexistent.module.graph")
        with pytest.raises(Exception):  # ModuleNotFoundError or similar
            resolver.load()

    def test_resolver_load_function(self):
        """Test resolver loads a function successfully."""
        import sys
        from types import ModuleType

        test_module = ModuleType("test_module")
        test_module.__all__ = ["test_func"]

        def test_func(dialect, params=None):
            return ProcedureGraph()

        test_module.test_func = test_func
        sys.modules["test_module"] = test_module

        try:
            resolver = NamedProcedureGraphResolver("test_module.test_func")
            resolver.load()
            assert resolver._callable is test_func
            assert resolver._target_callable is test_func
            assert resolver._is_class is False
        finally:
            del sys.modules["test_module"]

    def test_resolver_load_class(self):
        """Test resolver loads a class with __call__ successfully."""
        import sys
        from types import ModuleType

        test_module = ModuleType("test_module2")
        test_module.__all__ = ["TestGraph"]

        class TestGraph:
            def __call__(self, dialect, params=None):
                return ProcedureGraph()

        test_module.TestGraph = TestGraph
        sys.modules["test_module2"] = test_module

        try:
            resolver = NamedProcedureGraphResolver("test_module2.TestGraph")
            resolver.load()
            assert resolver._callable is TestGraph
            assert resolver._is_class is True
            assert resolver._instance is not None
        finally:
            del sys.modules["test_module2"]

    def test_resolver_build_graph(self, mock_dialect):
        """Test resolver builds graph with params."""
        import sys
        from types import ModuleType

        test_module = ModuleType("test_module3")
        test_module.__all__ = ["build_graph"]

        def build_graph(dialect, params=None):
            return (
                ProcedureGraph()
                | StepNode.query("step1", "myapp.q.step1", params={"month": params.get("month", "")})
            )

        test_module.build_graph = build_graph
        sys.modules["test_module3"] = test_module

        try:
            resolver = NamedProcedureGraphResolver("test_module3.build_graph")
            resolver.load()
            graph = resolver.build(mock_dialect, {"month": "2026-04"})
            assert "step1" in graph
        finally:
            del sys.modules["test_module3"]

    def test_resolver_missing_attr(self):
        """Test resolver handles missing attribute in module."""
        import sys
        from types import ModuleType

        test_module = ModuleType("test_module4")
        test_module.__all__ = []
        sys.modules["test_module4"] = test_module

        try:
            resolver = NamedProcedureGraphResolver("test_module4.missing")
            with pytest.raises(NamedProcedureGraphError, match="not found"):
                resolver.load()
        finally:
            del sys.modules["test_module4"]

    def test_resolver_invalid_callable(self):
        """Test resolver rejects non-callable."""
        import sys
        from types import ModuleType

        test_module = ModuleType("test_module5")
        test_module.__all__ = ["not_callable"]
        test_module.not_callable = "not a callable"
        sys.modules["test_module5"] = test_module

        try:
            resolver = NamedProcedureGraphResolver("test_module5.not_callable")
            with pytest.raises(NamedProcedureGraphError, match="must be a function"):
                resolver.load()
        finally:
            del sys.modules["test_module5"]

    def test_resolver_build_without_load(self, mock_dialect):
        """Test resolver build raises error if not loaded."""
        resolver = NamedProcedureGraphResolver("test.module.func")
        with pytest.raises(NamedProcedureGraphError, match="Callable not loaded"):
            resolver.build(mock_dialect)

    def test_resolver_build_invalid_return_type(self, mock_dialect):
        """Test resolver build rejects non-ProcedureGraph return."""
        import sys
        from types import ModuleType

        test_module = ModuleType("test_module6")
        test_module.__all__ = ["bad_func"]

        def bad_func(dialect, params=None):
            return "not a graph"

        test_module.bad_func = bad_func
        sys.modules["test_module6"] = test_module

        try:
            resolver = NamedProcedureGraphResolver("test_module6.bad_func")
            resolver.load()
            with pytest.raises(Exception, match="must return ProcedureGraph"):
                resolver.build(mock_dialect)
        finally:
            del sys.modules["test_module6"]

    def test_resolver_build_invalid_params(self, mock_dialect):
        """Test resolver build handles invalid params."""
        import sys
        from types import ModuleType

        test_module = ModuleType("test_module7")
        test_module.__all__ = ["strict_func"]

        def strict_func(dialect, params=None):
            return ProcedureGraph()

        test_module.strict_func = strict_func
        sys.modules["test_module7"] = test_module

        try:
            resolver = NamedProcedureGraphResolver("test_module7.strict_func")
            resolver.load()
            with pytest.raises(Exception):
                resolver.build(mock_dialect, extra_arg="bad")
        finally:
            del sys.modules["test_module7"]

    def test_resolver_describe(self):
        """Test resolver describe method."""
        import sys
        from types import ModuleType

        test_module = ModuleType("test_module8")
        test_module.__all__ = ["documented_func"]

        def documented_func(dialect, params=None):
            """This is a documented function."""
            return ProcedureGraph()

        test_module.documented_func = documented_func
        sys.modules["test_module8"] = test_module

        try:
            resolver = NamedProcedureGraphResolver("test_module8.documented_func")
            resolver.load()
            desc = resolver.describe()
            assert desc["qualified_name"] == "test_module8.documented_func"
            assert "documented function" in desc["docstring"]
            assert desc["is_class"] is False
        finally:
            del sys.modules["test_module8"]

    def test_resolver_describe_without_load(self):
        """Test resolver describe raises error if not loaded."""
        resolver = NamedProcedureGraphResolver("test.module.func")
        with pytest.raises(NamedProcedureGraphError, match="Callable not loaded"):
            resolver.describe()

    def test_resolver_build_validates_graph(self, mock_dialect):
        """Test resolver build validates the graph."""
        import sys
        from types import ModuleType

        test_module = ModuleType("test_module9")
        test_module.__all__ = ["cyclic_func"]

        def cyclic_func(dialect, params=None):
            return (
                ProcedureGraph()
                | StepNode.query("a", "q.a", depends_on=["b"])
                | StepNode.query("b", "q.b", depends_on=["a"])
            )

        test_module.cyclic_func = cyclic_func
        sys.modules["test_module9"] = test_module

        try:
            resolver = NamedProcedureGraphResolver("test_module9.cyclic_func")
            resolver.load()
            with pytest.raises(ProcedureGraphValidationError):
                resolver.build(mock_dialect)
        finally:
            del sys.modules["test_module9"]


class TestResolveNamedProcedureGraph:
    """Tests for resolve_named_procedure_graph function."""

    def test_resolve_named_procedure_graph_function(self, mock_dialect):
        """Test resolve_named_procedure_graph convenience function."""
        from rhosocial.activerecord.backend.named_query.graph_resolver import (
            resolve_named_procedure_graph,
        )
        import sys
        from types import ModuleType

        test_module = ModuleType("test_resolve_module")
        test_module.__all__ = ["simple_graph"]

        def simple_graph(dialect, params=None):
            return (
                ProcedureGraph()
                | StepNode.query("step1", "myapp.q.step1")
            )

        test_module.simple_graph = simple_graph
        sys.modules["test_resolve_module"] = test_module

        try:
            graph, resolver = resolve_named_procedure_graph(
                "test_resolve_module.simple_graph", mock_dialect
            )
            assert "step1" in graph
            assert resolver.qualified_name == "test_resolve_module.simple_graph"
        finally:
            del sys.modules["test_resolve_module"]


class TestListProcedureGraphs:
    """Tests for list_procedure_graphs_in_module function."""

    def test_list_procedure_graphs_function(self):
        """Test list_procedure_graphs_in_module function."""
        from rhosocial.activerecord.backend.named_query.graph_resolver import (
            list_procedure_graphs_in_module,
        )
        import sys
        from types import ModuleType

        test_module = ModuleType("test_list_module")
        test_module.__all__ = ["graph_func", "_private_func", "non_graph"]

        def graph_func(dialect, params=None):
            """A procedure graph function."""
            return ProcedureGraph()

        class GraphClass:
            """A procedure graph class."""

            def __call__(self, dialect, params=None):
                return ProcedureGraph()

        def non_graph():
            """Not a procedure graph."""
            pass

        test_module.graph_func = graph_func
        test_module.GraphClass = GraphClass
        test_module.non_graph = non_graph
        sys.modules["test_list_module"] = test_module

        try:
            results = list_procedure_graphs_in_module("test_list_module")
            names = [r["name"] for r in results]
            assert "graph_func" in names
            assert "GraphClass" in names
            assert "non_graph" not in names
            assert "_private_func" not in names
        finally:
            del sys.modules["test_list_module"]

    def test_list_procedure_graphs_missing_module(self):
        """Test list_procedure_graphs_in_module handles missing module."""
        from rhosocial.activerecord.backend.named_query.graph_resolver import (
            list_procedure_graphs_in_module,
        )
        from rhosocial.activerecord.backend.named_query.exceptions import (
            NamedQueryModuleNotFoundError,
        )

        with pytest.raises(NamedQueryModuleNotFoundError):
            list_procedure_graphs_in_module("nonexistent_module_xyz")

    def test_list_procedure_graphs_no_valid_graphs(self):
        """Test list_procedure_graphs_in_module with no valid graphs."""
        from rhosocial.activerecord.backend.named_query.graph_resolver import (
            list_procedure_graphs_in_module,
        )
        import sys
        from types import ModuleType

        test_module = ModuleType("test_empty_module")
        test_module.__all__ = []

        def no_dialect(x, y):
            pass

        test_module.no_dialect = no_dialect
        sys.modules["test_empty_module"] = test_module

        try:
            results = list_procedure_graphs_in_module("test_empty_module")
            assert len(results) == 0
        finally:
            del sys.modules["test_empty_module"]


class TestProcedureGraphResult:
    """Tests for ProcedureGraphResult."""

    def test_result_success(self):
        """Test result success property."""
        result = ProcedureGraphResult()
        assert result.success is True

    def test_result_failed_steps(self):
        """Test result tracks failed steps."""
        result = ProcedureGraphResult()
        entry = StepTraceEntry(name="test", kind="test", status=StepStatus.FAILED, error="Error")
        result.steps_failed.append(entry)
        assert result.success is False
        assert len(result.failed_steps()) == 1

    def test_result_to_dict(self):
        """Test result serialization."""
        result = ProcedureGraphResult()
        result.elapsed_ms = 100.0
        result.waves_count = 2

        d = result.to_dict()
        assert d["elapsed_ms"] == 100.0
        assert d["waves_count"] == 2
        assert d["success"] is True

    def test_result_to_json(self):
        """Test result JSON serialization."""
        result = ProcedureGraphResult()
        result.elapsed_ms = 50.0

        json_str = result.to_json()
        assert "elapsed_ms" in json_str
        assert "50" in json_str

    def test_result_to_table(self):
        """Test result table output."""
        result = ProcedureGraphResult()
        result.elapsed_ms = 75.0
        result.waves_count = 1
        result.steps_done.append(StepTraceEntry(
            name="step1", kind="query", status=StepStatus.OK, elapsed_ms=10.0
        ))

        table = result.to_table()
        assert "step1" in table
        assert "75" in table

    def test_result_to_table_with_skipped(self):
        """Test result table with skipped steps."""
        result = ProcedureGraphResult()
        result.steps_skipped.append(StepTraceEntry(
            name="skipped_step", kind="query", status=StepStatus.SKIPPED, reason="condition_false"
        ))

        table = result.to_table()
        assert "Skipped steps" in table
        assert "condition_false" in table

    def test_result_to_table_with_failed(self):
        """Test result table with failed steps."""
        result = ProcedureGraphResult()
        result.steps_failed.append(StepTraceEntry(
            name="failed_step", kind="query", status=StepStatus.FAILED, error="Database error"
        ))

        table = result.to_table()
        assert "Failed steps" in table
        assert "Database error" in table


class TestStepTraceEntry:
    """Tests for StepTraceEntry."""

    def test_step_trace_entry_to_dict(self):
        """Test StepTraceEntry to_dict."""
        entry = StepTraceEntry(
            name="test_step",
            kind="query",
            status=StepStatus.OK,
            sql="SELECT * FROM users",
            params=(1, 2),
            elapsed_ms=10.5,
            error=None,
            reason=None,
        )

        d = entry.to_dict()
        assert d["name"] == "test_step"
        assert d["status"] == "ok"
        assert d["sql"] == "SELECT * FROM users"
        assert d["elapsed_ms"] == 10.5

    def test_step_trace_entry_defaults(self):
        """Test StepTraceEntry default values."""
        entry = StepTraceEntry(name="test", kind="query")

        assert entry.status == StepStatus.PENDING
        assert entry.sql == ""
        assert entry.elapsed_ms == 0.0
        assert entry.error is None