# src/rhosocial/activerecord/backend/dialect/protocols/ddl/partition_drop_suggestion.py
"""PartitionDropSuggestionSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`.

This is a **backend suggestion** capability: the dialect answers how to
drop/detach a partition (DROP PARTITION / DROP TABLE child / MERGE RANGE /
DROP PARTITION ID). It answers only the "how" question; the caller owns the
plan/design.
Minimal protocol (one ``suggest_*`` method, no ``supports``/``format``), immutable
tri-state suggestion value, no core mixin default -- per the backend-suggestion spec.
"""

from typing import Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import PartitionStrategy
    from ....expression.statements import PartitionDropSuggestion


@runtime_checkable
class PartitionDropSuggestionSupport(Protocol):
    """A dialect's suggested DDL action chain to drop/detach a partition from a table."""

    def suggest_partition_drop(
        self, strategy: "PartitionStrategy", plan: object
    ) -> "PartitionDropSuggestion":
        """Suggest how to drop/detach a partition from a table for ``strategy``.

        ``plan`` is caller-supplied and opaque here to stay engine-neutral.
        The returned ``operations`` is an ordered expression chain (apply),
        ``False`` (this backend has no such mechanism), or ``None`` (no action).
        """
        ...  # pragma: no cover
