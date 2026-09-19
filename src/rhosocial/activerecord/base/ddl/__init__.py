# src/rhosocial/activerecord/base/ddl/__init__.py
"""DDL derivation from ActiveRecord model definitions."""

from .annotations import DDLAnnotationHandler, DDLFieldMetadata
from .binder import DialectBinder
from .contracts import COLUMN_CONTRACTS, TABLE_CONTRACTS, DeclarationContract
from .deriver import TableDDLDeriver
from .mixin import DDLMixin
from .options import ColumnOptions
from .selector import DialectExpressionSelector, ExpressionOwnership
from .types import ColumnTypeResolutionError, ColumnTypeResolver, PythonTypeMapping

__all__ = [
    "DDLAnnotationHandler",
    "DDLFieldMetadata",
    "DialectBinder",
    "COLUMN_CONTRACTS",
    "TABLE_CONTRACTS",
    "DeclarationContract",
    "TableDDLDeriver",
    "DDLMixin",
    "ColumnOptions",
    "DialectExpressionSelector",
    "ExpressionOwnership",
    "ColumnTypeResolutionError",
    "ColumnTypeResolver",
    "PythonTypeMapping",
]
