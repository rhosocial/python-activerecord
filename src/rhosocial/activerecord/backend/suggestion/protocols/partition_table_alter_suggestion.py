# src/rhosocial/activerecord/backend/suggestion/protocols/partition_table_alter_suggestion.py
"""PartitionTableAlterSuggestionSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.suggestion.protocols`.

Backend suggestion capability: the dialect answers how to alter the whole table's partitioning scheme.
Mechanism examples:
MySQL REMOVE PARTITIONING / COALESCE; most backends have no
equivalent, so the answer may be a rebuild-table chain.
It answers only "how"; the caller owns the plan. Minimal protocol (one
``suggest_*`` method, no ``supports``/``format``), immutable tri-state value,
no core mixin default -- per the backend-suggestion spec.
"""

from typing import Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.expression.statements import PartitionByClause
    from rhosocial.activerecord.backend.suggestion import PartitionTableAlterSuggestion


@runtime_checkable
class PartitionTableAlterSuggestionSupport(Protocol):
    """A dialect's suggested DDL action chain to alter the whole table's partitioning scheme."""

    def suggest_partition_table_alter(
        self, strategy: "PartitionByClause", plan: object
    ) -> "PartitionTableAlterSuggestion":
        """Suggest how to alter the whole table's partitioning scheme for ``strategy``.

        ``plan`` is caller-supplied and opaque to stay engine-neutral.
        ``operations`` is an ordered expression chain (apply), ``False``
        (no such mechanism), or ``None`` (no action).
        """
        ...  # pragma: no cover
