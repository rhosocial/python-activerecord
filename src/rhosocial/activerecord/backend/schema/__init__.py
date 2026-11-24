# src/rhosocial/activerecord/backend/schema/__init__.py
"""
Schema snapshot & diff subsystem for cross-migration schema comparison.

All public symbols are re-exported from ``rhosocial.activerecord.backend.schema``
so callers can use a single import::

    from rhosocial.activerecord.backend.schema import (
        SchemaSnapshot, SchemaDiff, SchemaDiffer,
        SyncSchemaSnapshotBuilder, AsyncSchemaSnapshotBuilder,
    )
"""

from .snapshot import SchemaSnapshot, SyncSchemaSnapshotBuilder, AsyncSchemaSnapshotBuilder
from .differ import SchemaDiff, ColumnDiff, TableDiff, SchemaDiffer, ColumnChangeKind
from .declaration_diff import (
    DeclarationDiffer, FieldDeclaration, TableDeclaration,
    field_declaration, table_declaration,
)

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
    "DeclarationDiffer",
    "FieldDeclaration",
    "TableDeclaration",
    "field_declaration",
    "table_declaration",
    "StatementType",
]
