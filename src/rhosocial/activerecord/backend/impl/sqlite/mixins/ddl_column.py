# src/rhosocial/activerecord/backend/impl/sqlite/mixins/ddl_column.py
"""
SQLite-specific Ddl Column implementation.

This module provides the SQLiteDDLColumnMixin class.
"""

from typing import Tuple
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError


class SQLiteDDLColumnMixin:
    """SQLite-specific column constraint and column definition formatting."""

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

    def format_unique_constraint(self, constraint) -> Tuple[str, tuple]:
        """Format UNIQUE constraint."""
        return " UNIQUE", ()

    def format_default_constraint(self, constraint) -> Tuple[str, tuple]:
        """Format DEFAULT constraint.

        Note: DEFAULT values in DDL must be literal values, not bound parameters.
        SQLite does not support parameterized DEFAULT in CREATE TABLE statements.
        This implementation inlines values directly into the SQL string.
        """
        if constraint.default_value is None:
            raise ValueError("DEFAULT constraint must have a default value specified.")
        from rhosocial.activerecord.backend.expression import bases
        from rhosocial.activerecord.backend.dialect.base import SQLDialectBase

        if isinstance(constraint.default_value, bases.BaseExpression):
            default_sql, default_params = constraint.default_value.to_sql()
            return f" DEFAULT {default_sql}", tuple(default_params)
        if isinstance(constraint.default_value, str):
            escaped = SQLDialectBase._escape_sql_string(constraint.default_value)
            return f" DEFAULT '{escaped}'", ()
        if isinstance(constraint.default_value, bool):
            return f" DEFAULT {'1' if constraint.default_value else '0'}", ()
        return f" DEFAULT {constraint.default_value}", ()

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

    def _handle_generated_column(self, col_def) -> Tuple[str, tuple]:
        """Handle generated column formatting."""
        from rhosocial.activerecord.backend.expression.statements import GeneratedColumnType

        if not self.supports_generated_columns():
            raise UnsupportedFeatureError(
                self.name, "Generated columns", "Generated columns require SQLite 3.31.0 or later."
            )
        gen_sql, gen_params = col_def.generated_expression.to_sql()
        gen_type = " STORED" if col_def.generated_type == GeneratedColumnType.STORED else " VIRTUAL"
        return f" GENERATED ALWAYS AS ({gen_sql}){gen_type}", gen_params

    def format_column_definition(self, col_def) -> Tuple[str, tuple]:
        """Format a column definition for SQLite, including generated columns support."""
        from rhosocial.activerecord.backend.expression.statements import ColumnConstraintType

        constraint_handlers = {
            ColumnConstraintType.PRIMARY_KEY: self.format_primary_key_constraint,
            ColumnConstraintType.NOT_NULL: self.format_not_null_constraint,
            ColumnConstraintType.NULL: self.format_null_constraint,
            ColumnConstraintType.UNIQUE: self.format_unique_constraint,
            ColumnConstraintType.DEFAULT: self.format_default_constraint,
            ColumnConstraintType.CHECK: self.format_check_constraint,
            ColumnConstraintType.FOREIGN_KEY: self.format_column_fk_constraint,
        }

        all_params = []
        type_sql, _ = col_def.data_type.to_sql(self)
        col_sql = f"{self.format_identifier(col_def.name)} {type_sql}"

        for constraint in col_def.constraints:
            handler = constraint_handlers.get(constraint.constraint_type)
            if handler:
                sql_part, params = handler(constraint)
                col_sql += sql_part
                all_params.extend(params)

        if col_def.generated_expression is not None:
            gen_sql, gen_params = self._handle_generated_column(col_def)
            col_sql += gen_sql
            all_params.extend(gen_params)

        return col_sql, tuple(all_params)


# =============================================================================
# SQLiteDMLMixin — INSERT and RETURNING clause formatting
# =============================================================================

