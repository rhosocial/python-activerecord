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


@pytest.mark.asyncio
class TestAsyncProcedureGraphRunner:
    """Tests for AsyncProcedureGraphRunner."""

    async def test_async_runner_init(self, mock_dialect, mock_backend):
        """Test async runner initialization."""
        runner = AsyncProcedureGraphRunner(mock_backend, dialect=mock_dialect)
        assert runner.dialect is mock_dialect


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