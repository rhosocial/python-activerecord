# src/rhosocial/activerecord/backend/suggestion/__init__.py
"""Backend suggestions: immutable values + OO renderers, one target group per file.

Suggestions are NOT expressions — this package is separate from `backend.expression`.
Suggestion protocols live in `backend.dialect.protocols`; concrete backends implement
them under `backend.impl.<name>.suggestion`.
"""

from .integer_auto_increment import (
    IntegerAutoIncrementColumnSuggestion,
    IntegerAutoIncrementSuggestionRenderer,
)
from .partition import (
    PartitionBuildSuggestion,
    PartitionAddSuggestion,
    PartitionDropSuggestion,
    PartitionRetentionSuggestion,
    PartitionTableDropSuggestion,
    PartitionTableAlterSuggestion,
    PartitionSplitSuggestion,
    PartitionMergeSuggestion,
    PartitionSuggestionRenderer,
)

__all__ = [
    "IntegerAutoIncrementColumnSuggestion",
    "IntegerAutoIncrementSuggestionRenderer",
    "PartitionBuildSuggestion",
    "PartitionAddSuggestion",
    "PartitionDropSuggestion",
    "PartitionRetentionSuggestion",
    "PartitionTableDropSuggestion",
    "PartitionTableAlterSuggestion",
    "PartitionSplitSuggestion",
    "PartitionMergeSuggestion",
    "PartitionSuggestionRenderer",
]
