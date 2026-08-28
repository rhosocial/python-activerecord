# src/rhosocial/activerecord/base/ddl.py
"""
DDL-related re-exports and common types shared between the model layer and
expression layer.

All actual implementation lives in
``backend.expression.statements.ddl_table``; this module exists only so that
``base``-level code can import DDL-related symbols without directly depending
on the ``backend`` package.
"""

from ..backend.expression.statements.ddl_table import (
    ColumnConstraint,
    ColumnConstraintType,
    IndexDefinition,
    TableConstraint,
    TableConstraintType,
    TableOptions,
)


__all__ = [
    "ColumnConstraintType",
    "ColumnConstraint",
    "TableConstraintType",
    "TableConstraint",
    "IndexDefinition",
    "TableOptions",
]