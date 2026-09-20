# src/rhosocial/activerecord/backend/impl/sqlite/mixins/ddl_column.py
"""
SQLite-specific Ddl Column implementation.

This module provides the SQLiteDDLColumnMixin class.
"""

from typing import Tuple
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError


class SQLiteDDLColumnMixin:
    """SQLite-specific column constraint and column definition formatting."""

    def supports_add_column_if_not_exists(self) -> bool:
        return False

    def supports_drop_column_if_exists(self) -> bool:
        return False

    def supports_drop_constraint_if_exists(self) -> bool:
        return False

    def format_add_index_action(self, action) -> Tuple[str, tuple]:
        raise UnsupportedFeatureError(
            self.name,
            "ALTER TABLE ADD INDEX",
            "SQLite does not support ALTER TABLE ADD INDEX. Use CREATE INDEX directly.",
        )

    def format_drop_index_action(self, action) -> Tuple[str, tuple]:
        raise UnsupportedFeatureError(
            self.name,
            "ALTER TABLE DROP INDEX",
            "SQLite does not support ALTER TABLE DROP INDEX. Use DROP INDEX directly.",
        )

    def format_add_column_action(self, action) -> Tuple[str, tuple]:
        """Format ALTER TABLE ADD COLUMN for SQLite.

        SQLite supports ``ADD COLUMN`` but **not** the vendor extension
        ``ADD COLUMN IF NOT EXISTS`` (and never jumps to a single-line
        idempotent form). When ``if_not_exists=True`` is requested the
        qualifier cannot be expressed; the caller should pre-check
        ``PRAGMA table_info``.
        """
        if getattr(action, "if_not_exists", None):
            raise UnsupportedFeatureError(
                self.name,
                "ALTER TABLE ADD COLUMN IF NOT EXISTS",
                "SQLite does not support IF NOT EXISTS on ADD COLUMN. "
                "Pre-check PRAGMA table_info before adding the column.",
            )
        return super().format_add_column_action(action)

    def format_drop_column_action(self, action) -> Tuple[str, tuple]:
        """ALTER TABLE DROP COLUMN for SQLite.

        SQLite (>= 3.35.0) supports plain ``DROP COLUMN`` but **not** the
        vendor extension ``DROP COLUMN IF EXISTS``. Guard against emitting
        the unsupported qualifier.
        """
        if getattr(action, "if_exists", None):
            raise UnsupportedFeatureError(
                self.name,
                "ALTER TABLE DROP COLUMN IF EXISTS",
                "SQLite does not support IF EXISTS on DROP COLUMN. "
                "Pre-check PRAGMA table_info before dropping the column.",
            )
        return super().format_drop_column_action(action)

    def format_drop_table_constraint_action(self, action) -> Tuple[str, tuple]:
        """ALTER TABLE DROP CONSTRAINT for SQLite.

        SQLite (>= 3.53.0) supports ``DROP CONSTRAINT`` for NOT NULL and
        CHECK constraints but **not** the ``IF EXISTS`` qualifier.
        """
        if getattr(action, "if_exists", None):
            raise UnsupportedFeatureError(
                self.name,
                "ALTER TABLE DROP CONSTRAINT IF EXISTS",
                "SQLite does not support IF EXISTS on DROP CONSTRAINT. "
                "Pre-check sqlite_master / the constraint catalog before dropping.",
            )
        return super().format_drop_table_constraint_action(action)

    def format_primary_key_constraint(self, constraint) -> Tuple[str, tuple]:
        """Format PRIMARY KEY constraint, optionally with AUTOINCREMENT."""
        result = " PRIMARY KEY"
        if constraint.is_auto_increment:
            result += " AUTOINCREMENT"
        return result, ()

    def format_not_null_constraint(self, constraint) -> Tuple[str, tuple]:
        """Format NOT NULL constraint."""
        return " NOT NULL", ()

    def format_null_constraint(self, constraint) -> Tuple[str, tuple]:
        """Format NULL constraint."""
        return " NULL", ()

    def format_column_unique_constraint(self, constraint) -> Tuple[str, tuple]:
        """Format a COLUMN-level UNIQUE constraint.

        NOTE: deliberately named ``..._column_...`` so it cannot shadow the
        TABLE-level ``SQLDialectBase.format_unique_constraint(t_const)``
        defined in ``backend.dialect.mixins.ddl_column`` — the two handle
        column-level vs table-level constraints respectively.
        """
        return " UNIQUE", ()

    def format_default_value_clause(self, expr) -> Tuple[str, tuple]:
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

    def format_check_constraint(self, constraint) -> Tuple[str, tuple]:
        """Format CHECK constraint."""
        if constraint.check_condition is None:
            return "", ()
        check_sql, check_params = constraint.check_condition.to_sql()
        return f" CHECK ({check_sql})", check_params

    def format_column_fk_constraint(self, constraint) -> Tuple[str, tuple]:
        """Format a column-level FOREIGN KEY reference for SQLite."""
        from rhosocial.activerecord.backend.expression.statements import ReferentialAction

        if constraint.foreign_key_reference is None:
            raise ValueError("Foreign key constraint must have a foreign_key_reference specified.")
        referenced_table, referenced_columns = constraint.foreign_key_reference
        ref_cols_str = ", ".join(self.format_identifier(col) for col in referenced_columns)
        result = f" REFERENCES {self.format_identifier(referenced_table)}({ref_cols_str})"

        if constraint.on_delete is not None and constraint.on_delete != ReferentialAction.NO_ACTION:
            result += f" ON DELETE {constraint.on_delete.value}"
        if constraint.on_update is not None and constraint.on_update != ReferentialAction.NO_ACTION:
            result += f" ON UPDATE {constraint.on_update.value}"

        return result, ()

    def format_column_definition(self, col_def) -> Tuple[str, tuple]:
        """Format a column definition for SQLite, including generated columns support."""
        from rhosocial.activerecord.backend.expression.statements import ColumnConstraintType

        constraint_handlers = {
            ColumnConstraintType.PRIMARY_KEY: self.format_primary_key_constraint,
            ColumnConstraintType.NOT_NULL: self.format_not_null_constraint,
            ColumnConstraintType.NULL: self.format_null_constraint,
            ColumnConstraintType.UNIQUE:
                self.format_column_unique_constraint,
            ColumnConstraintType.DEFAULT: self.format_default_constraint,
            ColumnConstraintType.CHECK: self.format_check_constraint,
            ColumnConstraintType.FOREIGN_KEY: self.format_column_fk_constraint,
        }

        all_params = []
        type_sql, _ = col_def.data_type.to_sql()
        col_sql = f"{self.format_identifier(col_def.name)} {type_sql}"

        for constraint in col_def.constraints:
            handler = constraint_handlers.get(constraint.constraint_type)
            if handler:
                sql_part, params = handler(constraint)
                col_sql += sql_part
                all_params.extend(params)

        if col_def.generated_expression is not None:
            gen_sql, gen_params = col_def.generated_expression.to_sql()
            col_sql += gen_sql
            all_params.extend(gen_params)

        return col_sql, tuple(all_params)


# =============================================================================
# SQLiteDMLMixin — INSERT and RETURNING clause formatting
# =============================================================================

