# src/rhosocial/activerecord/ddl/binder.py
"""Dialect binding for declaration-time DDL expression nodes.

DDL declarations are commonly created before a concrete backend is selected.
This module supplies the small binding boundary that turns those declarations
into dialect-associated copies without changing the source declarations.

The binder recognizes lazy expression factories, column constraints, and
index definitions explicitly because those are the declaration forms whose
nested expressions need binding.  Other expression values are shallow-copied
and receive the dialect through their public ``dialect`` attribute.  SQL
formatting, capability checks, and execution remain in the backend layer.
"""

from __future__ import annotations

from copy import copy
from typing import Any, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    ColumnConstraint,
    IndexDefinition,
    TableConstraint,
)

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class DialectBinder:
    """Bind declared DDL values to one SQL dialect.

    A binder is intentionally small and non-mutating for the declaration
    objects it receives.  Known composite declarations are copied and their
    nested expression children are rebound; other values are copied before
    their ``dialect`` attribute is assigned.

    Notes:
        Binding is per expression node.  It does not render SQL, query a
        database, or decide whether a dialect supports a feature.
    """

    def __init__(self, dialect: "SQLDialectBase"):
        """Create a binder for ``dialect``.

        Args:
            dialect: The SQL dialect to attach to bound declaration nodes.
                The dialect is expected to provide the backend expression
                formatting and capability interfaces used later by the
                expression tree.
        """
        self.dialect = dialect

    def bind(self, value: Any) -> Any:
        """Bind a declaration value without mutating its source object.

        A callable is treated as a lazy factory and is invoked with this
        binder's dialect.  ``ColumnConstraint`` and ``IndexDefinition``
        values receive their specialized binding paths, including nested
        predicate/default binding.  Any other value is shallow-copied and
        assigned the dialect.

        Args:
            value: A lazy ``(dialect) -> value`` factory, a declaration
                expression, or another value carrying a writable
                ``dialect`` attribute.

        Returns:
            The factory result, a dialect-bound declaration copy, or a shallow
            copy of another value whose ``dialect`` is this binder's dialect.

        Raises:
            Exception: Errors from a lazy factory, shallow copy, or nested
                declaration binding are propagated unchanged.  This method
                does not add capability validation of its own.

        Notes:
            The general fallback is deliberately shallow.  Only the nested
            expression fields explicitly handled by :meth:`bind_index` and
            :meth:`bind_constraint` are rebound.
        """
        if callable(value):
            resolved = value(self.dialect)
            return self.bind(resolved) if isinstance(resolved, BaseExpression) else resolved
        if isinstance(value, ColumnConstraint):
            return self.bind_constraint(value)
        if isinstance(value, TableConstraint):
            return self.bind_table_constraint(value)
        if isinstance(value, IndexDefinition):
            return self.bind_index(value)
        if isinstance(value, BaseExpression):
            return self._bind_expression(value, {})
        bound = copy(value)
        bound.dialect = self.dialect
        return bound

    def _bind_nested(self, value: Any, memo: dict) -> Any:
        if isinstance(value, BaseExpression):
            return self._bind_expression(value, memo)
        if isinstance(value, list):
            return [self._bind_nested(child, memo) for child in value]
        if isinstance(value, tuple):
            return tuple(self._bind_nested(child, memo) for child in value)
        if isinstance(value, set):
            return {self._bind_nested(child, memo) for child in value}
        if isinstance(value, dict):
            return {
                self._bind_nested(key, memo): self._bind_nested(child, memo)
                for key, child in value.items()
            }
        return value

    def _bind_expression(self, expression: BaseExpression, memo: dict) -> BaseExpression:
        identity = id(expression)
        if identity in memo:
            return memo[identity]
        bound = copy(expression)
        memo[identity] = bound
        bound.dialect = self.dialect
        for name, child in expression.__dict__.items():
            if name == "_dialect":
                continue
            setattr(bound, name, self._bind_nested(child, memo))
        return bound

    def bind_index(self, index_def: IndexDefinition) -> IndexDefinition:
        """Return a dialect-bound copy of an index declaration.

        Args:
            index_def: The declared index definition to copy.  Its name,
                columns, uniqueness, index type, include columns, and
                statement-level options are retained.

        Returns:
            A shallow copy of ``index_def`` with ``dialect`` set to this
            binder's dialect.  A non-``None`` ``partial_condition`` is bound
            as well, including when it is supplied as a lazy factory.

        Notes:
            ``if_not_exists``, ``if_exists``, ``tablespace``, and
            ``concurrent`` are declaration values only at this stage.  The
            selected dialect validates or renders them later.
        """
        bound = self._bind_expression(index_def, {})
        if callable(bound.partial_condition):
            bound.partial_condition = self.bind(bound.partial_condition)
        return bound

    def bind_constraint(self, constraint: ColumnConstraint) -> ColumnConstraint:
        """Rebuild a column constraint with dialect-bound child expressions.

        Args:
            constraint: The declared ``ColumnConstraint`` whose type, name,
                foreign-key reference, auto-increment flag, referential
                actions, and deferrability fields must be preserved.

        Returns:
            A new ``ColumnConstraint`` bound to this binder's dialect.  A
            ``check_condition`` is rebound, and a ``default_value`` is
            rebound only when it is a ``BaseExpression``.

        Notes:
            Scalar defaults and the remaining constraint fields are carried
            over as declared.  The method does not render the constraint or
            ask the dialect whether its features are supported.
        """
        bound = self._bind_expression(constraint, {})
        if callable(bound.check_condition):
            bound.check_condition = self.bind(bound.check_condition)
        if callable(bound.default_value):
            bound.default_value = self.bind(bound.default_value)
        return bound

    def bind_table_constraint(self, constraint: TableConstraint) -> TableConstraint:
        """Return a recursively dialect-bound copy of a table constraint.

        CHECK predicates and backend-owned table-constraint children such as
        PostgreSQL EXCLUDE elements and predicates are rebound without
        mutating the declaration.
        """
        bound = self._bind_expression(constraint, {})
        if callable(bound.check_condition):
            bound.check_condition = self.bind(bound.check_condition)
        if callable(getattr(bound, "where", None)):
            bound.where = self.bind(bound.where)
        return bound


__all__ = ["DialectBinder"]
