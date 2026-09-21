# src/rhosocial/activerecord/base/ddl/__init__.py
"""DDL derivation from ActiveRecord model definitions."""

from .annotations import DDLAnnotationHandler, DDLFieldMetadata
from .attributes import ColumnAttribute, IdentityAttribute
from .binder import DialectBinder
from .contracts import COLUMN_CONTRACTS, TABLE_CONTRACTS, DeclarationContract
from .deriver import TableDDLDeriver
from .mixin import DDLMixin
from .options import ColumnOptions
from .params import StatementParamSchema, StatementContractError
from .plans import DDLPlan
from .selector import (
    DeclarationSelectionError,
    DialectExpressionSelector,
    ExpressionOwnership,
)
from .types import ColumnTypeResolutionError, ColumnTypeResolver, PythonTypeMapping

__all__ = [
    "DDLAnnotationHandler",
    "DDLFieldMetadata",
    "DialectBinder",
    "ColumnAttribute",
    "IdentityAttribute",
    "COLUMN_CONTRACTS",
    "TABLE_CONTRACTS",
    "DeclarationContract",
    "TableDDLDeriver",
    "DDLMixin",
    "ColumnOptions",
    "StatementParamSchema",
    "StatementContractError",
    "DDLPlan",
    "DeclarationSelectionError",
    "DialectExpressionSelector",
    "ExpressionOwnership",
    "ColumnTypeResolutionError",
    "ColumnTypeResolver",
    "PythonTypeMapping",
]
