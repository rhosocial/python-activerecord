# src/rhosocial/activerecord/backend/named_query/graph_result.py
"""
Result types for ProcedureGraph execution.

This module defines the result types returned by ProcedureGraph
execution, including execution traces and result data.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .procedure_graph import StepNode, TransactionMode


class StepStatus(str, Enum):
    """Status of a step execution."""

    PENDING = "pending"
    OK = "ok"
    SKIPPED = "skipped"
    FAILED = "failed"
    DRY_RUN = "dry_run"


@dataclass
class StepTraceEntry:
    """Trace entry for a single step execution."""

    name: str
    kind: str
    status: StepStatus = StepStatus.PENDING
    sql: str = ""
    params: tuple = field(default_factory=tuple)
    result: Any = None
    error: Optional[str] = None
    elapsed_ms: float = 0.0
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "status": self.status.value,
            "sql": self.sql,
            "params": self.params,
            "error": self.error,
            "elapsed_ms": self.elapsed_ms,
            "reason": self.reason,
        }


@dataclass
class ProcedureGraphResult:
    """Result of ProcedureGraph execution.

    Attributes:
        steps_done: Steps that executed successfully.
        steps_skipped: Steps that were skipped.
        steps_failed: Steps that failed.
        steps_dry_run: Steps that were dry-run.
        elapsed_ms: Total execution time in milliseconds.
        waves_count: Number of waves executed.
    """

    steps_done: List[StepTraceEntry] = field(default_factory=list)
    steps_skipped: List[StepTraceEntry] = field(default_factory=list)
    steps_failed: List[StepTraceEntry] = field(default_factory=list)
    steps_dry_run: List[StepTraceEntry] = field(default_factory=list)
    elapsed_ms: float = 0.0
    waves_count: int = 0

    @property
    def success(self) -> bool:
        return len(self.steps_failed) == 0

    def failed_steps(self) -> List[StepTraceEntry]:
        return self.steps_failed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "steps_done": [s.to_dict() for s in self.steps_done],
            "steps_skipped": [s.to_dict() for s in self.steps_skipped],
            "steps_failed": [s.to_dict() for s in self.steps_failed],
            "steps_dry_run": [s.to_dict() for s in self.steps_dry_run],
            "elapsed_ms": self.elapsed_ms,
            "waves_count": self.waves_count,
            "success": self.success,
        }

    def to_json(self) -> str:
        import json
        return json.dumps(self.to_dict(), indent=2)

    def to_table(self) -> str:
        lines = []
        lines.append(f"Total waves: {self.waves_count}")
        lines.append(f"Elapsed: {self.elapsed_ms:.2f}ms")
        lines.append(f"Success: {self.success}")
        lines.append("")
        if self.steps_done:
            lines.append("Completed steps:")
            for s in self.steps_done:
                lines.append(f"  [{s.name}] {s.status.value} ({s.elapsed_ms:.2f}ms)")
        if self.steps_skipped:
            lines.append("Skipped steps:")
            for s in self.steps_skipped:
                lines.append(f"  [{s.name}] {s.reason or 'condition_false'}")
        if self.steps_failed:
            lines.append("Failed steps:")
            for s in self.steps_failed:
                lines.append(f"  [{s.name}] {s.error}")
        return "\n".join(lines)