# src/rhosocial/activerecord/backend/dialect/protocols/ddl/partition_add_suggestion.py
"""PartitionAddSuggestionSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`.

This is a **backend suggestion** capability: the dialect answers how to
add/attach a new partition (ADD PARTITION / CREATE TABLE PARTITION OF /
SPLIT RANGE / auto-on-first-row). It answers only the "how" question; the
caller owns the plan/design.
Minimal protocol (one ``suggest_*`` method, no ``supports``/``format``), immutable
tri-state suggestion value, no core mixin default -- per the backend-suggestion spec.
"""

from typing import Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import PartitionStrategy
    from ....suggestion import PartitionAddSuggestion


@runtime_checkable
class PartitionAddSuggestionSupport(Protocol):
    """A dialect's suggested DDL action chain to add/attach a new partition to an existing table."""

    def suggest_partition_add(
        self, strategy: "PartitionStrategy", plan: object
    ) -> "PartitionAddSuggestion":
        """Suggest how to add/attach a new partition to an existing table for ``strategy``.

        ``plan`` is caller-supplied and opaque here to stay engine-neutral.
        The returned ``operations`` is an ordered expression chain (apply),
        ``False`` (this backend has no such mechanism), or ``None`` (no action).
        """
        ...  # pragma: no cover
