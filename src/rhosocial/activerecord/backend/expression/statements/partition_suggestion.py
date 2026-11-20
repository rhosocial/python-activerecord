# src/rhosocial/activerecord/backend/expression/statements/partition_suggestion.py
"""Backend *suggestion* data classes for partition lifecycle operations.

A suggestion is the backend's answer to "how should this partition operation be
done here". It is not an expression node and not a statement: it is a small
immutable value the framework reads and turns into an ordered DDL action chain.
The name carries ``Suggestion`` (not ``Operation``) to mark it as a
backend-suggested value, matching ``IntegerAutoIncrementColumnSuggestion``.

Tri-state ``operations`` (identical across all four points):
- an ordered tuple of expression nodes -- apply them in order;
- ``False`` -- this backend has no such mechanism for the strategy;
- ``None`` -- no action needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Tuple, Union

if TYPE_CHECKING:  # pragma: no cover
    from ..bases import BaseExpression


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
