# src/rhosocial/activerecord/backend/dialect/protocols/ddl/partition_merge_suggestion.py
"""PartitionMergeSuggestionSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`.

Backend suggestion capability: the dialect answers how to merge two adjacent partitions.
Mechanism examples:
SQL Server MERGE RANGE (data-affecting); Oracle has syntax only;
most backends have no merge.
It answers only "how"; the caller owns the plan. Minimal protocol (one
``suggest_*`` method, no ``supports``/``format``), immutable tri-state value,
no core mixin default -- per the backend-suggestion spec.
"""

from typing import Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import PartitionByClause
    from ....suggestion import PartitionMergeSuggestion


@runtime_checkable
class PartitionMergeSuggestionSupport(Protocol):
    """A dialect's suggested DDL action chain to merge two adjacent partitions."""

    def suggest_partition_merge(
        self, strategy: "PartitionByClause", plan: object
    ) -> "PartitionMergeSuggestion":
        """Suggest how to merge two adjacent partitions for ``strategy``.

        ``plan`` is caller-supplied and opaque to stay engine-neutral.
        ``operations`` is an ordered expression chain (apply), ``False``
        (no such mechanism), or ``None`` (no action).
        """
        ...  # pragma: no cover
