# src/rhosocial/activerecord/backend/suggestion/protocols/partition_table_drop_suggestion.py
"""PartitionTableDropSuggestionSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.suggestion.protocols`.

Backend suggestion capability: the dialect answers how to drop the whole partitioned table.
Mechanism examples:
DROP TABLE on most backends; SQL Server drops function and scheme
in order to avoid moving every row.
It answers only "how"; the caller owns the plan. Minimal protocol (one
``suggest_*`` method, no ``supports``/``format``), immutable tri-state value,
no core mixin default -- per the backend-suggestion spec.
"""

from typing import Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.expression.statements import PartitionByClause
    from rhosocial.activerecord.backend.suggestion import PartitionTableDropSuggestion


@runtime_checkable
class PartitionTableDropSuggestionSupport(Protocol):
    """A dialect's suggested DDL action chain to drop the whole partitioned table."""

    def suggest_partition_table_drop(
        self, strategy: "PartitionByClause", plan: object
    ) -> "PartitionTableDropSuggestion":
        """Suggest how to drop the whole partitioned table for ``strategy``.

        ``plan`` is caller-supplied and opaque to stay engine-neutral.
        ``operations`` is an ordered expression chain (apply), ``False``
        (no such mechanism), or ``None`` (no action).
        """
        ...  # pragma: no cover
