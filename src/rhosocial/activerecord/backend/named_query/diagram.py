# src/rhosocial/activerecord/backend/named_query/diagram.py
"""
Procedure diagram visualization support.

This module provides Mermaid diagram generation for named procedures:
- Static diagrams: Generated via dry-run (no DB required)
- Instance diagrams: Generated from actual execution results

Usage:
    # Static diagram (no DB)
    print(MyProcedure.static_diagram("flowchart"))

    # Instance diagram (after execution)
    result = runner.run(dialect, backend)
    print(result.diagram("sequence", procedure_name="MyProcedure"))
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type

from .procedure import (
    AsyncProcedure,
    ParallelStep,
    Procedure,
    StepKind,
    TraceEntry,
    TransactionMode,
)

if TYPE_CHECKING:
    from .procedure import ProcedureResult

_STATUS_COLOR: Dict[str, str] = {
    "ok":      "fill:#a8d8a8,stroke:#6aad6a",
    "error":   "fill:#f4a4a4,stroke:#d96b6b",
    "skipped": "fill:#e8e8e8,stroke:#b0b0b0",
}
_UNEXECUTED_COLOR = "fill:#d8d8d8,stroke:#aaaaaa,color:#888888"
_NEUTRAL_COLOR    = "fill:#ddeeff,stroke:#7799cc"


class _DryRunContext:
    def __init__(self) -> None:
        self._trace: List[TraceEntry] = []
        self._index: int = 0
        self._bindings: Dict[str, Any] = {}
        self.dialect: Any = None
        self.transaction_mode = TransactionMode.AUTO
        self._in_transaction: bool = False

    def get(self, key: str, default: Any = None) -> Any:
        return self._bindings.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self._bindings.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        self._bindings[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self._bindings

    def scalar(self, var_name: str, column: str) -> Any:
        if var_name not in self._bindings:
            return None
        data = self._bindings[var_name].get("data", [])
        if not data:
            return None
        first_row = data[0]
        return first_row.get(column)

    def rows(self, var_name: str):
        if var_name not in self._bindings:
            return
        data = self._bindings[var_name].get("data", [])
        yield from data

    def bind(self, name: str, data: Any) -> None:
        if data is None:
            self._bindings[name] = {"data": []}
        elif isinstance(data, list):
            self._bindings[name] = {"data": data}
        elif isinstance(data, dict):
            self._bindings[name] = {"data": [data]}
        else:
            self._bindings[name] = {"data": [data]}

    def execute(
        self,
        qualified_name: str,
        params: Optional[Dict[str, Any]] = None,
        bind: Optional[str] = None,
        output: bool = False,
    ) -> Any:
        self._trace.append(TraceEntry(
            kind=StepKind.SINGLE,
            index=self._index,
            qualified_name=qualified_name,
            params={},
            bind=bind,
            output=output,
        ))
        self._index += 1
        result_data = {
            "qualified_name": qualified_name,
            "params": params or {},
            "bind": bind,
            "output": output,
            "data": [],
            "affected_rows": 0,
        }
        if bind:
            self._bindings[bind] = result_data
        return result_data

    def parallel(
        self,
        *steps: ParallelStep,
        max_concurrency: Optional[int] = None,
    ) -> None:
        sub_entries = [
            TraceEntry(
                kind=StepKind.SINGLE,
                index=i,
                qualified_name=s.qualified_name,
                params={},
                bind=s.bind,
                output=s.output,
            )
            for i, s in enumerate(steps)
        ]
        self._trace.append(TraceEntry(
            kind=StepKind.PARALLEL,
            index=self._index,
            sub_steps=sub_entries,
            max_concurrency=max_concurrency,
        ))
        self._index += 1
        for s in steps:
            if s.bind:
                self._bindings[s.bind] = None

    def begin_transaction(self) -> None:
        pass

    def commit_transaction(self) -> None:
        pass

    def rollback_transaction(self) -> None:
        pass

    def log(self, message: str, level: str = "INFO", step: str = None) -> None:
        pass

    def abort(self, procedure_name: str = "", reason: str = "") -> None:
        pass


class _AsyncDryRunContext:
    def __init__(self) -> None:
        self._trace: List[TraceEntry] = []
        self._index: int = 0
        self._bindings: Dict[str, Any] = {}
        self.dialect: Any = None
        self.transaction_mode = TransactionMode.AUTO
        self._in_transaction: bool = False

    def get(self, key: str, default: Any = None) -> Any:
        return self._bindings.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self._bindings.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        self._bindings[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self._bindings

    async def scalar(self, var_name: str, column: str) -> Any:
        if var_name not in self._bindings:
            return None
        data = self._bindings[var_name].get("data", [])
        if not data:
            return None
        first_row = data[0]
        return first_row.get(column)

    async def rows(self, var_name: str):
        if var_name not in self._bindings:
            return
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

    async def execute(
        self,
        qualified_name: str,
        params: Optional[Dict[str, Any]] = None,
        bind: Optional[str] = None,
        output: bool = False,
    ) -> Any:
        self._trace.append(TraceEntry(
            kind=StepKind.SINGLE,
            index=self._index,
            qualified_name=qualified_name,
            params={},
            bind=bind,
            output=output,
        ))
        self._index += 1
        result_data = {
            "qualified_name": qualified_name,
            "params": params or {},
            "bind": bind,
            "output": output,
            "data": [],
            "affected_rows": 0,
        }
        if bind:
            self._bindings[bind] = result_data
        return result_data

    async def parallel(
        self,
        *steps: ParallelStep,
        max_concurrency: Optional[int] = None,
    ) -> None:
        sub_entries = [
            TraceEntry(
                kind=StepKind.SINGLE,
                index=i,
                qualified_name=s.qualified_name,
                params={},
                bind=s.bind,
                output=s.output,
            )
            for i, s in enumerate(steps)
        ]
        self._trace.append(TraceEntry(
            kind=StepKind.PARALLEL,
            index=self._index,
            sub_steps=sub_entries,
            max_concurrency=max_concurrency,
        ))
        self._index += 1
        for s in steps:
            if s.bind:
                self._bindings[s.bind] = None

    async def begin_transaction(self) -> None:
        pass

    async def commit_transaction(self) -> None:
        pass

    async def rollback_transaction(self) -> None:
        pass

    async def log(self, message: str, level: str = "INFO", step: str = None) -> None:
        pass

    async def abort(self, procedure_name: str = "", reason: str = "") -> None:
        pass


class ProcedureDiagram:
    def __init__(
        self,
        static_trace: List[TraceEntry],
        instance_trace: Optional[List[TraceEntry]] = None,
        dialect_name: Optional[str] = None,
        backend_name: Optional[str] = None,
        backend_hint: Optional[str] = None,
        procedure_name: str = "Procedure",
    ) -> None:
        self.static_trace   = static_trace
        self.instance_trace = instance_trace
        self.dialect_name   = dialect_name
        self.backend_name   = backend_name
        self.backend_hint   = backend_hint
        self.procedure_name = procedure_name

    @property
    def is_static(self) -> bool:
        return self.instance_trace is None

    @classmethod
    def from_result(
        cls,
        result: "ProcedureResult",
        procedure_name: str = "Procedure",
    ) -> "ProcedureDiagram":
        return cls(
            static_trace=result.static_trace,
            instance_trace=result.instance_trace,
            dialect_name=result.dialect_name,
            backend_name=result.backend_name,
            backend_hint=result.backend_hint,
            procedure_name=procedure_name,
        )

    @classmethod
    def from_procedure(
        cls,
        procedure_cls: Type[Procedure],
        dialect: Any = None,
    ) -> "ProcedureDiagram":
        ctx = _DryRunContext()
        try:
            procedure_cls().run(ctx)  # type: ignore[arg-type]
        except Exception:
            pass
        return cls(
            static_trace=ctx._trace,
            instance_trace=None,
            dialect_name=type(dialect).__name__ if dialect else None,
            procedure_name=procedure_cls.__name__,
        )

    @classmethod
    async def from_async_procedure(
        cls,
        procedure_cls: Type[AsyncProcedure],
        dialect: Any = None,
    ) -> "ProcedureDiagram":
        ctx = _AsyncDryRunContext()
        try:
            await procedure_cls().run(ctx)  # type: ignore[arg-type]
        except Exception:
            pass
        return cls(
            static_trace=ctx._trace,
            instance_trace=None,
            dialect_name=type(dialect).__name__ if dialect else None,
            procedure_name=procedure_cls.__name__,
        )

    def to_mermaid(self, kind: str = "flowchart") -> str:
        if kind == "flowchart":
            return self._render_flowchart()
        if kind == "sequence":
            return self._render_sequence()
        raise ValueError(f"Unknown diagram kind: {kind!r}")

    def _build_executed_index(self) -> Dict[str, TraceEntry]:
        if self.instance_trace is None:
            return {}
        index: Dict[str, TraceEntry] = {}
        for entry in self.instance_trace:
            if entry.kind == StepKind.SINGLE and entry.qualified_name:
                index[entry.qualified_name] = entry
            elif entry.kind == StepKind.PARALLEL:
                for sub in entry.sub_steps:
                    if sub.qualified_name:
                        index[sub.qualified_name] = sub
        return index

    def _node_label(self, entry: TraceEntry, ex: Optional[TraceEntry]) -> str:
        name = entry.qualified_name or "?"
        if ex is not None and ex.elapsed_ms is not None:
            return f"{name}\\n({ex.elapsed_ms:.1f} ms)"
        return name

    def _title_label(self) -> str:
        parts = [self.procedure_name]
        if self.backend_name:
            parts.append(f"Backend: {self.backend_name}")
        elif self.dialect_name:
            parts.append(f"Dialect: {self.dialect_name}")
        return "\\n".join(parts)

    def _end_label(self) -> str:
        if self.instance_trace is None:
            return "End"
        total = sum(
            e.elapsed_ms for e in self.instance_trace if e.elapsed_ms is not None
        )
        return f"End\\n{len(self.instance_trace)} steps · {total:.1f} ms"

    def _render_flowchart(self) -> str:
        lines: List[str] = []
        styles: List[str] = []
        executed = self._build_executed_index()

        if self.is_static:
            lines.append(
                "%% [Static diagram — generated by dry-run."
                " Conditional branches may be incomplete.]"
            )
        if self.dialect_name and not self.backend_name:
            lines.append(f"%% Dialect: {self.dialect_name}")
        if self.backend_hint:
            lines.append(f"%% Backend hint: {self.backend_hint}")

        lines.append("flowchart TD")
        lines.append(f'    START(["{self._title_label()}"])')

        for entry in self.static_trace:
            if entry.kind == StepKind.SINGLE:
                nid = f"n{entry.index}"
                ex  = executed.get(entry.qualified_name or "")
                lines.append(f'    {nid}["{self._node_label(entry, ex)}"]')
                if self.is_static:
                    styles.append(f"    style {nid} {_NEUTRAL_COLOR}")
                elif ex is not None:
                    styles.append(
                        f"    style {nid} "
                        f"{_STATUS_COLOR.get(ex.status or 'ok', _NEUTRAL_COLOR)}"
                    )
                else:
                    styles.append(f"    style {nid} {_UNEXECUTED_COLOR}")

            elif entry.kind == StepKind.PARALLEL:
                lines.append(f"    fork{entry.index}{{ }}")
                lines.append(f"    join{entry.index}{{ }}")
                for sub in entry.sub_steps:
                    nid = f"n{entry.index}_{sub.index}"
                    ex  = executed.get(sub.qualified_name or "")
                    lines.append(f'    {nid}["{self._node_label(sub, ex)}"]')
                    if self.is_static:
                        styles.append(f"    style {nid} {_NEUTRAL_COLOR}")
                    elif ex is not None:
                        styles.append(
                            f"    style {nid} "
                            f"{_STATUS_COLOR.get(ex.status or 'ok', _NEUTRAL_COLOR)}"
                        )
                    else:
                        styles.append(f"    style {nid} {_UNEXECUTED_COLOR}")

        lines.append(f'    END(["{self._end_label()}"])')
        lines.append("")

        prev = "START"
        for entry in self.static_trace:
            if entry.kind == StepKind.SINGLE:
                nid = f"n{entry.index}"
                lines.append(f"    {prev} --> {nid}")
                prev = nid
            elif entry.kind == StepKind.PARALLEL:
                sub_ids = [f"n{entry.index}_{s.index}" for s in entry.sub_steps]
                lines.append(f"    {prev} --> fork{entry.index}")
                lines.append(f"    fork{entry.index} --> {' & '.join(sub_ids)}")
                lines.append(f"    {' & '.join(sub_ids)} --> join{entry.index}")
                prev = f"join{entry.index}"

        lines.append(f"    {prev} --> END")
        lines.append("")
        lines.extend(styles)
        return "\n".join(lines)

    def _render_sequence(self) -> str:
        lines: List[str] = []
        executed = self._build_executed_index()

        if self.is_static:
            lines.append(
                "%% [Static diagram — generated by dry-run."
                " Conditional branches may be incomplete.]"
            )

        lines.append("sequenceDiagram")
        lines.append("    participant Runner")
        lines.append("    participant DB")

        if self.backend_name:
            note = f"Backend: {self.backend_name}"
            if self.dialect_name:
                note += f"<br/>Dialect: {self.dialect_name}"
            lines.append(f"    note over Runner: {note}")
        elif self.dialect_name:
            lines.append(f"    note over Runner: Dialect: {self.dialect_name}")

        lines.append("")

        for entry in self.static_trace:
            if entry.kind == StepKind.SINGLE:
                lines.extend(self._seq_single(entry, executed, indent=4))
                lines.append("")
            elif entry.kind == StepKind.PARALLEL:
                for i, sub in enumerate(entry.sub_steps):
                    keyword = "par" if i == 0 else "and"
                    hint = (
                        f"  %% max_concurrency={entry.max_concurrency}"
                        if i == 0 and entry.max_concurrency else ""
                    )
                    lines.append(
                        f"    {keyword} "
                        f"{sub.qualified_name or f'step_{sub.index}'}{hint}"
                    )
                    lines.extend(self._seq_single(sub, executed, indent=8))
                lines.append("    end")
                lines.append("")

        if not self.is_static and self.instance_trace is not None:
            total = sum(
                e.elapsed_ms for e in self.instance_trace if e.elapsed_ms is not None
            )
            ok_n  = sum(1 for e in self.instance_trace if e.status == "ok")
            err_n = sum(1 for e in self.instance_trace if e.status == "error")
            summary = f"✓ {ok_n} ok"
            if err_n:
                summary += f" · ✗ {err_n} error"
            summary += f" · {total:.1f} ms total"
            lines.append(f"    note over Runner: {summary}")

        return "\n".join(lines)

    def _seq_single(
        self,
        entry: TraceEntry,
        executed: Dict[str, TraceEntry],
        indent: int,
    ) -> List[str]:
        pad  = " " * indent
        name = entry.qualified_name or "?"
        ex   = executed.get(name)
        lines: List[str] = []

        if ex is not None:
            if ex.status == "error":
                lines.append(f"{pad}Runner-xDB: {name}")
                elapsed = f" [{ex.elapsed_ms:.1f} ms]" if ex.elapsed_ms else ""
                lines.append(
                    f"{pad}note right of Runner: ✗ {ex.error or 'error'}{elapsed}"
                )
            else:
                lines.append(f"{pad}Runner->>DB: {name}")
                reply   = f"→ {entry.bind}" if entry.bind else "ok"
                elapsed = f"  [{ex.elapsed_ms:.1f} ms]" if ex.elapsed_ms else ""
                lines.append(f"{pad}DB-->>Runner: {reply}{elapsed}")
        else:
            if self.is_static:
                lines.append(f"{pad}Runner->>DB: {name}")
                reply = f"→ {entry.bind}" if entry.bind else "ok"
                lines.append(f"{pad}DB-->>Runner: {reply}")
            else:
                lines.append(f"{pad}Runner-->>DB: {name}")
                lines.append(f"{pad}note right of Runner: [not executed]")

        return lines