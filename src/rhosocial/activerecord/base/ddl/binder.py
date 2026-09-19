# src/rhosocial/activerecord/base/ddl/binder.py
"""Collect-time dialect binding for declared expressions.

A declared expression may be a lazy ``(dialect) -> expression`` factory or a
ready expression. Binding copies ready expressions so the caller's declared
instance is never mutated.
"""

from __future__ import annotations

from copy import copy
from typing import Any, TYPE_CHECKING

from ...backend.expression.bases import BaseExpression
from ...backend.expression.statements.ddl_table import ColumnConstraint, IndexDefinition

if TYPE_CHECKING:  # pragma: no cover
    from ...backend.dialect import SQLDialectBase


class DialectBinder:
    """Resolves declared expression values against a dialect."""

    def __init__(self, dialect: "SQLDialectBase"):
        self.dialect = dialect

    def bind(self, value: Any) -> Any:
        """Bind a lazy factory or a copy of a ready expression to the dialect.

        Constraints and index definitions carry nested expressions (CHECK
        conditions, DEFAULT values, partial-index predicates), so they are
        rebuilt through their dedicated binders; everything else is copied and
        has its dialect set.
        """
        if callable(value):
            return value(self.dialect)
        if isinstance(value, ColumnConstraint):
            return self.bind_constraint(value)
        if isinstance(value, IndexDefinition):
            return self.bind_index(value)
        bound = copy(value)
        bound.dialect = self.dialect
        return bound

    def bind_index(self, index_def: IndexDefinition) -> IndexDefinition:
        """Copy an ``IndexDefinition`` and bind/resolve its nested predicate."""
        bound = copy(index_def)
        bound.dialect = self.dialect
        if bound.partial_condition is not None:
            bound.partial_condition = self.bind(bound.partial_condition)
        return bound

    def bind_constraint(self, constraint: ColumnConstraint) -> ColumnConstraint:
        """Rebuild a declared ``ColumnConstraint`` bound to the dialect."""
        check_condition = constraint.check_condition
        if check_condition is not None:
            check_condition = self.bind(check_condition)
        default_value = constraint.default_value
        if isinstance(default_value, BaseExpression):
            default_value = self.bind(default_value)
        return ColumnConstraint(
            self.dialect,
            constraint_type=constraint.constraint_type,
            name=constraint.name,
            check_condition=check_condition,
            foreign_key_reference=constraint.foreign_key_reference,
            default_value=default_value,
            is_auto_increment=constraint.is_auto_increment,
            on_delete=constraint.on_delete,
            on_update=constraint.on_update,
            deferrable=constraint.deferrable,
            initially_deferred=constraint.initially_deferred,
            dialect_options=dict(constraint.dialect_options or {}),
            collation=constraint.collation,
            identity=constraint.identity,
        )
