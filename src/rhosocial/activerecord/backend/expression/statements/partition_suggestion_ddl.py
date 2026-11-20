# src/rhosocial/activerecord/backend/expression/statements/partition_suggestion_ddl.py
"""Consume partition-lifecycle suggestions into ordered expression lists.

This is the ``apply(suggest(c, delta))`` bridge for partition DDL. A dialect with
no matching ``*SuggestionSupport`` has no answer: the structural "no" (no probing,
no fallback string), matching ``auto_increment_parts()``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from ..bases import BaseExpression

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase
    from ..statements import PartitionStrategy


def _parts(
    dialect: "SQLDialectBase",
    protocol: type,
    method: str,
    strategy: "PartitionStrategy",
    plan: object,
) -> Optional[List["BaseExpression"]]:
    if not isinstance(dialect, protocol):
        return None
    suggestion = getattr(dialect, method)(strategy, plan)
    operations = suggestion.operations
    if isinstance(operations, (list, tuple)):
        return [expr for expr in operations if isinstance(expr, BaseExpression)]
    return None  # False (unsupported) or None (no-op)


def partition_build_parts(
    dialect: "SQLDialectBase", strategy: "PartitionStrategy", plan: object
) -> Optional[List["BaseExpression"]]:
    """Ordered expressions to declare a partitioned table, or None for no-answer."""
    from ...dialect.protocols import PartitionBuildSuggestionSupport

    return _parts(
        dialect, PartitionBuildSuggestionSupport, "suggest_partition_build", strategy, plan
    )


def partition_add_parts(
    dialect: "SQLDialectBase", strategy: "PartitionStrategy", plan: object
) -> Optional[List["BaseExpression"]]:
    """Ordered expressions to add/attach a partition, or None for no-answer."""
    from ...dialect.protocols import PartitionAddSuggestionSupport

    return _parts(dialect, PartitionAddSuggestionSupport, "suggest_partition_add", strategy, plan)


def partition_drop_parts(
    dialect: "SQLDialectBase", strategy: "PartitionStrategy", plan: object
) -> Optional[List["BaseExpression"]]:
    """Ordered expressions to drop/detach a partition, or None for no-answer."""
    from ...dialect.protocols import PartitionDropSuggestionSupport

    return _parts(dialect, PartitionDropSuggestionSupport, "suggest_partition_drop", strategy, plan)


def partition_retention_parts(
    dialect: "SQLDialectBase", strategy: "PartitionStrategy", plan: object
) -> Optional[List["BaseExpression"]]:
    """Ordered expressions to retire old partitions, or None for no-answer."""
    from ...dialect.protocols import PartitionRetentionSuggestionSupport

    return _parts(
        dialect, PartitionRetentionSuggestionSupport, "suggest_partition_retention", strategy, plan
    )


def partition_table_drop_parts(
    dialect: "SQLDialectBase", strategy: "PartitionStrategy", plan: object
) -> Optional[List["BaseExpression"]]:
    """Ordered expressions to drop the whole partitioned table, or None for no-answer."""
    from ...dialect.protocols import PartitionTableDropSuggestionSupport

    return _parts(
        dialect, PartitionTableDropSuggestionSupport, "suggest_partition_table_drop", strategy, plan
    )


def partition_table_alter_parts(
    dialect: "SQLDialectBase", strategy: "PartitionStrategy", plan: object
) -> Optional[List["BaseExpression"]]:
    """Ordered expressions to alter the table's partitioning scheme, or None for no-answer."""
    from ...dialect.protocols import PartitionTableAlterSuggestionSupport

    return _parts(
        dialect,
        PartitionTableAlterSuggestionSupport,
        "suggest_partition_table_alter",
        strategy,
        plan,
    )


def partition_split_parts(
    dialect: "SQLDialectBase", strategy: "PartitionStrategy", plan: object
) -> Optional[List["BaseExpression"]]:
    """Ordered expressions to split one partition into two, or None for no-answer."""
    from ...dialect.protocols import PartitionSplitSuggestionSupport

    return _parts(
        dialect, PartitionSplitSuggestionSupport, "suggest_partition_split", strategy, plan
    )


def partition_merge_parts(
    dialect: "SQLDialectBase", strategy: "PartitionStrategy", plan: object
) -> Optional[List["BaseExpression"]]:
    """Ordered expressions to merge two adjacent partitions, or None for no-answer."""
    from ...dialect.protocols import PartitionMergeSuggestionSupport

    return _parts(
        dialect, PartitionMergeSuggestionSupport, "suggest_partition_merge", strategy, plan
    )
