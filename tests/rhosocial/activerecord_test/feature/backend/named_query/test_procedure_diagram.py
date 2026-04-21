# tests/rhosocial/activerecord_test/feature/backend/named_query/test_procedure_diagram.py
"""
Tests for procedure execution diagrams:
- _DryRunContext / _AsyncDryRunContext
- ProcedureDiagram (static and instance modes)
- ProcedureResult.diagram()
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from rhosocial.activerecord.backend.named_query.diagram import (
    ProcedureDiagram,
    _AsyncDryRunContext,
    _DryRunContext,
)
from rhosocial.activerecord.backend.named_query.procedure import (
    AsyncProcedure,
    AsyncProcedureContext,
    ParallelStep,
    Procedure,
    ProcedureContext,
    ProcedureResult,
    StepKind,
    TraceEntry,
    TransactionMode,
)


# Sample Procedures
class SimpleProcedure(Procedure):
    def run(self, ctx: ProcedureContext) -> None:
        ctx.execute("users.find", bind="user")
        ctx.execute("orders.create", bind="order", output=True)


class ParallelProcedure(Procedure):
    def run(self, ctx: ProcedureContext) -> None:
        ctx.execute("users.find", bind="user")
        ctx.parallel(
            ParallelStep("inventory.reserve", bind="inv"),
            ParallelStep("notify.send"),
            max_concurrency=2,
        )
        ctx.execute("orders.finalize", output=True)


class ConditionalProcedure(Procedure):
    def run(self, ctx: ProcedureContext) -> None:
        ctx.execute("users.find", bind="user")
        if ctx["user"]:
            ctx.execute("vip.apply_discount")
        else:
            ctx.execute("standard.price")
        ctx.execute("orders.create", output=True)


class SimpleAsyncProcedure(AsyncProcedure):
    async def run(self, ctx: AsyncProcedureContext) -> None:
        await ctx.execute("users.find", bind="user")
        await ctx.parallel(
            ParallelStep("inventory.reserve"),
            ParallelStep("notify.send"),
        )
        await ctx.execute("orders.finalize", output=True)


# _DryRunContext Tests
class TestDryRunContext:
    def test_execute_records_single_entry(self):
        ctx = _DryRunContext()
        ctx.execute("users.find", bind="user")

        assert len(ctx._trace) == 1
        entry = ctx._trace[0]
        assert entry.kind == StepKind.SINGLE
        assert entry.index == 0
        assert entry.qualified_name == "users.find"
        assert entry.bind == "user"
        assert entry.params == {}
        assert entry.status is None
        assert entry.elapsed_ms is None

    def test_execute_increments_index(self):
        ctx = _DryRunContext()
        ctx.execute("a.b")
        ctx.execute("c.d")

        assert ctx._trace[0].index == 0
        assert ctx._trace[1].index == 1

    def test_execute_binds_none_placeholder(self):
        ctx = _DryRunContext()
        ctx.execute("users.find", bind="user")

        assert "user" in ctx._bindings
        assert ctx._bindings["user"]["data"] == []

    def test_execute_returns_result_dict(self):
        ctx = _DryRunContext()
        result = ctx.execute("users.find")
        assert result is not None
        assert isinstance(result, dict)
        assert result["qualified_name"] == "users.find"

    def test_parallel_records_parallel_entry(self):
        ctx = _DryRunContext()
        ctx.parallel(
            ParallelStep("a.b", bind="x"),
            ParallelStep("c.d"),
            max_concurrency=2,
        )

        assert len(ctx._trace) == 1
        entry = ctx._trace[0]
        assert entry.kind == StepKind.PARALLEL
        assert entry.max_concurrency == 2
        assert len(entry.sub_steps) == 2
        assert entry.sub_steps[0].qualified_name == "a.b"
        assert entry.sub_steps[1].qualified_name == "c.d"

    def test_parallel_sub_steps_are_single_kind(self):
        ctx = _DryRunContext()
        ctx.parallel(ParallelStep("a.b"), ParallelStep("c.d"))
        for sub in ctx._trace[0].sub_steps:
            assert sub.kind == StepKind.SINGLE

    def test_parallel_binds_none_placeholder(self):
        ctx = _DryRunContext()
        ctx.parallel(ParallelStep("a.b", bind="res"))
        assert ctx._bindings.get("res") is None

    def test_getitem_returns_none_not_keyerror(self):
        ctx = _DryRunContext()
        assert ctx["nonexistent"] is None

    def test_transaction_methods_are_noop(self):
        ctx = _DryRunContext()
        ctx.begin_transaction()
        ctx.commit_transaction()
        ctx.rollback_transaction()

    def test_simple_procedure_dry_run(self):
        ctx = _DryRunContext()
        SimpleProcedure().run(ctx)

        assert len(ctx._trace) == 2
        assert ctx._trace[0].qualified_name == "users.find"
        assert ctx._trace[1].qualified_name == "orders.create"
        assert ctx._trace[1].output is True

    def test_parallel_procedure_dry_run(self):
        ctx = _DryRunContext()
        ParallelProcedure().run(ctx)

        assert len(ctx._trace) == 3
        assert ctx._trace[0].kind == StepKind.SINGLE
        assert ctx._trace[1].kind == StepKind.PARALLEL
        assert len(ctx._trace[1].sub_steps) == 2
        assert ctx._trace[2].kind == StepKind.SINGLE

    def test_conditional_procedure_dry_run_takes_true_branch(self):
        ctx = _DryRunContext()
        ConditionalProcedure().run(ctx)

        names = [e.qualified_name for e in ctx._trace]
        assert "vip.apply_discount" in names


# _AsyncDryRunContext Tests
class TestAsyncDryRunContext:
    @pytest.mark.asyncio
    async def test_execute_records_entry(self):
        ctx = _AsyncDryRunContext()
        await ctx.execute("users.find", bind="user")
        assert len(ctx._trace) == 1
        assert ctx._trace[0].qualified_name == "users.find"

    @pytest.mark.asyncio
    async def test_parallel_records_entry(self):
        ctx = _AsyncDryRunContext()
        await ctx.parallel(
            ParallelStep("a.b"),
            ParallelStep("c.d"),
        )
        assert len(ctx._trace) == 1
        assert ctx._trace[0].kind == StepKind.PARALLEL
        assert len(ctx._trace[0].sub_steps) == 2

    @pytest.mark.asyncio
    async def test_async_procedure_dry_run(self):
        ctx = _AsyncDryRunContext()
        await SimpleAsyncProcedure().run(ctx)
        assert len(ctx._trace) == 3
        assert ctx._trace[0].qualified_name == "users.find"
        assert ctx._trace[1].kind == StepKind.PARALLEL
        assert ctx._trace[2].qualified_name == "orders.finalize"


# ProcedureDiagram factory methods Tests
class TestProcedureDiagramFactories:
    def test_from_procedure_is_static(self):
        d = ProcedureDiagram.from_procedure(SimpleProcedure)
        assert d.is_static is True
        assert d.instance_trace is None

    def test_from_procedure_captures_trace(self):
        d = ProcedureDiagram.from_procedure(SimpleProcedure)
        assert len(d.static_trace) == 2

    def test_from_procedure_sets_name(self):
        d = ProcedureDiagram.from_procedure(SimpleProcedure)
        assert d.procedure_name == "SimpleProcedure"

    def test_from_procedure_sets_dialect_name(self):
        dialect = MagicMock()
        dialect.__class__.__name__ = "SQLiteDialect"
        d = ProcedureDiagram.from_procedure(SimpleProcedure, dialect=dialect)
        assert d.dialect_name == "SQLiteDialect"

    @pytest.mark.asyncio
    async def test_from_async_procedure(self):
        d = await ProcedureDiagram.from_async_procedure(SimpleAsyncProcedure)
        assert d.is_static is True
        assert len(d.static_trace) == 3

    @pytest.mark.asyncio
    async def test_from_result_is_not_static(self):
        result = _make_result_with_traces(
            static=_simple_static_trace(),
            instance=_simple_instance_trace(),
        )
        d = ProcedureDiagram.from_result(result, "MyProc")
        assert d.is_static is False
        assert d.procedure_name == "MyProc"

    @pytest.mark.asyncio
    async def test_from_result_copies_metadata(self):
        result = _make_result_with_traces(
            static=_simple_static_trace(),
            instance=_simple_instance_trace(),
            dialect_name="SQLiteDialect",
            backend_name="SQLiteBackend",
            backend_hint="File lock warning",
        )
        d = ProcedureDiagram.from_result(result)
        assert d.dialect_name == "SQLiteDialect"
        assert d.backend_name == "SQLiteBackend"
        assert d.backend_hint == "File lock warning"


# Flowchart rendering Tests
class TestFlowchartRendering:
    def test_static_contains_dry_run_comment(self):
        d = ProcedureDiagram.from_procedure(SimpleProcedure)
        output = d.to_mermaid("flowchart")
        assert "dry-run" in output

    def test_static_contains_flowchart_td(self):
        d = ProcedureDiagram.from_procedure(SimpleProcedure)
        output = d.to_mermaid("flowchart")
        assert "flowchart TD" in output

    def test_static_contains_start_and_end(self):
        d = ProcedureDiagram.from_procedure(SimpleProcedure)
        output = d.to_mermaid("flowchart")
        assert "START" in output
        assert "END" in output

    def test_static_contains_node_names(self):
        d = ProcedureDiagram.from_procedure(SimpleProcedure)
        output = d.to_mermaid("flowchart")
        assert "users.find" in output
        assert "orders.create" in output

    def test_static_nodes_use_neutral_colour(self):
        d = ProcedureDiagram.from_procedure(SimpleProcedure)
        output = d.to_mermaid("flowchart")
        assert "#ddeeff" in output

    def test_parallel_flowchart_contains_fork_join(self):
        d = ProcedureDiagram.from_procedure(ParallelProcedure)
        output = d.to_mermaid("flowchart")
        assert "fork1" in output
        assert "join1" in output

    def test_parallel_flowchart_uses_ampersand_syntax(self):
        d = ProcedureDiagram.from_procedure(ParallelProcedure)
        output = d.to_mermaid("flowchart")
        assert "&" in output

    def test_instance_contains_timing(self):
        result = _make_result_with_traces(
            static=_simple_static_trace(),
            instance=_simple_instance_trace(elapsed_ms=12.3),
        )
        d = ProcedureDiagram.from_result(result)
        output = d.to_mermaid("flowchart")
        assert "12.3 ms" in output

    def test_instance_ok_nodes_are_green(self):
        result = _make_result_with_traces(
            static=_simple_static_trace(),
            instance=_simple_instance_trace(status="ok"),
        )
        d = ProcedureDiagram.from_result(result)
        output = d.to_mermaid("flowchart")
        assert "#a8d8a8" in output

    def test_instance_error_nodes_are_red(self):
        result = _make_result_with_traces(
            static=_simple_static_trace(),
            instance=_simple_instance_trace(status="error"),
        )
        d = ProcedureDiagram.from_result(result)
        output = d.to_mermaid("flowchart")
        assert "#f4a4a4" in output

    def test_instance_unexecuted_nodes_are_grey(self):
        static = [
            TraceEntry(kind=StepKind.SINGLE, index=0, qualified_name="a.b"),
            TraceEntry(kind=StepKind.SINGLE, index=1, qualified_name="c.d"),
        ]
        instance = [
            TraceEntry(
                kind=StepKind.SINGLE, index=0,
                qualified_name="a.b", status="ok", elapsed_ms=5.0,
            )
        ]
        result = _make_result_with_traces(static=static, instance=instance)
        d = ProcedureDiagram.from_result(result)
        output = d.to_mermaid("flowchart")
        assert "#d8d8d8" in output

    def test_instance_title_contains_backend_name(self):
        result = _make_result_with_traces(
            static=_simple_static_trace(),
            instance=_simple_instance_trace(),
            backend_name="SQLiteBackend",
        )
        d = ProcedureDiagram.from_result(result, "MyProc")
        output = d.to_mermaid("flowchart")
        assert "SQLiteBackend" in output

    def test_instance_end_contains_total_time(self):
        result = _make_result_with_traces(
            static=_simple_static_trace(),
            instance=_simple_instance_trace(elapsed_ms=20.0),
        )
        d = ProcedureDiagram.from_result(result)
        output = d.to_mermaid("flowchart")
        assert "20.0 ms" in output

    def test_backend_hint_in_comment(self):
        d = ProcedureDiagram(
            static_trace=_simple_static_trace(),
            backend_hint="File lock: parallel may not help",
        )
        output = d.to_mermaid("flowchart")
        assert "File lock" in output

    def test_invalid_kind_raises(self):
        d = ProcedureDiagram.from_procedure(SimpleProcedure)
        with pytest.raises(ValueError):
            d.to_mermaid("invalid_kind")


# Sequence rendering Tests
class TestSequenceRendering:
    def test_static_contains_dry_run_comment(self):
        d = ProcedureDiagram.from_procedure(SimpleProcedure)
        output = d.to_mermaid("sequence")
        assert "dry-run" in output

    def test_static_contains_participants(self):
        d = ProcedureDiagram.from_procedure(SimpleProcedure)
        output = d.to_mermaid("sequence")
        assert "participant Runner" in output
        assert "participant DB" in output

    def test_static_contains_step_names(self):
        d = ProcedureDiagram.from_procedure(SimpleProcedure)
        output = d.to_mermaid("sequence")
        assert "users.find" in output
        assert "orders.create" in output

    def test_parallel_sequence_uses_par_and(self):
        d = ProcedureDiagram.from_procedure(ParallelProcedure)
        output = d.to_mermaid("sequence")
        assert "\n    par " in output
        assert "\n    and " in output
        assert "    end" in output

    def test_instance_executed_step_uses_solid_arrow(self):
        result = _make_result_with_traces(
            static=_simple_static_trace(),
            instance=_simple_instance_trace(status="ok"),
        )
        d = ProcedureDiagram.from_result(result)
        output = d.to_mermaid("sequence")
        assert "Runner->>DB:" in output

    def test_instance_error_step_uses_cross_arrow(self):
        result = _make_result_with_traces(
            static=_simple_static_trace(),
            instance=_simple_instance_trace(status="error", error="ValueError"),
        )
        d = ProcedureDiagram.from_result(result)
        output = d.to_mermaid("sequence")
        assert "Runner-xDB:" in output
        assert "ValueError" in output

    def test_instance_unexecuted_step_uses_dashed_arrow(self):
        static = [
            TraceEntry(kind=StepKind.SINGLE, index=0, qualified_name="a.b"),
            TraceEntry(kind=StepKind.SINGLE, index=1, qualified_name="c.d"),
        ]
        instance = [
            TraceEntry(kind=StepKind.SINGLE, index=0,
                       qualified_name="a.b", status="ok", elapsed_ms=5.0)
        ]
        result = _make_result_with_traces(static=static, instance=instance)
        d = ProcedureDiagram.from_result(result)
        output = d.to_mermaid("sequence")
        assert "Runner-->>DB: c.d" in output
        assert "not executed" in output

    def test_instance_backend_note(self):
        result = _make_result_with_traces(
            static=_simple_static_trace(),
            instance=_simple_instance_trace(),
            backend_name="SQLiteBackend",
            dialect_name="SQLiteDialect",
        )
        d = ProcedureDiagram.from_result(result)
        output = d.to_mermaid("sequence")
        assert "SQLiteBackend" in output
        assert "SQLiteDialect" in output

    def test_instance_summary_note(self):
        result = _make_result_with_traces(
            static=_simple_static_trace(),
            instance=_simple_instance_trace(status="ok", elapsed_ms=15.0),
        )
        d = ProcedureDiagram.from_result(result)
        output = d.to_mermaid("sequence")
        assert "ok" in output
        assert "15.0 ms" in output

    def test_instance_bind_shown_in_reply(self):
        static = [
            TraceEntry(kind=StepKind.SINGLE, index=0,
                       qualified_name="users.find", bind="user_id"),
        ]
        instance = [
            TraceEntry(kind=StepKind.SINGLE, index=0,
                       qualified_name="users.find", bind="user_id",
                       status="ok", elapsed_ms=3.0),
        ]
        result = _make_result_with_traces(static=static, instance=instance)
        d = ProcedureDiagram.from_result(result)
        output = d.to_mermaid("sequence")
        assert "→ user_id" in output


# ProcedureResult.diagram() Tests
class TestProcedureResultDiagram:
    def test_diagram_returns_string(self):
        result = _make_result_with_traces(
            static=_simple_static_trace(),
            instance=_simple_instance_trace(),
        )
        output = result.diagram("flowchart", "TestProc")
        assert isinstance(output, str)
        assert len(output) > 0

    def test_diagram_sequence(self):
        result = _make_result_with_traces(
            static=_simple_static_trace(),
            instance=_simple_instance_trace(),
        )
        output = result.diagram("sequence")
        assert "sequenceDiagram" in output

    def test_diagram_default_is_flowchart(self):
        result = _make_result_with_traces(
            static=_simple_static_trace(),
            instance=_simple_instance_trace(),
        )
        output = result.diagram()
        assert "flowchart TD" in output


# Procedure.static_diagram() class method Tests
class TestProcedureStaticDiagram:
    def test_static_diagram_flowchart(self):
        output = SimpleProcedure.static_diagram("flowchart")
        assert "flowchart TD" in output
        assert "users.find" in output

    def test_static_diagram_sequence(self):
        output = SimpleProcedure.static_diagram("sequence")
        assert "sequenceDiagram" in output

    @pytest.mark.asyncio
    async def test_async_static_diagram(self):
        output = await SimpleAsyncProcedure.static_diagram("flowchart")
        assert "flowchart TD" in output
        assert "users.find" in output


# Helper Functions
def _simple_static_trace() -> List[TraceEntry]:
    return [
        TraceEntry(kind=StepKind.SINGLE, index=0, qualified_name="users.find", bind="user"),
        TraceEntry(kind=StepKind.SINGLE, index=1, qualified_name="orders.create", output=True),
    ]


def _simple_instance_trace(
    status: str = "ok",
    elapsed_ms: float = 10.0,
    error: Optional[str] = None,
) -> List[TraceEntry]:
    return [
        TraceEntry(
            kind=StepKind.SINGLE, index=0,
            qualified_name="users.find", bind="user",
            status=status, error=error, elapsed_ms=elapsed_ms,
        ),
        TraceEntry(
            kind=StepKind.SINGLE, index=1,
            qualified_name="orders.create", output=True,
            status=status, error=error, elapsed_ms=elapsed_ms,
        ),
    ]


def _make_result_with_traces(
    static: List[TraceEntry],
    instance: List[TraceEntry],
    dialect_name: Optional[str] = None,
    backend_name: Optional[str] = None,
    backend_hint: Optional[str] = None,
) -> ProcedureResult:
    return ProcedureResult(
        outputs=[],
        logs=[],
        aborted=False,
        abort_reason=None,
        static_trace=static,
        instance_trace=instance,
        dialect_name=dialect_name,
        backend_name=backend_name,
        backend_hint=backend_hint,
    )