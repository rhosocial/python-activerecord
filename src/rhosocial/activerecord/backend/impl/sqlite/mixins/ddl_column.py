# src/rhosocial/activerecord/backend/impl/sqlite/mixins/ddl_column.py
"""
SQLite-specific Ddl Column implementation.

This module provides the SQLiteDDLColumnMixin class.
"""

from typing import Tuple, TYPE_CHECKING
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.expression.statements.ddl_table import (
        ColumnConstraint,
        ColumnDefinition,
        DefaultValueClause,
    )


class SQLiteDDLColumnMixin:
    """SQLite-specific column constraint and column definition formatting.

    What is left here is what SQLite genuinely spells differently: the
    ``AUTOINCREMENT`` tail on its primary-key grammar, booleans inlined as
    ``1``/``0``, and the placement rules only the column definition can
    check. Everything else the core already renders — its IF [NOT] EXISTS
    probes default to the answers SQLite gives, so the shared formatters
    refuse those qualifiers without a per-dialect copy.
    """

    def format_primary_key_constraint(self, constraint: "ColumnConstraint") -> Tuple[str, tuple]:
        """SQLite's PRIMARY KEY, which is where ``AUTOINCREMENT`` lives.

        ``AUTOINCREMENT`` is part of SQLite's primary-key grammar -- it follows
        ``PRIMARY KEY`` and nowhere else -- so it is appended here rather than
        in the shared renderer, which knows nothing about it.

        Placement is checked in :meth:`format_column_definition`, because
        whether the column is an ``INTEGER`` is a fact only the column
        definition holds.
        """
        sql, params = super().format_primary_key_constraint(constraint)
        if constraint.is_auto_increment:
            sql += " AUTOINCREMENT"
        return sql, params

    def format_default_value_clause(self, expr: "DefaultValueClause") -> Tuple[str, tuple]:
        """Format the value clause of a DEFAULT constraint (SQLite).

        SQLite does not support parameterized DEFAULT in CREATE TABLE, so
        values are inlined directly. Booleans render as ``1``/``0`` (SQLite
        has no native boolean literal); everything else delegates to the
        generic implementation.
        """
        from rhosocial.activerecord.backend.expression import bases

        value = expr.value
        if isinstance(value, bool) and not isinstance(value, bases.BaseExpression):
            return f"{'1' if value else '0'}", ()
        return super().format_default_value_clause(expr)

    def format_column_definition(self, col_def: "ColumnDefinition") -> Tuple[str, tuple]:
        """Format a column definition for SQLite.

        SQLite needs no column-definition grammar of its own. What it does need
        is decided before delegating: an inline comment is refused (SQLite has
        no column-comment mechanism at all), and ``AUTOINCREMENT`` is refused
        anywhere but on an ``INTEGER`` primary key. Both are checked here rather
        than in the renderer because both are facts about the column, and this
        override is the only place that sees the column type.
        """
        if col_def.comment:
            raise UnsupportedFeatureError(
                self.name, "COLUMN COMMENT",
                "SQLite has no column comment mechanism; comments are not supported.",
            )
        self._check_auto_increment_placement(col_def)

        sql, params = super().format_column_definition(col_def)
        return sql, params

    def _check_auto_increment_placement(self, col_def: "ColumnDefinition") -> None:
        """Refuse ``AUTOINCREMENT`` anywhere SQLite cannot spell it.

        SQLite accepts ``INTEGER PRIMARY KEY AUTOINCREMENT`` and nothing else.
        A flag on any other constraint used to be dropped without a word, which
        left a table whose key does not autoincrement and no trace of why.
        """
        from rhosocial.activerecord.backend.expression.statements import (
            ColumnConstraintType,
        )
        from rhosocial.activerecord.backend.expression.types.integer import (
            IntegerType,
        )

        flagged = [
            constraint
            for constraint in col_def.constraints
            if constraint.is_auto_increment
        ]
        if not flagged:
            return
        for constraint in flagged:
            if (
                constraint.constraint_type
                is not ColumnConstraintType.PRIMARY_KEY
            ):
                raise UnsupportedFeatureError(
                    self.name,
                    "AUTOINCREMENT on a non-primary-key column constraint",
                    "SQLite spells AUTOINCREMENT only as part of "
                    "INTEGER PRIMARY KEY AUTOINCREMENT; declare it on the "
                    "primary key constraint.",
                )
        if not isinstance(col_def.data_type, IntegerType):
            raise UnsupportedFeatureError(
                self.name,
                "AUTOINCREMENT on a non-INTEGER column",
                f"SQLite spells AUTOINCREMENT only as part of INTEGER PRIMARY "
                f"KEY AUTOINCREMENT, and this column is "
                f"{type(col_def.data_type).__name__}.",
            )


# =============================================================================
# SQLiteDMLMixin — INSERT and RETURNING clause formatting
# =============================================================================

