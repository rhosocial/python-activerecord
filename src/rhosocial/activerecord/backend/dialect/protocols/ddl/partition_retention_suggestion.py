# src/rhosocial/activerecord/backend/dialect/protocols/ddl/partition_retention_suggestion.py
"""PartitionRetentionSuggestionSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`.

This is a **backend suggestion** capability: the dialect answers how to retire
partitions older than a cutoff for a given partition strategy. It answers only
the "how" question -- the model/database decides *which* partitions are old and
the caller owns the plan; this protocol supplies the ordered action chain the
backend would render to retire them.

It follows the backend-suggestion spec: the protocol is minimal (one
``suggest_*`` method, no ``supports``/``format``), returns an immutable
suggestion value with a tri-state payload, and carries no core mixin default.
"""

from typing import Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import PartitionStrategy
    from ....expression.statements import PartitionRetentionSuggestion


@runtime_checkable
class PartitionRetentionSuggestionSupport(Protocol):
    """A dialect's suggested DDL action chain for retiring old partitions."""

    def suggest_partition_retention(
        self, strategy: "PartitionStrategy", plan: object
    ) -> "PartitionRetentionSuggestion":
        """Suggest how to retire partitions older than the cutoff in ``plan``.

        ``strategy`` is the partition strategy word (``RANGE``, ``LIST``,
        ``HASH``, ...); ``plan`` is the caller-supplied retention plan, kept
        opaque here so the protocol stays engine-neutral. The returned
        suggestion's ``operations`` is an ordered expression chain (apply),
        ``False`` (this strategy has no retirement mechanism on this backend),
        or ``None`` (no action needed).
        """
        ...  # pragma: no cover
