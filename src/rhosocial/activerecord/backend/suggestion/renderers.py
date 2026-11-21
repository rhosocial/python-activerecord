# src/rhosocial/activerecord/backend/suggestion/renderers.py
"""Object-oriented renderers that consume backend suggestions into expressions.

This replaces the old pure helper functions (`partition_*_parts`,
`auto_increment_parts`) with classes/methods. A renderer asks the dialect for a
suggestion and turns its tri-state payload into an ordered expression list.
A dialect with no matching suggestion support has no answer: the structural
"no" (no probing, no fallback string).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

from ..expression.bases import BaseExpression

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect.base import SQLDialectBase
    from ..expression.types import DataType
    from .dataclasses import IntegerAutoIncrementColumnSuggestion


class PartitionSuggestionRenderer:
    """Render a partition-lifecycle suggestion into an ordered expression list.

    One renderer for all eight intents; the intent-to-protocol mapping is a
    class-level strategy table, so adding an intent needs no new function.
    """

    # intent -> (protocol attribute name on backend.dialect.protocols, suggest method)
    _INTENTS: Dict[str, Tuple[str, str]] = {
        "build": ("PartitionBuildSuggestionSupport", "suggest_partition_build"),
        "add": ("PartitionAddSuggestionSupport", "suggest_partition_add"),
        "drop": ("PartitionDropSuggestionSupport", "suggest_partition_drop"),
        "retention": ("PartitionRetentionSuggestionSupport", "suggest_partition_retention"),
        "table_drop": ("PartitionTableDropSuggestionSupport", "suggest_partition_table_drop"),
        "table_alter": ("PartitionTableAlterSuggestionSupport", "suggest_partition_table_alter"),
        "split": ("PartitionSplitSuggestionSupport", "suggest_partition_split"),
        "merge": ("PartitionMergeSuggestionSupport", "suggest_partition_merge"),
    }

    def parts(
        self, dialect: "SQLDialectBase", intent: str, strategy, plan: object
    ) -> Optional[List["BaseExpression"]]:
        """Return the expression chain for ``intent``, or None for no-answer."""
        from ..dialect import protocols

        try:
            protocol_name, method_name = self._INTENTS[intent]
        except KeyError as exc:
            raise ValueError(f"unknown partition suggestion intent: {intent!r}") from exc
        protocol = getattr(protocols, protocol_name)
        if not isinstance(dialect, protocol):
            return None
        suggestion = getattr(dialect, method_name)(strategy, plan)
        operations = suggestion.operations
        if isinstance(operations, (list, tuple)):
            return [expr for expr in operations if isinstance(expr, BaseExpression)]
        return None  # False (unsupported) or None (no-op)

    # Convenience methods keep call sites readable without free functions.
    def build(self, dialect, strategy, plan):
        return self.parts(dialect, "build", strategy, plan)

    def add(self, dialect, strategy, plan):
        return self.parts(dialect, "add", strategy, plan)

    def drop(self, dialect, strategy, plan):
        return self.parts(dialect, "drop", strategy, plan)

    def retention(self, dialect, strategy, plan):
        return self.parts(dialect, "retention", strategy, plan)

    def table_drop(self, dialect, strategy, plan):
        return self.parts(dialect, "table_drop", strategy, plan)

    def table_alter(self, dialect, strategy, plan):
        return self.parts(dialect, "table_alter", strategy, plan)

    def split(self, dialect, strategy, plan):
        return self.parts(dialect, "split", strategy, plan)

    def merge(self, dialect, strategy, plan):
        return self.parts(dialect, "merge", strategy, plan)


class IntegerAutoIncrementSuggestionRenderer:
    """Render an integer auto-increment suggestion into ``(type, attributes)``."""

    def parts(self, dialect: "SQLDialectBase", data_type: "DataType") -> Tuple["DataType", List]:
        """Return ``(type, attributes)`` for a generated integer key.

        A dialect with no ``IntegerAutoIncrementColumnSuggestionSupport`` has no
        answer: the type is left alone and no attribute added (structural "no").
        """
        from ..dialect.protocols import IntegerAutoIncrementColumnSuggestionSupport

        if not isinstance(dialect, IntegerAutoIncrementColumnSuggestionSupport):
            return data_type, []
        suggestion: "IntegerAutoIncrementColumnSuggestion" = (
            dialect.suggest_integer_auto_increment_column(data_type)
        )
        attributes = (
            [suggestion.auto_increment]
            if isinstance(suggestion.auto_increment, BaseExpression)
            else []
        )
        return suggestion.type, attributes
