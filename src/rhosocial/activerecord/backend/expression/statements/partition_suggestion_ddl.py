# src/rhosocial/activerecord/backend/expression/statements/partition_suggestion_ddl.py
"""Consume a partition-retention suggestion into an ordered expression list.

This is the ``apply(suggest(c, delta))`` bridge for partition retirement. A
dialect with no ``PartitionRetentionSuggestionSupport`` has no answer: it is the
structural "no" (no probing, no fallback string), matching
``auto_increment_parts()``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from ..bases import BaseExpression

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase
    from ..statements import PartitionStrategy


def partition_retention_parts(
    dialect: "SQLDialectBase", strategy: "PartitionStrategy", plan: object
) -> Optional[List["BaseExpression"]]:
    """Return the ordered expression chain for retiring old partitions.

    ``None`` here means either "no suggestion capability" (structural no) or
    "no action needed" (the suggestion's ``operations`` is ``None``). ``False``
    from the suggestion is also returned as ``None`` so callers get a uniform
    "nothing to apply" answer; use the suggestion directly when the distinction
    between unsupported and no-op matters.
    """
    from ...dialect.protocols import PartitionRetentionSuggestionSupport

    if not isinstance(dialect, PartitionRetentionSuggestionSupport):
        return None
    suggestion = dialect.suggest_partition_retention(strategy, plan)
    operations = suggestion.operations
    if isinstance(operations, (list, tuple)):
        return [expr for expr in operations if isinstance(expr, BaseExpression)]
    return None  # False (unsupported) or None (no-op)
