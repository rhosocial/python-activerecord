# src/rhosocial/activerecord/backend/dialect/protocols/ddl/partition_split_suggestion.py
"""PartitionSplitSuggestionSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`.

Backend suggestion capability: the dialect answers how to split one partition into two.
Mechanism examples:
SQL Server SPLIT RANGE; Oracle/MySQL have syntax but no executor;
PostgreSQL has no split.
It answers only "how"; the caller owns the plan. Minimal protocol (one
``suggest_*`` method, no ``supports``/``format``), immutable tri-state value,
no core mixin default -- per the backend-suggestion spec.
"""

from typing import Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import PartitionStrategy
    from ....expression.statements import PartitionSplitSuggestion


@runtime_checkable
class PartitionSplitSuggestionSupport(Protocol):
    """A dialect's suggested DDL action chain to split one partition into two."""

    def suggest_partition_split(
        self, strategy: "PartitionStrategy", plan: object
    ) -> "PartitionSplitSuggestion":
        """Suggest how to split one partition into two for ``strategy``.

        ``plan`` is caller-supplied and opaque to stay engine-neutral.
        ``operations`` is an ordered expression chain (apply), ``False``
        (no such mechanism), or ``None`` (no action).
        """
        ...  # pragma: no cover
