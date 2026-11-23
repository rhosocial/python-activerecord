# src/rhosocial/activerecord/backend/suggestion/definitions/partition.py
"""Value definitions for the eight partition-lifecycle suggestion methods."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Tuple, Union

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.bases import BaseExpression


@dataclass(frozen=True)
class PartitionBuildSuggestion:
    """Suggested action chain to declare a partitioned table at CREATE time."""
    operations: Union[Tuple["BaseExpression", ...], bool, None] = None


@dataclass(frozen=True)
class PartitionAddSuggestion:
    """Suggested action chain to add/attach a partition to an existing table."""
    operations: Union[Tuple["BaseExpression", ...], bool, None] = None


@dataclass(frozen=True)
class PartitionDropSuggestion:
    """Suggested action chain to drop/detach a partition from a table."""
    operations: Union[Tuple["BaseExpression", ...], bool, None] = None


@dataclass(frozen=True)
class PartitionRetentionSuggestion:
    """Suggested action chain to retire old partitions (by cutoff)."""
    operations: Union[Tuple["BaseExpression", ...], bool, None] = None


@dataclass(frozen=True)
class PartitionTableDropSuggestion:
    """Suggested action chain to drop the whole partitioned table."""
    operations: Union[Tuple["BaseExpression", ...], bool, None] = None


@dataclass(frozen=True)
class PartitionTableAlterSuggestion:
    """Suggested action chain to alter the table's partitioning scheme."""
    operations: Union[Tuple["BaseExpression", ...], bool, None] = None


@dataclass(frozen=True)
class PartitionSplitSuggestion:
    """Suggested action chain to split one partition into two."""
    operations: Union[Tuple["BaseExpression", ...], bool, None] = None


@dataclass(frozen=True)
class PartitionMergeSuggestion:
    """Suggested action chain to merge two adjacent partitions."""
    operations: Union[Tuple["BaseExpression", ...], bool, None] = None


@dataclass(frozen=True)
class PartitionSuggestionOutcome:
    """The consumed result of a partition suggestion, with all three states kept distinct.

    A backend's ``operations`` is ``tuple`` (do this), ``False`` (this backend
    explicitly has no mechanism) or ``None`` (no action needed). Consumers that
    only want the expression list can use :meth:`operations_or_none`, but an
    operator-facing caller must read ``state`` to report "unsupported" rather
    than silently skipping it as "no action". The "no-protocol" state means the
    dialect does not implement the suggestion protocol at all.
    """

    # One of: "actions", "unsupported", "no-action", "no-protocol".
    state: str
    operations: Tuple["BaseExpression", ...] = ()

    @property
    def is_actionable(self) -> bool:
        """True only when there is a concrete expression chain to apply."""
        return self.state == "actions"

    def operations_or_none(self) -> Tuple["BaseExpression", ...] | None:
        """Return the expression chain, or ``None`` for every non-action state.

        Kept for callers that only need "something to apply or not" and want
        the historical ``None``-means-skip behaviour.
        """
        return self.operations if self.state == "actions" else None


__all__ = [
    "PartitionSuggestionOutcome",
    "PartitionBuildSuggestion",
    "PartitionAddSuggestion",
    "PartitionDropSuggestion",
    "PartitionRetentionSuggestion",
    "PartitionTableDropSuggestion",
    "PartitionTableAlterSuggestion",
    "PartitionSplitSuggestion",
    "PartitionMergeSuggestion",
]
