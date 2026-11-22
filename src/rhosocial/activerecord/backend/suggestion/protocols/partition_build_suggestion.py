# src/rhosocial/activerecord/backend/suggestion/protocols/partition_build_suggestion.py
"""PartitionBuildSuggestionSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.suggestion.protocols`.

This is a **backend suggestion** capability: the dialect answers how to
declare a partitioned table at CREATE TABLE time (inline clause, separate
CREATE TABLE statement, or function+scheme chain). It answers only the
"how" question; the caller owns the plan/design.
Minimal protocol (one ``suggest_*`` method, no ``supports``/``format``), immutable
tri-state suggestion value, no core mixin default -- per the backend-suggestion spec.
"""

from typing import Protocol, runtime_checkable, TYPE_CHECKING
from ..definitions import PartitionBuildSuggestion

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.expression.statements import PartitionByClause
    from rhosocial.activerecord.backend.suggestion import PartitionBuildSuggestion


@runtime_checkable
class PartitionBuildSuggestionSupport(Protocol):
    """A dialect's suggested DDL action chain to declare a partitioned table at CREATE TABLE time."""

    def suggest_partition_build(
        self, strategy: "PartitionByClause", plan: object
    ) -> 'PartitionBuildSuggestion':
        """Suggest how to declare a partitioned table at CREATE TABLE time for ``strategy``.

        ``plan`` is caller-supplied and opaque here to stay engine-neutral.
        The returned ``operations`` is an ordered expression chain (apply),
        ``False`` (this backend has no such mechanism), or ``None`` (no action).
        """
        ...  # pragma: no cover
