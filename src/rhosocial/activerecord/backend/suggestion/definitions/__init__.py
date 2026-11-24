# src/rhosocial/activerecord/backend/suggestion/definitions/__init__.py
"""Value definitions for suggestion returns.

One dataclass per ``suggest_*`` protocol method. These describe the *shape* of
a backend's answer; concrete backends construct and return them. Renderers are
deliberately absent -- a suggestion is a complete decision, consumed directly.
"""
from .column_types import ColumnTypeSuggestion, ExtraColumnTypeSuggestion
from .data_adapters import DataAdapterSuggestion, ExtraDataAdapterSuggestion
from .data_types import (
    DataTypeSuggestion,
    ExtraDataTypeSuggestion,
    SubstituteAdviceSuggestion,
    SubstituteTypeSuggestion,
)
from .general import (
    ConcatenationFunctionSuggestion,
    IndexStatementSuggestion,
    IndexTypeSuggestion,
    IntrospectionScopeSuggestion,
    JSONAccessOperatorSuggestion,
    CreateTableLayoutSuggestion,
    UpsertSyntaxSuggestion,
)
from .generated_value import GeneratedValueSuggestion
from .partition import (
    PartitionSuggestionOutcome,
    PartitionAddSuggestion,
    PartitionBuildSuggestion,
    PartitionDropSuggestion,
    PartitionMergeSuggestion,
    PartitionRetentionSuggestion,
    PartitionSplitSuggestion,
    PartitionTableAlterSuggestion,
    PartitionTableDropSuggestion,
)

__all__ = [
    "ColumnTypeSuggestion",
    "ExtraColumnTypeSuggestion",
    "DataAdapterSuggestion",
    "ExtraDataAdapterSuggestion",
    "DataTypeSuggestion",
    "ExtraDataTypeSuggestion",
    "SubstituteAdviceSuggestion",
    "SubstituteTypeSuggestion",
    "ConcatenationFunctionSuggestion",
    "IndexStatementSuggestion",
    "IndexTypeSuggestion",
    "IntrospectionScopeSuggestion",
    "JSONAccessOperatorSuggestion",
    "CreateTableLayoutSuggestion",
    "UpsertSyntaxSuggestion",
    "GeneratedValueSuggestion",
    "PartitionAddSuggestion",
    "PartitionSuggestionOutcome",
    "PartitionBuildSuggestion",
    "PartitionDropSuggestion",
    "PartitionMergeSuggestion",
    "PartitionRetentionSuggestion",
    "PartitionSplitSuggestion",
    "PartitionTableAlterSuggestion",
    "PartitionTableDropSuggestion",
]
