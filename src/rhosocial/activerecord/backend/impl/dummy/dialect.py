# src/rhosocial/activerecord/backend/impl/dummy/dialect.py
"""
Dummy backend SQL dialect implementation.

This dialect implements all protocols and supports all features.
It is used for to_sql() testing and does not involve actual database connections.
"""
from typing import Tuple, Optional, List, Dict, Any

from rhosocial.activerecord.backend.dialect.base import BaseDialect
from rhosocial.activerecord.backend.dialect.protocols import (
    WindowFunctionSupport, CTESupport, AdvancedGroupingSupport, ReturningSupport,
    UpsertSupport, LateralJoinSupport, ArraySupport, JSONSupport, ExplainSupport,
    FilterClauseSupport, OrderedSetAggregationSupport, MergeSupport,
    TemporalTableSupport, QualifyClauseSupport, LockingSupport, GraphSupport,
)

class DummyDialect(
    BaseDialect,
    WindowFunctionSupport, CTESupport, AdvancedGroupingSupport, ReturningSupport,
    UpsertSupport, LateralJoinSupport, ArraySupport, JSONSupport, ExplainSupport,
    FilterClauseSupport, OrderedSetAggregationSupport, MergeSupport,
    TemporalTableSupport, QualifyClauseSupport, LockingSupport, GraphSupport,
):
    """
    Dummy dialect supporting all features for SQL generation testing.
    """

    def get_placeholder(self) -> str:
        """Use '?' placeholder for consistency."""
        return "?"

    # region Protocol Support Checks
    def supports_window_functions(self) -> bool: return True
    def supports_window_frame_clause(self) -> bool: return True
    def supports_basic_cte(self) -> bool: return True
    def supports_recursive_cte(self) -> bool: return True
    def supports_materialized_cte(self) -> bool: return True
    def supports_rollup(self) -> bool: return True
    def supports_cube(self) -> bool: return True
    def supports_grouping_sets(self) -> bool: return True
    def supports_returning_clause(self) -> bool: return True
    def supports_upsert(self) -> bool: return True
    def get_upsert_syntax_type(self) -> str: return "ON CONFLICT"
    def supports_lateral_join(self) -> bool: return True
    def supports_array_type(self) -> bool: return True
    def supports_array_constructor(self) -> bool: return True
    def supports_array_access(self) -> bool: return True
    def supports_json_type(self) -> bool: return True
    def get_json_access_operator(self) -> str: return "->"
    def supports_json_table(self) -> bool: return True
    def supports_explain_analyze(self) -> bool: return True
    def supports_explain_format(self, format_type: str) -> bool: return True
    def supports_filter_clause(self) -> bool: return True
    def supports_ordered_set_aggregation(self) -> bool: return True
    def supports_merge_statement(self) -> bool: return True
    def supports_temporal_tables(self) -> bool: return True
    def supports_qualify_clause(self) -> bool: return True
    def supports_for_update_skip_locked(self) -> bool: return True
    def supports_graph_match(self) -> bool: return True
    # endregion

    # region ALTER TABLE Statement Formatting
    def format_alter_table_statement(self, expr: "AlterTableExpression") -> Tuple[str, tuple]:
        """Format ALTER TABLE statement per SQL standard."""
        all_params = []

        # Basic statement
        parts = [f"ALTER TABLE {self.format_identifier(expr.table_name)}"]

        # Process each action
        action_parts = []
        for action in expr.actions:
            action_part, action_params = action.to_sql()
            action_parts.append(action_part)
            all_params.extend(action_params)

        if action_parts:
            # Join actions with commas
            parts.append(" " + ", ".join(action_parts))

        return " ".join(parts), tuple(all_params)

    def format_add_column_action(self, action: "AddColumn") -> Tuple[str, tuple]:
        """Format ADD COLUMN action per SQL standard."""
        column_sql, column_params = self.format_column_definition(action.column)
        return f"ADD COLUMN {column_sql}", column_params

    def format_drop_column_action(self, action: "DropColumn") -> Tuple[str, tuple]:
        """Format DROP COLUMN action per SQL standard."""
        if action.if_exists:
            return f"DROP COLUMN IF EXISTS {self.format_identifier(action.column_name)}", ()
        return f"DROP COLUMN {self.format_identifier(action.column_name)}", ()

    def format_alter_column_action(self, action: "AlterColumn") -> Tuple[str, tuple]:
        """Format ALTER COLUMN action per SQL standard."""
        all_params = []
        # Handle enum values properly - get the string value instead of the enum representation
        operation_str = action.operation.value if hasattr(action.operation, 'value') else str(action.operation)
        column_part = f"ALTER COLUMN {self.format_identifier(action.column_name)} {operation_str}"

        if action.new_value is not None:
            # For "SET DATA TYPE" operations, the new value is typically a type specification, not a parameter
            if operation_str == "SET DATA TYPE":
                column_part += f" {action.new_value}"
            elif isinstance(action.new_value, str):
                column_part += f" {self.get_placeholder()}"
                all_params.append(action.new_value)
            elif hasattr(action.new_value, 'to_sql'):
                value_sql, value_params = action.new_value.to_sql()
                column_part += f" {value_sql}"
                all_params.extend(value_params)
            else:
                column_part += f" {self.get_placeholder()}"
                all_params.append(action.new_value)

        # Add cascade if specified
        if hasattr(action, 'cascade') and action.cascade:
            column_part += " CASCADE"

        return column_part, tuple(all_params)

    def format_add_constraint_action(self, action: "AddTableConstraint") -> Tuple[str, tuple]:
        """Format ADD CONSTRAINT action per SQL standard."""
        from rhosocial.activerecord.backend.expression.statements import TableConstraintType

        all_params = []
        parts = []
        if action.constraint.name:
            parts.append(f"CONSTRAINT {self.format_identifier(action.constraint.name)}")

        if action.constraint.constraint_type == TableConstraintType.PRIMARY_KEY:
            if action.constraint.columns:
                cols_str = ", ".join(self.format_identifier(col) for col in action.constraint.columns)
                parts.append(f"PRIMARY KEY ({cols_str})")
            else:
                parts.append("PRIMARY KEY")
        elif action.constraint.constraint_type == TableConstraintType.UNIQUE:
            if action.constraint.columns:
                cols_str = ", ".join(self.format_identifier(col) for col in action.constraint.columns)
                parts.append(f"UNIQUE ({cols_str})")
            else:
                parts.append("UNIQUE")
        elif action.constraint.constraint_type == TableConstraintType.CHECK and action.constraint.check_condition:
            check_sql, check_params = action.constraint.check_condition.to_sql()
            parts.append(f"CHECK ({check_sql})")
            all_params.extend(check_params)
        elif action.constraint.constraint_type == TableConstraintType.FOREIGN_KEY:
            if action.constraint.columns and action.constraint.foreign_key_table:
                cols_str = ", ".join(self.format_identifier(col) for col in action.constraint.columns)
                ref_table = self.format_identifier(action.constraint.foreign_key_table)
                ref_cols_str = ", ".join(self.format_identifier(col) for col in action.constraint.foreign_key_columns) if action.constraint.foreign_key_columns else ""
                if ref_cols_str:
                    parts.append(f"FOREIGN KEY ({cols_str}) REFERENCES {ref_table}({ref_cols_str})")
                else:
                    parts.append(f"FOREIGN KEY ({cols_str}) REFERENCES {ref_table}")

        return f"ADD {' '.join(parts)}", tuple(all_params)

    def format_drop_constraint_action(self, action: "DropTableConstraint") -> Tuple[str, tuple]:
        """Format DROP CONSTRAINT action per SQL standard."""
        result = f"DROP CONSTRAINT {self.format_identifier(action.constraint_name)}"
        if action.cascade:
            result += " CASCADE"
        return result, ()

    def format_rename_column_action(self, action: "RenameColumn") -> Tuple[str, tuple]:
        """Format RENAME COLUMN action per SQL standard."""
        return f"RENAME COLUMN {self.format_identifier(action.old_name)} TO {self.format_identifier(action.new_name)}", ()

    def format_rename_table_action(self, action: "RenameTable") -> Tuple[str, tuple]:
        """Format RENAME TABLE action per SQL standard."""
        return f"RENAME TO {self.format_identifier(action.new_name)}", ()

    def format_rename_object_action(self, action: "RenameObject") -> Tuple[str, tuple]:
        """Format RENAME action for ALTER TABLE statement."""
        if hasattr(action, 'object_type') and action.object_type.upper() == "COLUMN":
            return f"RENAME COLUMN {self.format_identifier(action.old_name)} TO {self.format_identifier(action.new_name)}", ()
        elif hasattr(action, 'object_type') and action.object_type.upper() == "TABLE":
            # Though this wouldn't typically be used in ALTER TABLE context
            return f"RENAME TO {self.format_identifier(action.new_name)}", ()
        else:
            return f"RENAME {self.format_identifier(action.old_name)} TO {self.format_identifier(action.new_name)}", ()

    def format_add_index_action(self, action: "AddIndex") -> Tuple[str, tuple]:
        """Format ADD INDEX action."""
        return f"ADD INDEX {self.format_identifier(action.index.name)}", ()

    def format_drop_index_action(self, action: "DropIndex") -> Tuple[str, tuple]:
        """Format DROP INDEX action."""
        cmd = f"DROP INDEX {self.format_identifier(action.index_name)}"
        if hasattr(action, 'if_exists') and action.if_exists:
            cmd = f"DROP INDEX IF EXISTS {self.format_identifier(action.index_name)}"
        return cmd, ()
    # endregion




