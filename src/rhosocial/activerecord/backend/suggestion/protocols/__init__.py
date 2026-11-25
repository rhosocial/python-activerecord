# src/rhosocial/activerecord/backend/suggestion/protocols/__init__.py
"""Suggestion protocols -- the second half of the dialect split.

Every ``*SuggestionSupport`` lives here; capability protocols
(``format_*`` / ``supports_*``) live in ``backend.dialect.protocols``.
Core declares only these interfaces and supplies no default implementation:
concrete backends implement them under ``backend.impl.<name>.suggestion``.
"""
from .column_reorder_suggestion import ColumnReorderSuggestionSupport
from .table_constraint_change_suggestion import TableConstraintChangeSuggestionSupport
from .table_index_change_suggestion import TableIndexChangeSuggestionSupport
from .partition_scheme_change_suggestion import PartitionSchemeChangeSuggestionSupport
from .column_type_suggestion import ColumnTypeSuggestionSupport
from .data_adapter_suggestion import DataAdapterSuggestionSupport
from .data_type_suggestion import DataTypeSuggestionSupport
from .index_suggestion import IndexSuggestionSupport
from .generated_value_suggestion import GeneratedValueSuggestionSupport
from .introspection_suggestion import IntrospectionSuggestionSupport
from .json_suggestion import JSONSuggestionSupport
from .string_concatenation_suggestion import StringConcatenationSuggestionSupport
from .create_table_layout_suggestion import CreateTableLayoutSuggestionSupport
from .upsert_suggestion import UpsertSuggestionSupport
from .partition_add_suggestion import PartitionAddSuggestionSupport
from .partition_build_suggestion import PartitionBuildSuggestionSupport
from .partition_drop_suggestion import PartitionDropSuggestionSupport
from .partition_merge_suggestion import PartitionMergeSuggestionSupport
from .partition_retention_suggestion import PartitionRetentionSuggestionSupport
from .partition_split_suggestion import PartitionSplitSuggestionSupport
from .partition_table_alter_suggestion import PartitionTableAlterSuggestionSupport
from .partition_table_drop_suggestion import PartitionTableDropSuggestionSupport

__all__ = [
    "ColumnReorderSuggestionSupport",
    "TableConstraintChangeSuggestionSupport",
    "TableIndexChangeSuggestionSupport",
    "PartitionSchemeChangeSuggestionSupport",
    "ColumnTypeSuggestionSupport",
    "DataAdapterSuggestionSupport",
    "DataTypeSuggestionSupport",
    "IndexSuggestionSupport",
    "GeneratedValueSuggestionSupport",
    "IntrospectionSuggestionSupport",
    "JSONSuggestionSupport",
    "StringConcatenationSuggestionSupport",
    "CreateTableLayoutSuggestionSupport",
    "UpsertSuggestionSupport",
    "PartitionAddSuggestionSupport",
    "PartitionBuildSuggestionSupport",
    "PartitionDropSuggestionSupport",
    "PartitionMergeSuggestionSupport",
    "PartitionRetentionSuggestionSupport",
    "PartitionSplitSuggestionSupport",
    "PartitionTableAlterSuggestionSupport",
    "PartitionTableDropSuggestionSupport",
]
