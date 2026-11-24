# src/rhosocial/activerecord/backend/schema/__init__.py
"""
Schema snapshot & diff subsystem for cross-migration schema comparison.

All public symbols are re-exported from ``rhosocial.activerecord.backend.schema``
so callers can use a single import::

    from rhosocial.activerecord.backend.schema import (
        SchemaSnapshot, SchemaDiff, SchemaDiffer,
        SyncSchemaSnapshotBuilder, AsyncSchemaSnapshotBuilder,
    )

The diff data classes here are dialect-neutral payloads and the differ compares
introspection snapshots. Reading *model declarations* is an ActiveRecord-layer
concern and lives in ``rhosocial.activerecord.migration`` — backend stays
 ignorant of AR (layer-separation.md A1/A2).
"""

from .snapshot import SchemaSnapshot, SyncSchemaSnapshotBuilder, AsyncSchemaSnapshotBuilder
from .differ import SchemaDiff, ColumnDiff, TableDiff, SchemaDiffer, ColumnChangeKind

# Legacy — StatementType classification (used by execution layer)
from .statement_type import StatementType

__all__ = [
    "SchemaSnapshot",
    "SyncSchemaSnapshotBuilder",
    "AsyncSchemaSnapshotBuilder",
    "SchemaDiff",
    "ColumnDiff",
    "TableDiff",
    "SchemaDiffer",
    "ColumnChangeKind",
    "StatementType",
]
