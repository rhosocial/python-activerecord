# src/rhosocial/activerecord/backend/suggestion/__init__.py
"""Backend suggestions: immutable suggestion values + OO renderers.

Suggestions are NOT expressions — this package is deliberately separate from
`backend.expression`, which holds only `BaseExpression` derivatives. The
suggestion protocols live in `backend.dialect.protocols` (the backend abstract
layer holds only protocols); concrete backends implement them under their own
`backend.impl.<name>.suggestion` namespace.
"""

from .dataclasses import (
    IntegerAutoIncrementColumnSuggestion,
    PartitionBuildSuggestion,
    PartitionAddSuggestion,
    PartitionDropSuggestion,
    PartitionRetentionSuggestion,
    PartitionTableDropSuggestion,
    PartitionTableAlterSuggestion,
    PartitionSplitSuggestion,
    PartitionMergeSuggestion,
)
from .renderers import IntegerAutoIncrementSuggestionRenderer, PartitionSuggestionRenderer

__all__ = [
    "IntegerAutoIncrementColumnSuggestion",
    "PartitionBuildSuggestion",
    "PartitionAddSuggestion",
    "PartitionDropSuggestion",
    "PartitionRetentionSuggestion",
    "PartitionTableDropSuggestion",
    "PartitionTableAlterSuggestion",
    "PartitionSplitSuggestion",
    "PartitionMergeSuggestion",
    "IntegerAutoIncrementSuggestionRenderer",
    "PartitionSuggestionRenderer",
]
