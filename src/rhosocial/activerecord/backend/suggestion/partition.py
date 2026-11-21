# src/rhosocial/activerecord/backend/suggestion/partition.py
"""Partition-lifecycle suggestions: values + renderer.

One suggestion GROUP per file. The eight partition suggestion values are pure
frozen dataclasses; the renderer turns a suggestion into an ordered expression
list by asking the dialect for the matching suggestion. Suggestions live in
`backend.suggestion`, never in `backend.expression`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Union

from ..expression.bases import BaseExpression

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect.base import SQLDialectBase
    from ..expression.statements import PartitionByClause


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


class PartitionSuggestionRenderer:
    """Render a partition-lifecycle suggestion into an ordered expression list.

    One renderer for all eight intents; intent-to-protocol mapping is a class
    strategy table. A dialect with no matching support answers the structural
    "no" (no probing, no fallback string).
    """

    _INTENTS: Dict[str, Tuple[str, str]] = {
        "build": ("PartitionBuildSuggestionSupport", "suggest_partition_build"),
        "add": ("PartitionAddSuggestionSupport", "suggest_partition_add"),
        "drop": ("PartitionDropSuggestionSupport", "suggest_partition_drop"),
        "retention": ("PartitionRetentionSuggestionSupport", "suggest_partition_retention"),
        "table_drop": ("PartitionTableDropSuggestionSupport", "suggest_partition_table_drop"),
        "table_alter": ("PartitionTableAlterSuggestionSupport", "suggest_partition_table_alter"),
        "split": ("PartitionSplitSuggestionSupport", "suggest_partition_split"),
        "merge": ("PartitionMergeSuggestionSupport", "suggest_partition_merge"),
    }

    def parts(
        self, dialect: "SQLDialectBase", intent: str, strategy: "PartitionByClause", plan: object
    ) -> Optional[List["BaseExpression"]]:
        from ..dialect import protocols

        try:
            protocol_name, method_name = self._INTENTS[intent]
        except KeyError as exc:
            raise ValueError(f"unknown partition suggestion intent: {intent!r}") from exc
        protocol = getattr(protocols, protocol_name)
        if not isinstance(dialect, protocol):
            return None
        suggestion = getattr(dialect, method_name)(strategy, plan)
        operations = suggestion.operations
        if isinstance(operations, (list, tuple)):
            return [expr for expr in operations if isinstance(expr, BaseExpression)]
        return None  # False (unsupported) or None (no-op)

    def build(self, dialect, strategy, plan):
        return self.parts(dialect, "build", strategy, plan)

    def add(self, dialect, strategy, plan):
        return self.parts(dialect, "add", strategy, plan)

    def drop(self, dialect, strategy, plan):
        return self.parts(dialect, "drop", strategy, plan)

    def retention(self, dialect, strategy, plan):
        return self.parts(dialect, "retention", strategy, plan)

    def table_drop(self, dialect, strategy, plan):
        return self.parts(dialect, "table_drop", strategy, plan)

    def table_alter(self, dialect, strategy, plan):
        return self.parts(dialect, "table_alter", strategy, plan)

    def split(self, dialect, strategy, plan):
        return self.parts(dialect, "split", strategy, plan)

    def merge(self, dialect, strategy, plan):
        return self.parts(dialect, "merge", strategy, plan)
