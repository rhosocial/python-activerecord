# src/rhosocial/activerecord/migration/outcome.py
"""Frozen, dialect-neutral outcomes for user-facing change planning.

The lower layers deliberately expose pieces: :func:`plan_changes` emits
single-action expressions plus frozen suggestion points, and
:func:`resolve_suggestions` returns a tri-state report. This module composes
them into a single value a migration can inspect and hand to
``ctx.apply_change()``. Nothing here renders SQL or constructs an expression:
the chains are exactly the ones a dialect returned through ``\\mathcal{I}``.

Both outcomes keep every non-applicable point visible. A backend's ``False``
(explicitly unsupported), ``None`` (no answer) and a missing protocol are
different answers and stay different here, so a planner can explain *why* a
point is not being applied instead of silently dropping it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Tuple, Union

from ..backend.dialect.partition_capability import PartitionCapability
from .schema_change import ResolvedSuggestion

#: Reasons for the backend partition-suggestion states, in operator language.
#: No SQL is stored or rendered: these are descriptions, not statements.
PARTITION_STATE_REASONS = {
    "unsupported": "the backend explicitly reported this partition intent is unsupported",
    "no-action": "the backend reported no action is needed",
    "no-protocol": "the backend does not implement the matching partition suggestion protocol",
    "engine-managed": "the engine manages partitioning itself; there is no partition DDL to target",
    "not-supported": "the backend has no table partitioning",
}


@dataclass(frozen=True)
class SchemaChangeOutcome:
    """Result of planning a model-declaration schema change.

    ``statements`` is the executable chain: one core expression per statement,
    already assembled by ``plan_changes`` and ``resolve_suggestions``. The four
    grouped fields hold the *suggestion points* classified by answer state, so
    every point considered during planning is accounted for:

    * ``supported`` — the backend returned an expression chain (applied);
    * ``unsupported`` — the backend answered ``False``;
    * ``no_answer`` — the backend answered ``None``;
    * ``missing`` — the dialect does not implement the matching protocol.

    Direct single-action statements are not suggestion points: they are already
    in ``statements``. The groups are tuples of frozen
    :class:`~rhosocial.activerecord.migration.schema_change.ResolvedSuggestion`
    entries, each retaining its point, protocol and operations.
    """

    statements: Tuple[Any, ...] = ()
    supported: Tuple[ResolvedSuggestion, ...] = ()
    unsupported: Tuple[ResolvedSuggestion, ...] = ()
    no_answer: Tuple[ResolvedSuggestion, ...] = ()
    missing: Tuple[ResolvedSuggestion, ...] = ()

    @property
    def is_complete(self) -> bool:
        """True when no suggestion point was left unresolved."""
        return not (self.unsupported or self.no_answer or self.missing)

    def report(self) -> str:
        """A text description of what can be applied and what cannot, and why.

        Deliberately SQL-free: it names statement counts, point labels and
        protocol names, never rendered SQL.
        """
        lines = [
            f"Schema change plan: {len(self.statements)} executable statement(s).",
            f"  supported: {len(self.supported)} suggestion point(s) resolved by the backend.",
        ]
        for entry in self.supported:
            lines.append(f"    - {entry.point.label} via {entry.protocol}.")
        for entry in self.unsupported:
            lines.append(
                f"  unsupported: {entry.point.label} — "
                f"the backend explicitly reported it cannot address the change "
                f"({entry.protocol})."
            )
        for entry in self.no_answer:
            lines.append(
                f"  no answer: {entry.point.label} — "
                f"the backend returned no answer ({entry.protocol})."
            )
        for entry in self.missing:
            lines.append(
                f"  missing protocol: {entry.point.label} — "
                f"the dialect does not implement {entry.protocol}."
            )
        return "\n".join(lines)


@dataclass(frozen=True)
class PartitionChangeOutcome:
    """Result of planning one partition lifecycle intent.

    ``capability`` is read from the dialect **before** any suggestion is asked.
    When it is ``AUTOMATIC`` or ``UNSUPPORTED`` there is nothing addressable by
    name, so ``operations`` is the sentinel ``False`` and ``state`` names the
    engine-managed / not-supported reason. No backend partition suggestion is
    consulted in those cases, and no DDL is fabricated.

    When the capability is ``NATIVE``, the backend's raw suggestion decides the
    state: ``actions`` (``operations`` is an expression tuple), ``no-action``
    (empty tuple), ``unsupported`` / ``no-protocol`` (``False``).
    """

    capability: PartitionCapability
    operations: Union[Tuple[Any, ...], bool] = False
    state: str = "not-supported"
    intent: str = ""
    reason: str = ""

    @property
    def is_actionable(self) -> bool:
        """True only when there is a concrete expression chain to apply."""
        return self.state == "actions" and bool(self.operations)

    @property
    def is_complete(self) -> bool:
        """True when the intent is fully addressed (or needs no action)."""
        return self.operations is not False

    def report(self) -> str:
        """A text description of the capability, state and applicability."""
        if self.state == "actions" and not self.is_actionable:
            detail = "the backend returned an empty chain; nothing to apply."
        elif self.is_actionable:
            detail = f"{len(self.operations)} operation(s) ready to apply."
        elif self.operations is False:
            detail = f"unaddressable; {self.reason}."
        else:
            detail = f"nothing to apply; {self.reason}."
        return (
            f"Partition change '{self.intent}': capability={self.capability}, "
            f"state={self.state}; {detail}"
        )


__all__ = ["SchemaChangeOutcome", "PartitionChangeOutcome"]
