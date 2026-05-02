# src/rhosocial/activerecord/backend/named_query/graph_runner.py
"""
ProcedureGraph runners for sync and async execution.

This module provides runners that execute ProcedureGraphs,
including both synchronous and asynchronous implementations.
"""
import time
from typing import Any, Dict, List, Optional, Tuple

from .exceptions import ProcedureError
from .graph_result import ProcedureGraphResult, StepStatus, StepTraceEntry
from .procedure_graph import (
    GraphContext,
    ProcedureGraph,
    StepKind,
    StepNode,
    _extract_path,
    _interpolate_template,
    _safe_eval_condition,
)


class ProcedureGraphValidationError(ProcedureError):
    """Raised when ProcedureGraph validation fails."""

    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Graph validation failed: {', '.join(errors)}")


class ProcedureGraphRunner:
    """Synchronous runner for ProcedureGraph.

    Executes a ProcedureGraph using a synchronous backend.
    Steps within the same wave can be executed in parallel
    using ThreadPoolExecutor.

    Attributes:
        backend: The database backend (must be sync).
        dialect: The SQL dialect. If None, obtained from backend.
        dry_run: If True, only resolve SQL without executing.
        trace: If True, record execution traces.
        parallel_wave: If True, execute steps in parallel within waves.

    Example:
        >>> runner = ProcedureGraphRunner(backend, dry_run=True)
        >>> result = runner.run(graph, {"month": "2026-04"})
    """

    def __init__(
        self,
        backend: Any,
        dialect: Optional[Any] = None,
        dry_run: bool = False,
        trace: bool = False,
        parallel_wave: bool = False,
    ):
        self._backend = backend
        self._dialect = dialect or getattr(backend, "dialect", None)
        self._dry_run = dry_run
        self._trace = trace
        self._parallel_wave = parallel_wave

    @property
    def dialect(self) -> Any:
        return self._dialect

    def run(
        self,
        graph: ProcedureGraph,
        params: Optional[Dict[str, Any]] = None,
    ) -> ProcedureGraphResult:
        """Execute the ProcedureGraph.

        Args:
            graph: The ProcedureGraph to execute.
            params: Parameters for the graph execution.

        Returns:
            ProcedureGraphResult with execution details.

        Raises:
            ProcedureGraphValidationError: If graph validation fails.
        """
        errors = graph.validate()
        if errors:
            raise ProcedureGraphValidationError(errors)

        ctx = GraphContext(self._dialect, params or {})
        result = ProcedureGraphResult()

        with self._transaction(graph.transaction_mode):
            t0 = time.monotonic()
            for wave_idx, wave in enumerate(graph.waves()):
                result.waves_count = wave_idx + 1
                if self._parallel_wave:
                    self._run_wave_parallel(wave, ctx, result)
                else:
                    for node in wave:
                        self._run_node(node, ctx, result)
            result.elapsed_ms = (time.monotonic() - t0) * 1000

        return result

    def _transaction(self, mode):
        """Context manager for transactions."""
        return _SyncTransactionContext(self._backend, mode)

    def _run_wave_parallel(
        self,
        wave: List[StepNode],
        ctx: GraphContext,
        result: ProcedureGraphResult,
    ) -> None:
        """Run all nodes in a wave in parallel."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        with ThreadPoolExecutor(max_workers=len(wave)) as executor:
            futures = {
                executor.submit(self._run_node, node, ctx, result): node
                for node in wave
            }
            for future in as_completed(futures):
                future.result()

    def _run_node(
        self,
        node: StepNode,
        ctx: GraphContext,
        result: ProcedureGraphResult,
    ) -> None:
        """Run a single step node."""
        entry = StepTraceEntry(
            name=node.name,
            kind=node.kind.name,
        )

        if not ctx.eval_condition(node.condition):
            entry.status = StepStatus.SKIPPED
            entry.reason = "condition_false"
            result.steps_skipped.append(entry)
            return

        if self._dialect.name in node.skip_for:
            entry.status = StepStatus.SKIPPED
            entry.reason = f"skip_for_{self._dialect.name}"
            result.steps_skipped.append(entry)
            return

        t0 = time.monotonic()
        try:
            sql, params = self._resolve_step(node, ctx)
            entry.sql = sql
            entry.params = params

            if self._dry_run:
                entry.status = StepStatus.DRY_RUN
                result.steps_dry_run.append(entry)
                return

            rows = self._execute(sql, params)
            entry.result = rows
            entry.status = StepStatus.OK

            ctx.bind(node.bind_output, rows)
            result.steps_done.append(entry)

        except Exception as e:
            entry.status = StepStatus.FAILED
            entry.error = f"{type(e).__name__}: {e}"
            result.steps_failed.append(entry)
            raise
        finally:
            entry.elapsed_ms = (time.monotonic() - t0) * 1000

    def _resolve_step(
        self,
        node: StepNode,
        ctx: GraphContext,
    ) -> Tuple[str, tuple]:
        """Resolve a step to SQL and parameters."""
        resolved_params = {**node.params, **node.bind}
        resolved_params = _interpolate_dict(resolved_params, ctx)

        if node.kind == StepKind.NAMED_QUERY:
            from .resolver import resolve_named_query
            expr = resolve_named_query(node.named_query, self._dialect, resolved_params)[0]
            return expr.to_sql()

        elif node.kind == StepKind.EXPRESSION:
            return node.expression.to_sql()

        elif node.kind == StepKind.SUBGRAPH:
            raise ProcedureError("SUBGRAPH must be expanded before execution")

    def _execute(self, sql: str, params: tuple) -> Any:
        """Execute SQL on the backend."""
        return self._backend.execute(sql, params)


class AsyncProcedureGraphRunner:
    """Asynchronous runner for ProcedureGraph.

    Executes a ProcedureGraph using an async backend.
    Steps within the same wave are executed concurrently
    using asyncio.gather().

    Example:
        >>> runner = AsyncProcedureGraphRunner(async_backend, dry_run=True)
        >>> result = await runner.run(graph, {"month": "2026-04"})
    """

    def __init__(
        self,
        backend: Any,
        dialect: Optional[Any] = None,
        dry_run: bool = False,
        trace: bool = False,
    ):
        self._backend = backend
        self._dialect = dialect or getattr(backend, "dialect", None)
        self._dry_run = dry_run
        self._trace = trace

    @property
    def dialect(self) -> Any:
        return self._dialect

    async def run(
        self,
        graph: ProcedureGraph,
        params: Optional[Dict[str, Any]] = None,
    ) -> ProcedureGraphResult:
        """Execute the ProcedureGraph asynchronously."""
        errors = graph.validate()
        if errors:
            raise ProcedureGraphValidationError(errors)

        ctx = GraphContext(self._dialect, params or {})
        result = ProcedureGraphResult()

        async with self._transaction(graph.transaction_mode):
            t0 = time.monotonic()
            for wave_idx, wave in enumerate(graph.waves()):
                result.waves_count = wave_idx + 1
                import asyncio
                tasks = [
                    self._run_node_async(node, ctx, result)
                    for node in wave
                ]
                await asyncio.gather(*tasks)
            result.elapsed_ms = (time.monotonic() - t0) * 1000

        return result

    def _transaction(self, mode):
        """Context manager for async transactions."""
        return _AsyncTransactionContext(self._backend, mode)

    async def _run_node_async(
        self,
        node: StepNode,
        ctx: GraphContext,
        result: ProcedureGraphResult,
    ) -> None:
        """Run a single step node asynchronously."""
        entry = StepTraceEntry(
            name=node.name,
            kind=node.kind.name,
        )

        if not ctx.eval_condition(node.condition):
            entry.status = StepStatus.SKIPPED
            entry.reason = "condition_false"
            result.steps_skipped.append(entry)
            return

        if self._dialect.name in node.skip_for:
            entry.status = StepStatus.SKIPPED
            entry.reason = f"skip_for_{self._dialect.name}"
            result.steps_skipped.append(entry)
            return

        t0 = time.monotonic()
        try:
            sql, params = self._resolve_step(node, ctx)
            entry.sql = sql
            entry.params = params

            if self._dry_run:
                entry.status = StepStatus.DRY_RUN
                result.steps_dry_run.append(entry)
                return

            rows = await self._execute(sql, params)
            entry.result = rows
            entry.status = StepStatus.OK

            ctx.bind(node.bind_output, rows)
            result.steps_done.append(entry)

        except Exception as e:
            entry.status = StepStatus.FAILED
            entry.error = f"{type(e).__name__}: {e}"
            result.steps_failed.append(entry)
            raise
        finally:
            entry.elapsed_ms = (time.monotonic() - t0) * 1000

    def _resolve_step(
        self,
        node: StepNode,
        ctx: GraphContext,
    ) -> Tuple[str, tuple]:
        """Resolve a step to SQL and parameters."""
        resolved_params = {**node.params, **node.bind}
        resolved_params = _interpolate_dict(resolved_params, ctx)

        if node.kind == StepKind.NAMED_QUERY:
            from .resolver import resolve_named_query
            expr = resolve_named_query(node.named_query, self._dialect, resolved_params)[0]
            return expr.to_sql()

        elif node.kind == StepKind.EXPRESSION:
            return node.expression.to_sql()

        elif node.kind == StepKind.SUBGRAPH:
            raise ProcedureError("SUBGRAPH must be expanded before execution")

    async def _execute(self, sql: str, params: tuple) -> Any:
        """Execute SQL on the async backend."""
        return await self._backend.execute(sql, params)


def _interpolate_dict(
    data: Dict[str, Any],
    ctx: GraphContext,
) -> Dict[str, Any]:
    """Interpolate ${var} placeholders in a dict."""
    result = {}
    for k, v in data.items():
        if isinstance(v, str):
            result[k] = ctx.interpolate(v)
        elif isinstance(v, dict):
            result[k] = _interpolate_dict(v, ctx)
        elif isinstance(v, list):
            result[k] = [
                ctx.interpolate(i) if isinstance(i, str) else i
                for i in v
            ]
        else:
            result[k] = v
    return result


class _SyncTransactionContext:
    """Sync transaction context manager."""

    def __init__(self, backend, mode):
        self._backend = backend
        self._mode = mode
        self._in_tx = False

    def __enter__(self):
        from .procedure_graph import TransactionMode
        if self._mode in (TransactionMode.AUTO, TransactionMode.STEP):
            self._backend.begin_transaction()
            self._in_tx = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        from .procedure_graph import TransactionMode
        if self._in_tx:
            if exc_type is None:
                self._backend.commit_transaction()
            else:
                self._backend.rollback_transaction()
            self._in_tx = False
        return False


class _AsyncTransactionContext:
    """Async transaction context manager."""

    def __init__(self, backend, mode):
        self._backend = backend
        self._mode = mode
        self._in_tx = False

    async def __aenter__(self):
        from .procedure_graph import TransactionMode
        if self._mode in (TransactionMode.AUTO, TransactionMode.STEP):
            await self._backend.begin_transaction()
            self._in_tx = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        from .procedure_graph import TransactionMode
        if self._in_tx:
            if exc_type is None:
                await self._backend.commit_transaction()
            else:
                await self._backend.rollback_transaction()
            self._in_tx = False
        return False