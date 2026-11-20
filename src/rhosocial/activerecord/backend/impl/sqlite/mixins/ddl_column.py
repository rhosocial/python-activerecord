from rhosocial.activerecord.backend.expression.statements import (
    ColumnPrimaryKeyConstraint,
)
from rhosocial.activerecord.backend.impl.sqlite.sqlite_auto_increment_clause import (
    SQLiteAutoIncrementClause,
)
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from typing import Tuple, TYPE_CHECKING
# src/rhosocial/activerecord/backend/impl/sqlite/mixins/ddl_column.py
"""
SQLite-specific Ddl Column implementation.

This module provides the SQLiteDDLColumnMixin class.
"""



if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.expression.statements.ddl_table import (
        ColumnPrimaryKeyConstraint,
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

    def format_column_primary_key_constraint(
        self, constraint: "ColumnPrimaryKeyConstraint"
    ) -> Tuple[str, tuple]:
        """SQLite's plain ``PRIMARY KEY``.

        ``AUTOINCREMENT`` follows ``PRIMARY KEY`` in SQLite's grammar, but it
        comes from the backend's column suggestion as an ``AutoIncrementClause``
        attribute, not from a flag on this constraint. :meth:`format_column_definition`
        places that clause immediately after the primary key.
        """
        return super().format_column_primary_key_constraint(constraint)

    def format_sqlite_auto_increment_clause(self, expr) -> Tuple[str, tuple]:
        """SQLite's rowid-alias ``AUTOINCREMENT`` tail (after PRIMARY KEY)."""
        return " AUTOINCREMENT", ()

    def format_default_value_clause(self, expr: "DefaultValueClause") -> Tuple[str, tuple]:
        """Format the value clause of a DEFAULT constraint (SQLite).

        SQLite does not support parameterized DEFAULT in CREATE TABLE, so
        values are inlined directly. Booleans render as ``1``/``0`` (SQLite
        has no native boolean literal); everything else delegates to the
        generic implementation.

        The value arrives as a ``Literal``, because the clause normalises a
        bare scalar at construction, so the bool is read out of the literal
        rather than off the clause.
        """
        from rhosocial.activerecord.backend.expression.core import Literal

        value = expr.value
        if isinstance(value, Literal):
            value = value.value
        if isinstance(value, bool):
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

        all_params: list = []
        type_sql, _ = col_def.data_type.to_sql()
        sql = f"{self.format_identifier(col_def.name)} {type_sql}"

        attributes = tuple(col_def.attributes or ())
        increment_attributes = [a for a in attributes if isinstance(a, SQLiteAutoIncrementClause)]
        other_attributes = [a for a in attributes if not isinstance(a, SQLiteAutoIncrementClause)]
        for attr in other_attributes:
            fragment, params = self.format_column_attribute(attr)
            sql += fragment
            all_params.extend(params)
        for constraint in col_def.constraints:
            fragment, params = self.format_column_constraint(constraint)
            sql += fragment
            all_params.extend(params)
            # AUTOINCREMENT is grammar that follows PRIMARY KEY *immediately*
            # (before NOT NULL and any later constraint), so it is emitted
            # right after the primary-key constraint's own fragment.
            if any(
                isinstance(c.branch, ColumnPrimaryKeyConstraint) and c is constraint
                for c in col_def.constraints
            ):
                for attr in increment_attributes:
                    increment_sql, increment_params = self.format_column_attribute(attr)
                    sql += increment_sql
                    all_params.extend(increment_params)

        if col_def.generated_expression is not None:
            gen_sql, gen_params = col_def.generated_expression.to_sql()
            sql += gen_sql
            all_params.extend(gen_params)
        return sql, tuple(all_params)

    def _check_auto_increment_placement(self, col_def: "ColumnDefinition") -> None:
        """Refuse ``AUTOINCREMENT`` anywhere SQLite cannot spell it.

        SQLite accepts ``INTEGER PRIMARY KEY AUTOINCREMENT`` and nothing else:
        the column must be INTEGER and its primary key must be a single-column
        constraint. A suggestion applied to any other column used to be dropped
        without a word, leaving a key that does not autoincrement and no trace.
        """
        from rhosocial.activerecord.backend.expression.types.integer import (
            IntegerType,
        )

        has_increment = any(
            isinstance(a, SQLiteAutoIncrementClause) for a in (col_def.attributes or ())
        )
        if not has_increment:
            return
        if not isinstance(col_def.data_type, IntegerType):
            raise UnsupportedFeatureError(
                self.name,
                "AUTOINCREMENT on a non-INTEGER column",
                f"SQLite spells AUTOINCREMENT only as part of INTEGER PRIMARY "
                f"KEY AUTOINCREMENT, and this column is "
                f"{type(col_def.data_type).__name__}.",
            )
        has_pk = any(
            isinstance(constraint.branch, ColumnPrimaryKeyConstraint)
            for constraint in col_def.constraints
        )
        if not has_pk:
            raise UnsupportedFeatureError(
                self.name,
                "AUTOINCREMENT without a primary key",
                "SQLite spells AUTOINCREMENT only as part of INTEGER PRIMARY "
                "KEY AUTOINCREMENT; this column has no primary-key constraint.",
            )


# =============================================================================
# SQLiteDMLMixin — INSERT and RETURNING clause formatting
# =============================================================================

