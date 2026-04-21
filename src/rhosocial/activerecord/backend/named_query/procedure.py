# src/rhosocial/activerecord/backend/named_query/procedure.py
"""
Named procedure support for the backend.

This module provides functionality to define and execute named procedures
that can orchestrate multiple named queries with transaction support.

What is Named Procedure:
    Named procedure is a class that:
    - Inherits from the Procedure base class
    - Defines parameters as class attributes with type annotations
    - Implements a run(ctx) method that orchestrates named queries

    Example:
        >>> from rhosocial.activerecord.backend.named_query import Procedure, ProcedureContext
        >>>
        >>> class MonthlyReportProcedure(Procedure):
        ...     month: str  # Required parameter
        ...     threshold: int = 100  # Optional with default
        ...
        ...     def run(self, ctx: ProcedureContext) -> None:
        ...         # Execute a named query and bind result
        ...         ctx.execute(
        ...             "myapp.queries.orders.monthly_summary",
        ...             params={"month": self.month},
        ...             bind="summary",
        ...         )
        ...         # Get scalar value from result
        ...         total = ctx.scalar("summary", "total_count")
        ...         if total < self.threshold:
        ...             ctx.log(f"Total {total} below threshold")
        ...             return
        ...         # Iterate rows
        ...         for row in ctx.rows("summary"):
        ...             ctx.execute(
        ...                 "myapp.queries.archive.insert_record",
        ...                 params={"order_id": row["id"], "month": self.month},
        ...             )

Components:
    - Procedure: Base class for named procedures
    - ProcedureContext: Runtime context for procedure execution
    - ProcedureRunner: Executes procedures with transaction management
    - ProcedureResult: Result object returned by procedure execution

Usage:
    >>> from rhosocial.activerecord.backend.named_query import ProcedureRunner
    >>> runner = ProcedureRunner("myapp.procedures.monthly_report")
    >>> result = runner.run(dialect, {"month": "2026-03"})
"""
import inspect
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Type

from .resolver import resolve_named_query


class TransactionMode(Enum):
    """Transaction mode for procedure execution."""

    AUTO = "auto"
    STEP = "step"
    NONE = "none"


class StepKind(str, Enum):
    """Kind of procedure step."""

    SINGLE   = "single"
    PARALLEL = "parallel"


@dataclass
class LogEntry:
    """Represents a log entry from procedure execution."""

    level: str
    message: str


@dataclass
class TraceEntry:
    """Represents a single step trace entry for diagram generation."""

    kind: StepKind
    index: int

    qualified_name: Optional[str]    = None
    params: Dict[str, Any]           = field(default_factory=dict)
    bind: Optional[str]              = None
    output: bool                     = False

    sub_steps: List["TraceEntry"]    = field(default_factory=list)
    max_concurrency: Optional[int]   = None

    status: Optional[str]            = None
    error: Optional[str]             = None
    elapsed_ms: Optional[float]      = None


@dataclass
class ProcedureResult:
    """Result of procedure execution."""

    outputs: List[Dict[str, Any]] = field(default_factory=list)
    logs: List[LogEntry] = field(default_factory=list)
    aborted: bool = False
    abort_reason: Optional[str] = None

    static_trace: List[TraceEntry]   = field(default_factory=list)
    instance_trace: List[TraceEntry] = field(default_factory=list)

    dialect_name: Optional[str]      = None
    backend_name: Optional[str]      = None
    backend_hint: Optional[str]      = None

    @property
    def success(self) -> bool:
        return not self.aborted

    def diagram(
        self,
        kind: str = "flowchart",
        procedure_name: str = "Procedure",
    ) -> str:
        from .diagram import ProcedureDiagram
        return ProcedureDiagram.from_result(self, procedure_name).to_mermaid(kind)


@dataclass
class ParallelStep:
    """Descriptor for a single step in ctx.parallel().

    Mirrors the execute() signature so the parallel API stays consistent
    with sequential execution.

    Attributes:
        qualified_name: Fully qualified name of the named query.
        params: Parameters to pass to the named query.
        bind: Optional variable name to bind the result into ctx.bindings.
        output: Whether to include this result in ProcedureResult.outputs.

    Example:
        >>> await ctx.parallel(
        ...     ParallelStep("myapp.inventory.deduct", {"order_id": 1}),
        ...     ParallelStep("myapp.payments.preauth", {"amount": 99},
        ...                  bind="pay", output=True),
        ...     max_concurrency=2,
        ... )
    """

    qualified_name: str
    params: Dict[str, Any] = field(default_factory=dict)
    bind: Optional[str] = None
    output: bool = False


def _resolve_concurrency(backend: Any, user_max: Optional[int]) -> Optional[int]:
    """Resolve effective concurrency limit.

    Priority chain:
        user_max > backend ConcurrencyAware hint > None (unlimited)

    Args:
        backend: Database backend, optionally implementing ConcurrencyAware.
        user_max: Caller-specified limit. None means "not specified by caller".

    Returns:
        Resolved integer limit, or None for unlimited.
    """
    if user_max is not None:
        return user_max

    try:
        from ..protocols import ConcurrencyAware

        if isinstance(backend, ConcurrencyAware):
            hint = backend.get_concurrency_hint()
            if hint is not None:
                return hint.max_concurrency
    except ImportError:
        pass

    return None


def _get_backend_hint_reason(backend: Any) -> Optional[str]:
    """Get backend concurrency hint reason if available."""
    try:
        from ..protocols import ConcurrencyAware

        if isinstance(backend, ConcurrencyAware):
            hint = backend.get_concurrency_hint()
            if hint is not None:
                return hint.reason
    except ImportError:
        pass
    return None


class ProcedureContext:
    """Runtime context for procedure execution.

    This class provides the interface for procedures to interact with
    the execution environment, including executing named queries,
    binding results, and logging.

    Attributes:
        dialect: The dialect instance for query execution.
        bindings: Dictionary of bound result sets.

    Example:
        >>> class MyProcedure(Procedure):
        ...     def run(self, ctx: ProcedureContext) -> None:
        ...         ctx.execute("myapp.queries.get_users", bind="users")
        ...         for user in ctx.rows("users"):
        ...             print(user["name"])
    """

    def __init__(
        self,
        dialect: Any,
        execute_callback: Any,
        transaction_mode: TransactionMode = TransactionMode.AUTO,
        backend: Any = None,
    ):
        self._dialect = dialect
        self._execute_callback = execute_callback
        self._transaction_mode = transaction_mode
        self._backend = backend
        self._bindings: Dict[str, Dict[str, Any]] = {}
        self._logs: List[LogEntry] = []
        self._in_transaction: bool = False
        self._trace: List[TraceEntry] = []
        self._trace_index: int = 0

    @property
    def dialect(self) -> Any:
        """Get the dialect instance."""
        return self._dialect

    @property
    def bindings(self) -> Dict[str, Dict[str, Any]]:
        """Get all bindings."""
        return self._bindings

    def execute(
        self,
        qualified_name: str,
        params: Optional[Dict[str, Any]] = None,
        bind: Optional[str] = None,
        output: bool = False,
    ) -> Dict[str, Any]:
        """Execute a named query and optionally bind the result.

        For TransactionMode.STEP, each execute call runs in its own transaction
        and commits after execution.

        Args:
            qualified_name: Fully qualified name of the named query.
            params: Parameters to pass to the named query.
            bind: Optional variable name to bind the result to.
            output: Mark this result as an output to be returned.

        Returns:
            Dict containing:
                - data: List of row dictionaries
                - affected_rows: Number of rows affected
                - sql: The generated SQL
                - params: The SQL parameters

        Example:
            >>> ctx.execute(
            ...     "myapp.queries.active_users",
...             params={"limit": 50},
            ...             bind="users",
            ... )
        """
        import time as time_module

        if self._transaction_mode == TransactionMode.STEP:
            if hasattr(self, "_begin_transaction") and callable(getattr(self, "_begin_transaction", None)):
                self._begin_transaction()

        params = params or {}
        _start = time_module.monotonic()
        _status, _error = "ok", None
        try:
            result = self._execute_callback(qualified_name, self._dialect, params)
        except Exception as exc:
            _status, _error = "error", type(exc).__name__
            raise
        finally:
            self._trace.append(TraceEntry(
                kind=StepKind.SINGLE,
                index=self._trace_index,
                qualified_name=qualified_name,
                params=dict(params),
                bind=bind,
                output=output,
                status=_status,
                error=_error,
                elapsed_ms=(time_module.monotonic() - _start) * 1000,
            ))
            self._trace_index += 1

        if self._transaction_mode == TransactionMode.STEP:
            if hasattr(self, "_in_transaction") and self._in_transaction:
                if hasattr(self, "_commit_transaction") and callable(getattr(self, "_commit_transaction", None)):
                    self._commit_transaction()

        result_data = {
            "qualified_name": qualified_name,
            "params": params,
            "bind": bind,
            "output": output,
            "sql": result.get("sql", ""),
            "params_sql": result.get("params_sql", ()),
            "data": result.get("data", []),
            "affected_rows": result.get("affected_rows", 0),
        }

        if bind:
            self._bindings[bind] = result_data

        return result_data

    def scalar(self, var_name: str, column: str) -> Any:
        """Extract a scalar value from a bound result set.

        Args:
            var_name: The variable name the result was bound to.
            column: The column name to extract.

        Returns:
            The value from the first row's column, or None if not found.

        Example:
            >>> total = ctx.scalar("summary", "total_count")
        """
        if var_name not in self._bindings:
            raise ValueError(f"Variable '{var_name}' not found in bindings")

        data = self._bindings[var_name].get("data", [])
        if not data:
            return None

        first_row = data[0]
        return first_row.get(column)

    def rows(self, var_name: str) -> Iterator[Dict[str, Any]]:
        """Iterate over all rows in a bound result set.

        Args:
            var_name: The variable name the result was bound to.

        Yields:
            Row dictionaries from the result set.

        Example:
            >>> for user in ctx.rows("users"):
            ...     print(user["name"])
        """
        if var_name not in self._bindings:
            raise ValueError(f"Variable '{var_name}' not found in bindings")

        data = self._bindings[var_name].get("data", [])
        yield from data

    def bind(self, name: str, data: Any) -> None:
        """Bind arbitrary data to a variable.

        Args:
            name: Variable name to bind to.
            data: Data to bind. Can be a single item, dict, or list of items.

        Example:
            >>> ctx.bind("config", {"threshold": 100})
            >>> ctx.bind("items", [{"id": 1}, {"id": 2}])
        """
        if data is None:
            self._bindings[name] = {"data": []}
        elif isinstance(data, list):
            self._bindings[name] = {"data": data}
        elif isinstance(data, dict):
            self._bindings[name] = {"data": [data]}
        else:
            self._bindings[name] = {"data": [data]}

    def log(self, message: str, level: str = "INFO") -> None:
        """Log a message from the procedure.

        Args:
            message: The log message.
            level: Log level (DEBUG, INFO, WARNING, ERROR).

        Example:
            >>> ctx.log("Processing started", "DEBUG")
        """
        self._logs.append(LogEntry(level=level, message=message))

    def abort(self, procedure_name: str, reason: str) -> None:
        """Abort the procedure execution.

        This triggers a transaction rollback and stops further execution.

        Args:
            procedure_name: The qualified name of the procedure.
            reason: The reason for aborting.

        Example:
        >>> if total < threshold:
        ...     ctx.abort("myapp.procedures.monthly", f"Total {total} below threshold")
        """
        from .exceptions import ProcedureAbortedError

        raise ProcedureAbortedError(procedure_name, reason)

    def parallel(
        self,
        *steps: ParallelStep,
        max_concurrency: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Execute multiple named query steps concurrently.

        Steps bypass per-step transaction management (the BEGIN/COMMIT that
        TransactionMode.STEP applies to each execute() call) and invoke the
        shared execute_callback directly.  In TransactionMode.AUTO the outer
        transaction therefore covers all parallel steps; in STEP/NONE each
        step executes independently.

        Args:
            *steps: ParallelStep descriptors to execute concurrently.
            max_concurrency: Maximum concurrent steps.
                None  — resolved from backend ConcurrencyAware hint, or unlimited.
                1     — force serial execution (debug / safe fallback).
                N > 1 — at most N steps run simultaneously.

        Returns:
            List of result dicts in the **same order** as input steps.

        Raises:
            Exception: First exception raised by any step; the executor waits
                for all futures before re-raising.

        Example:
            >>> results = ctx.parallel(
            ...     ParallelStep("myapp.stock.deduct", {"sku": "A1"}),
            ...     ParallelStep("myapp.payment.reserve", {"amount": 50}),
            ...     max_concurrency=2,
            ... )
        """
        import time as time_module

        if not steps:
            return []

        limit = _resolve_concurrency(getattr(self, "_backend", None), max_concurrency)
        _start = time_module.monotonic()

        sub_entries: List[TraceEntry] = []
        results: List[Optional[Dict[str, Any]]] = []

        if limit == 1:
            for i, step in enumerate(steps):
                t = time_module.monotonic()
                s, e = "ok", None
                try:
                    result = self._run_parallel_step(step)
                    results.append(result)
                except Exception as exc:
                    s, e = "error", type(exc).__name__
                    results.append(None)
                sub_entries.append(TraceEntry(
                    kind=StepKind.SINGLE,
                    index=i,
                    qualified_name=step.qualified_name,
                    params=dict(step.params),
                    bind=step.bind,
                    output=step.output,
                    status=s,
                    error=e,
                    elapsed_ms=(time_module.monotonic() - t) * 1000,
                ))
        else:
            results = [None] * len(steps)
            bind_lock = threading.Lock()
            first_exc: List[BaseException] = []

            def _run(idx: int, step: ParallelStep) -> None:
                t = time_module.monotonic()
                s, e = "ok", None
                try:
                    results[idx] = self._run_parallel_step(step, bind_lock=bind_lock)
                except Exception as exc:
                    s, e = "error", type(exc).__name__
                    first_exc.append(exc)
                    raise

            with ThreadPoolExecutor(max_workers=limit) as executor:
                futures = [
                    executor.submit(_run, i, step) for i, step in enumerate(steps)
                ]
                for fut in futures:
                    try:
                        fut.result()
                    except Exception:
                        pass

            for i, r in enumerate(results):
                if r is not None:
                    sub_entries.append(TraceEntry(
                        kind=StepKind.SINGLE,
                        index=i,
                        qualified_name=steps[i].qualified_name,
                        params=dict(steps[i].params),
                        bind=steps[i].bind,
                        output=steps[i].output,
                        status="ok",
                        elapsed_ms=0,
                    ))
                else:
                    sub_entries.append(TraceEntry(
                        kind=StepKind.SINGLE,
                        index=i,
                        qualified_name=steps[i].qualified_name,
                        params=dict(steps[i].params),
                        bind=steps[i].bind,
                        output=steps[i].output,
                        status="error",
                        error="unknown",
                        elapsed_ms=0,
                    ))

            if first_exc:
                raise first_exc[0]

        overall = "error" if any(e.status == "error" for e in sub_entries) else "ok"
        self._trace.append(TraceEntry(
            kind=StepKind.PARALLEL,
            index=self._trace_index,
            sub_steps=sub_entries,
            max_concurrency=limit,
            status=overall,
            elapsed_ms=(time_module.monotonic() - _start) * 1000,
        ))
        self._trace_index += 1

        return [r for r in results if r is not None]

    def _run_parallel_step(
        self,
        step: ParallelStep,
        bind_lock: Optional[threading.Lock] = None,
    ) -> Dict[str, Any]:
        """Execute a single ParallelStep directly via execute_callback.

        Bypasses per-step transaction management; called by both parallel()
        and (when max_concurrency=1) the serial fallback path.
        """
        params = step.params or {}
        raw = self._execute_callback(step.qualified_name, self._dialect, params)
        result_data: Dict[str, Any] = {
            "qualified_name": step.qualified_name,
            "params": params,
            "bind": step.bind,
            "output": step.output,
            "sql": raw.get("sql", ""),
            "params_sql": raw.get("params_sql", ()),
            "data": raw.get("data", []),
            "affected_rows": raw.get("affected_rows", 0),
        }
        if step.bind:
            if bind_lock is not None:
                with bind_lock:
                    self._bindings[step.bind] = result_data
            else:
                self._bindings[step.bind] = result_data
        return result_data


class AsyncProcedureContext:
    """Asynchronous runtime context for procedure execution.

    This class provides the async interface for procedures to interact with
    the execution environment, including executing named queries,
    binding results, and logging.

    Example:
        >>> class MyAsyncProcedure(AsyncProcedure):
        ...     async def run(self, ctx: AsyncProcedureContext) -> None:
        ...         await ctx.execute("myapp.queries.get_users", bind="users")
        ...         async for user in ctx.rows("users"):
        ...             print(user["name"])
    """

    def __init__(
        self,
        dialect: Any,
        execute_callback: Any,
        transaction_mode: TransactionMode = TransactionMode.AUTO,
        backend: Any = None,
    ):
        self._dialect = dialect
        self._execute_callback = execute_callback
        self._transaction_mode = transaction_mode
        self._backend = backend
        self._bindings: Dict[str, Dict[str, Any]] = {}
        self._logs: List[LogEntry] = []
        self._in_transaction: bool = False
        self._trace: List[TraceEntry] = []
        self._trace_index: int = 0

    @property
    def dialect(self) -> Any:
        return self._dialect

    @property
    def bindings(self) -> Dict[str, Dict[str, Any]]:
        return self._bindings

    async def execute(
        self,
        qualified_name: str,
        params: Optional[Dict[str, Any]] = None,
        bind: Optional[str] = None,
        output: bool = False,
    ) -> Dict[str, Any]:
        """Execute a named query asynchronously."""
        import time as time_module

        if self._transaction_mode == TransactionMode.STEP:
            if hasattr(self, "_begin_transaction") and callable(getattr(self, "_begin_transaction", None)):
                await self._begin_transaction()

        params = params or {}
        _start = time_module.monotonic()
        _status, _error = "ok", None
        try:
            result = await self._execute_callback(qualified_name, self._dialect, params)
        except Exception as exc:
            _status, _error = "error", type(exc).__name__
            raise
        finally:
            self._trace.append(TraceEntry(
                kind=StepKind.SINGLE,
                index=self._trace_index,
                qualified_name=qualified_name,
                params=dict(params),
                bind=bind,
                output=output,
                status=_status,
                error=_error,
                elapsed_ms=(time_module.monotonic() - _start) * 1000,
            ))
            self._trace_index += 1

        if self._transaction_mode == TransactionMode.STEP:
            in_transaction = getattr(self, "_in_transaction", False)
            if in_transaction:
                if hasattr(self, "_commit_transaction") and callable(getattr(self, "_commit_transaction", None)):
                    await self._commit_transaction()

        result_data = {
            "qualified_name": qualified_name,
            "params": params,
            "bind": bind,
            "output": output,
            "sql": result.get("sql", ""),
            "params_sql": result.get("params_sql", ()),
            "data": result.get("data", []),
            "affected_rows": result.get("affected_rows", 0),
        }

        if bind:
            self._bindings[bind] = result_data

        return result_data

    async def scalar(self, var_name: str, column: str) -> Any:
        if var_name not in self._bindings:
            raise ValueError(f"Variable '{var_name}' not found in bindings")
        data = self._bindings[var_name].get("data", [])
        if not data:
            return None
        first_row = data[0]
        return first_row.get(column)

    async def rows(self, var_name: str) -> AsyncIterator[Dict[str, Any]]:
        if var_name not in self._bindings:
            raise ValueError(f"Variable '{var_name}' not found in bindings")
        data = self._bindings[var_name].get("data", [])
        for row in data:
            yield row

    async def bind(self, name: str, data: Any) -> None:
        if data is None:
            self._bindings[name] = {"data": []}
        elif isinstance(data, list):
            self._bindings[name] = {"data": data}
        elif isinstance(data, dict):
            self._bindings[name] = {"data": [data]}
        else:
            self._bindings[name] = {"data": [data]}

    async def log(self, message: str, level: str = "INFO") -> None:
        self._logs.append(LogEntry(level=level, message=message))

    async def abort(self, procedure_name: str, reason: str) -> None:
        from .exceptions import ProcedureAbortedError
        raise ProcedureAbortedError(procedure_name, reason)

    async def parallel(
        self,
        *steps: ParallelStep,
        max_concurrency: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Execute multiple named query steps concurrently (async).

        Same semantics as ProcedureContext.parallel() but uses
        asyncio.Semaphore + asyncio.gather for concurrency control.
        asyncio is single-threaded; assignments between await points are
        inherently atomic, so no lock is needed for _bindings writes.

        Args:
            *steps: ParallelStep descriptors to execute concurrently.
            max_concurrency: See ProcedureContext.parallel().

        Returns:
            List of result dicts in the **same order** as input steps.
        """
        import asyncio
        import time as time_module

        if not steps:
            return []

        limit = _resolve_concurrency(getattr(self, "_backend", None), max_concurrency)
        _start = time_module.monotonic()

        sub_entries: List[TraceEntry] = []
        results: List[Optional[Dict[str, Any]]] = []

        if limit == 1:
            for i, step in enumerate(steps):
                t = time_module.monotonic()
                s, e = "ok", None
                try:
                    result = await self._run_parallel_step(step)
                    results.append(result)
                except Exception as exc:
                    s, e = "error", type(exc).__name__
                    results.append(None)
                sub_entries.append(TraceEntry(
                    kind=StepKind.SINGLE,
                    index=i,
                    qualified_name=step.qualified_name,
                    params=dict(step.params),
                    bind=step.bind,
                    output=step.output,
                    status=s,
                    error=e,
                    elapsed_ms=(time_module.monotonic() - t) * 1000,
                ))
        else:
            semaphore = asyncio.Semaphore(limit) if limit is not None else None

            async def _run(idx: int, step: ParallelStep) -> tuple:
                t = time_module.monotonic()
                s, e = "ok", None
                try:
                    result = await self._run_parallel_step(step)
                except Exception as exc:
                    s, e = "error", type(exc).__name__
                    result = None
                return (idx, result, s, e, (time_module.monotonic() - t) * 1000)

            task_results = await asyncio.gather(*[
                _run(i, step) for i, step in enumerate(steps)
            ])

            task_results_sorted = sorted(task_results, key=lambda x: x[0])
            results = [r[1] for r in task_results_sorted]
            for idx, result, status, error, elapsed in task_results_sorted:
                sub_entries.append(TraceEntry(
                    kind=StepKind.SINGLE,
                    index=idx,
                    qualified_name=steps[idx].qualified_name,
                    params=dict(steps[idx].params),
                    bind=steps[idx].bind,
                    output=steps[idx].output,
                    status=status,
                    error=error,
                    elapsed_ms=elapsed,
                ))

        overall = "error" if any(e.status == "error" for e in sub_entries) else "ok"
        self._trace.append(TraceEntry(
            kind=StepKind.PARALLEL,
            index=self._trace_index,
            sub_steps=sub_entries,
            max_concurrency=limit,
            status=overall,
            elapsed_ms=(time_module.monotonic() - _start) * 1000,
        ))
        self._trace_index += 1

        return [r for r in results if r is not None]

    async def _run_parallel_step(self, step: ParallelStep) -> Dict[str, Any]:
        """Execute a single ParallelStep directly via async execute_callback."""
        params = step.params or {}
        raw = await self._execute_callback(step.qualified_name, self._dialect, params)
        result_data: Dict[str, Any] = {
            "qualified_name": step.qualified_name,
            "params": params,
            "bind": step.bind,
            "output": step.output,
            "sql": raw.get("sql", ""),
            "params_sql": raw.get("params_sql", ()),
            "data": raw.get("data", []),
            "affected_rows": raw.get("affected_rows", 0),
        }
        if step.bind:
            # asyncio single-threaded: assignment is atomic between await points
            self._bindings[step.bind] = result_data
        return result_data


class Procedure:
    """Base class for named procedures.

    Subclasses must:
    - Define parameters as class attributes with type annotations
    - Implement a run(ctx: ProcedureContext) method

    Attributes:
        Parameters are defined as class attributes with type annotations.
        Required parameters have no default, optional parameters have defaults.

    Example:
        >>> class MyProcedure(Procedure):
        ...     month: str
        ...     threshold: int = 100
        ...
        ...     def run(self, ctx: ProcedureContext) -> None:
        ...         ctx.execute("myapp.queries.get_data", bind="data")
    """

    def run(self, ctx: ProcedureContext) -> None:
        """Execute the procedure logic.

        This method must be implemented by subclasses to define
        the procedure's logic.

        Args:
            ctx: The procedure context for execution.

        Raises:
            Any exception will cause transaction rollback.
        """
        raise NotImplementedError("Subclasses must implement run()")

    @classmethod
    def get_parameters(cls) -> Dict[str, Any]:
        """Get parameter information from class attributes.

        Returns:
            Dict mapping parameter names to type annotations and defaults.
        """
        params = {}
        for name, annotation in cls.__annotations__.items():
            if name == "run":
                continue
            default = getattr(cls, name, inspect.Parameter.empty)
            params[name] = {
                "annotation": annotation,
                "default": default,
                "has_default": default is not inspect.Parameter.empty,
            }
        return params

    @classmethod
    def static_diagram(cls, kind: str = "flowchart", dialect: Any = None) -> str:
        """Generate a static diagram without executing the procedure.

        This performs a dry-run to capture the procedure structure.

        Args:
            kind: Diagram type - "flowchart" or "sequence"
            dialect: Optional dialect for additional metadata

        Returns:
            Mermaid diagram string
        """
        from .diagram import ProcedureDiagram
        return ProcedureDiagram.from_procedure(cls, dialect=dialect).to_mermaid(kind)


class _BaseProcedureRunner:
    """Internal base class sharing qualified-name parsing and describe() logic.

    Not part of the public API. Subclasses must implement load() and run().
    """

    def __init__(self, qualified_name: str) -> None:
        self._qualified_name = qualified_name
        self._procedure_class: Optional[type] = None
        self._params_info: Dict[str, Any] = {}
        self._module_name, self._class_name = self._parse_qualified_name(qualified_name)

    @staticmethod
    def _parse_qualified_name(qualified_name: str):
        parts = qualified_name.rsplit(".", 1)
        if len(parts) != 2:
            from .exceptions import NamedQueryError
            raise NamedQueryError(
                f"Invalid qualified name '{qualified_name}'. "
                "Must be in format 'module.path.ClassName'"
            )
        return parts[0], parts[1]

    @property
    def qualified_name(self) -> str:
        return self._qualified_name

    def _import_class(self) -> type:
        """Import the class from the module. No type validation performed here."""
        import importlib
        from .exceptions import NamedQueryError, NamedQueryModuleNotFoundError

        try:
            module = importlib.import_module(self._module_name)
        except ModuleNotFoundError as e:
            raise NamedQueryModuleNotFoundError(
                self._module_name, f"Module not found: {e}"
            ) from None

        if not hasattr(module, self._class_name):
            raise NamedQueryError(
                f"Procedure '{self._class_name}' not found "
                f"in module '{self._module_name}'"
            )
        return getattr(module, self._class_name)

    def describe(self) -> Dict[str, Any]:
        if not self._procedure_class:
            from .exceptions import NamedQueryError
            raise NamedQueryError("Procedure not loaded. Call load() first.")
        return {
            "qualified_name": self._qualified_name,
            "class_name": self._class_name,
            "docstring": inspect.getdoc(self._procedure_class) or "",
            "parameters": self._params_info,
        }


class AsyncProcedure:
    """Base class for asynchronous named procedures.

    Subclasses must:
    - Define parameters as class attributes with type annotations
    - Implement an async run(ctx: AsyncProcedureContext) method

    Example:
        >>> class MyAsyncProcedure(AsyncProcedure):
        ...     month: str
        ...     threshold: int = 100
        ...
        ...     async def run(self, ctx: AsyncProcedureContext) -> None:
        ...         await ctx.execute("myapp.queries.get_data", bind="data")
    """

    async def run(self, ctx: AsyncProcedureContext) -> None:
        raise NotImplementedError("Subclasses must implement async run()")

    @classmethod
    def get_parameters(cls) -> Dict[str, Any]:
        params = {}
        for name, annotation in cls.__annotations__.items():
            if name == "run":
                continue
            default = getattr(cls, name, inspect.Parameter.empty)
            params[name] = {
                "annotation": annotation,
                "default": default,
                "has_default": default is not inspect.Parameter.empty,
            }
        return params

    @classmethod
    async def static_diagram(
        cls, kind: str = "flowchart", dialect: Any = None
    ) -> str:
        """Generate a static diagram without executing the procedure (async).

        Args:
            kind: Diagram type - "flowchart" or "sequence"
            dialect: Optional dialect for additional metadata

        Returns:
            Mermaid diagram string
        """
        from .diagram import ProcedureDiagram

        return (
            await ProcedureDiagram.from_async_procedure(cls, dialect=dialect)
        ).to_mermaid(kind)


class ProcedureRunner(_BaseProcedureRunner):
    """Runner for synchronous Procedure subclasses.

    Only accepts classes that inherit from Procedure.
    For async procedures use AsyncProcedureRunner.
    """

    def load(self) -> "ProcedureRunner":
        """Load the procedure class.

        Returns:
            self for chaining.

        Raises:
            NamedQueryModuleNotFoundError: If module cannot be imported.
            NamedQueryNotFoundError: If class doesn't exist or inherit Procedure.
        """
        cls = self._import_class()

        if not isinstance(cls, type) or not issubclass(cls, Procedure):
            from .exceptions import NamedQueryError

            raise NamedQueryError(
                f"'{self._class_name}' must inherit from Procedure. "
                "For async procedures use AsyncProcedureRunner."
            )

        self._procedure_class = cls
        self._params_info = cls.get_parameters()
        return self

    def run(
        self,
        dialect: Any,
        user_params: Optional[Dict[str, Any]] = None,
        transaction_mode: TransactionMode = TransactionMode.AUTO,
        backend: Any = None,
        execute_query: Any = None,
    ) -> ProcedureResult:
        """Execute the procedure.

        Args:
            dialect: The dialect instance.
            user_params: User-provided parameters.
            transaction_mode: Transaction mode (auto, step, none).
            backend: The database backend for transaction control.
            execute_query: Callback for executing queries. Signature:
                (sql: str, params: tuple, stmt_type) -> result.

        Returns:
            ProcedureResult with outputs and logs.
        """
        if not self._procedure_class:
            from .exceptions import NamedQueryError
            raise NamedQueryError("Procedure not loaded. Call load() first.")

        from .exceptions import ProcedureAbortedError
        from .diagram import _DryRunContext

        proc_instance = self._procedure_class()
        user_params = user_params or {}
        for name, value in user_params.items():
            if name in self._params_info:
                setattr(proc_instance, name, value)

        static_ctx = _DryRunContext()
        try:
            self._procedure_class().run(static_ctx)  # type: ignore[arg-type]
        except Exception:
            pass

        def execute_callback(fqn: str, dial: Any, params: Dict[str, Any]) -> Dict[str, Any]:
            _, sql, params_sql = resolve_named_query(fqn, dial, params)
            data, affected_rows = [], 0
            if execute_query and sql:
                raw = execute_query(sql, params_sql, None)
                if raw and raw.data:
                    data = raw.data
                if raw:
                    affected_rows = raw.affected_rows or 0
            return {
                "sql": sql,
                "params_sql": params_sql,
                "data": data,
                "affected_rows": affected_rows,
            }

        ctx = ProcedureContext(dialect, execute_callback, transaction_mode, backend)
        result = ProcedureResult()
        in_transaction = False

        def begin_transaction() -> None:
            nonlocal in_transaction
            if backend and not in_transaction:
                if transaction_mode in (TransactionMode.AUTO, TransactionMode.STEP):
                    backend.begin_transaction()
                in_transaction = True
                ctx._in_transaction = True

        def commit_transaction() -> None:
            nonlocal in_transaction
            if backend and in_transaction:
                backend.commit_transaction()
                in_transaction = False
                ctx._in_transaction = False

        def rollback_transaction() -> None:
            nonlocal in_transaction
            if backend and in_transaction:
                backend.rollback_transaction()
                in_transaction = False
                ctx._in_transaction = False

        ctx._begin_transaction = begin_transaction
        ctx._commit_transaction = commit_transaction
        ctx._rollback_transaction = rollback_transaction

        try:
            if transaction_mode == TransactionMode.AUTO:
                begin_transaction()
            proc_instance.run(ctx)
            if in_transaction and transaction_mode == TransactionMode.AUTO:
                commit_transaction()
        except ProcedureAbortedError as e:
            if transaction_mode != TransactionMode.NONE:
                rollback_transaction()
            result.aborted = True
            result.abort_reason = e.reason
        except Exception as e:
            if transaction_mode != TransactionMode.NONE:
                rollback_transaction()
            result.aborted = True
            result.abort_reason = str(e)

        result.logs = ctx._logs
        result.outputs = [v for v in ctx.bindings.values() if v.get("output")]
        result.static_trace = list(static_ctx._trace)
        result.instance_trace = list(ctx._trace)
        result.dialect_name = type(dialect).__name__ if dialect else None
        result.backend_name = type(backend).__name__ if backend else None
        result.backend_hint = _get_backend_hint_reason(backend)
        return result


class AsyncProcedureRunner(_BaseProcedureRunner):
    """Runner for asynchronous AsyncProcedure subclasses.

    Only accepts classes that inherit from AsyncProcedure.
    For sync procedures use ProcedureRunner.
    """

    def load(self) -> "AsyncProcedureRunner":
        """Load the procedure class.

        Returns:
            self for chaining.

        Raises:
            NamedQueryModuleNotFoundError: If module cannot be imported.
            NamedQueryNotFoundError: If class doesn't exist or inherit AsyncProcedure.
        """
        cls = self._import_class()

        if not isinstance(cls, type) or not issubclass(cls, AsyncProcedure):
            from .exceptions import NamedQueryError

            raise NamedQueryError(
                f"'{self._class_name}' must inherit from AsyncProcedure. "
                "For sync procedures use ProcedureRunner."
            )

        self._procedure_class = cls
        self._params_info = cls.get_parameters()
        return self

    async def run(
        self,
        dialect: Any,
        user_params: Optional[Dict[str, Any]] = None,
        transaction_mode: TransactionMode = TransactionMode.AUTO,
        backend: Any = None,
        execute_query: Any = None,
    ) -> ProcedureResult:
        """Execute the procedure asynchronously.

        Args:
            dialect: The dialect instance.
            user_params: User-provided parameters.
            transaction_mode: Transaction mode (auto, step, none).
            backend: The database backend for transaction control.
            execute_query: Async callback for executing queries. Signature:
                async (sql: str, params: tuple, stmt_type) -> result.

        Returns:
            ProcedureResult with outputs and logs.
        """
        if not self._procedure_class:
            from .exceptions import NamedQueryError
            raise NamedQueryError("Procedure not loaded. Call load() first.")

        from .exceptions import ProcedureAbortedError
        from .diagram import _AsyncDryRunContext

        proc_instance = self._procedure_class()
        user_params = user_params or {}
        for name, value in user_params.items():
            if name in self._params_info:
                setattr(proc_instance, name, value)

        static_ctx = _AsyncDryRunContext()
        try:
            await self._procedure_class().run(static_ctx)  # type: ignore[arg-type]
        except Exception:
            pass

        async def execute_callback(
            fqn: str, dial: Any, params: Dict[str, Any]
        ) -> Dict[str, Any]:
            _, sql, params_sql = resolve_named_query(fqn, dial, params)
            data, affected_rows = [], 0
            if execute_query and sql:
                raw = await execute_query(sql, params_sql, None)
                if raw and raw.data:
                    data = raw.data
                if raw:
                    affected_rows = raw.affected_rows or 0
            return {
                "sql": sql,
                "params_sql": params_sql,
                "data": data,
                "affected_rows": affected_rows,
            }

        ctx = AsyncProcedureContext(
            dialect, execute_callback, transaction_mode, backend
        )
        result = ProcedureResult()
        in_transaction = False

        async def begin_transaction() -> None:
            nonlocal in_transaction
            if backend and not in_transaction:
                if transaction_mode in (TransactionMode.AUTO, TransactionMode.STEP):
                    await backend.begin_transaction()
                in_transaction = True
                ctx._in_transaction = True

        async def commit_transaction() -> None:
            nonlocal in_transaction
            if backend and in_transaction:
                await backend.commit_transaction()
                in_transaction = False
                ctx._in_transaction = False

        async def rollback_transaction() -> None:
            nonlocal in_transaction
            if backend and in_transaction:
                await backend.rollback_transaction()
                in_transaction = False
                ctx._in_transaction = False

        ctx._begin_transaction = begin_transaction
        ctx._commit_transaction = commit_transaction
        ctx._rollback_transaction = rollback_transaction

        try:
            if transaction_mode == TransactionMode.AUTO:
                await begin_transaction()
            await proc_instance.run(ctx)
            if in_transaction and transaction_mode == TransactionMode.AUTO:
                await commit_transaction()
        except ProcedureAbortedError as e:
            if transaction_mode != TransactionMode.NONE:
                await rollback_transaction()
            result.aborted = True
            result.abort_reason = e.reason
        except Exception as e:
            if transaction_mode != TransactionMode.NONE:
                await rollback_transaction()
            result.aborted = True
            result.abort_reason = str(e)

        result.logs = ctx._logs
        result.outputs = [v for v in ctx.bindings.values() if v.get("output")]
        result.static_trace = list(static_ctx._trace)
        result.instance_trace = list(ctx._trace)
        result.dialect_name = type(dialect).__name__ if dialect else None
        result.backend_name = type(backend).__name__ if backend else None
        result.backend_hint = _get_backend_hint_reason(backend)
        return result