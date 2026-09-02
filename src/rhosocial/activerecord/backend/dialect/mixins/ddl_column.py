# src/rhosocial/activerecord/backend/dialect/mixins/ddl_column.py
from typing import Any, Dict, List, Tuple

from ..exceptions import UnsupportedFeatureError
from ...expression.bases import BaseExpression, ToSQLProtocol


class DDLColumnMixin:
    """Mixin for DDL column definition and ALTER TABLE action formatting."""

    def supports_add_column_if_not_exists(self) -> bool:
        return False

    def supports_drop_column_if_exists(self) -> bool:
        return False

    def supports_drop_constraint_if_exists(self) -> bool:
        return False

    def format_column_definition(self, col_def) -> Tuple[str, tuple]:
        all_params: List[Any] = []
        type_sql, _ = col_def.data_type.to_sql(self)
        col_sql = f"{self.format_identifier(col_def.name)} {type_sql}"
        for constraint in col_def.constraints:
            suffix, params = self.format_column_constraint(constraint)
            col_sql += suffix
            all_params.extend(params)
        if col_def.comment:
            from ...dialect.base import SQLDialectBase as _B
            escaped_comment = _B._escape_sql_string(col_def.comment)
            col_sql += f" COMMENT '{escaped_comment}'"
        return col_sql, tuple(all_params)

    def format_column_constraint(self, constraint) -> Tuple[str, tuple]:
        from ...expression.statements import ColumnConstraintType
        ctype = constraint.constraint_type
        simple_constraints = {
            ColumnConstraintType.PRIMARY_KEY: " PRIMARY KEY",
            ColumnConstraintType.NOT_NULL: " NOT NULL",
            ColumnConstraintType.NULL: " NULL",
            ColumnConstraintType.UNIQUE: " UNIQUE",
        }
        if ctype in simple_constraints:
            return simple_constraints[ctype], ()
        if ctype == ColumnConstraintType.DEFAULT:
            return self.format_default_constraint(constraint)
        if ctype == ColumnConstraintType.CHECK:
            return self.format_column_check_constraint(constraint)
        if ctype == ColumnConstraintType.FOREIGN_KEY:
            return self.format_column_fk_constraint(constraint)
        return "", ()

    def format_column_check_constraint(self, constraint) -> Tuple[str, tuple]:
        if constraint.check_condition is None:
            return "", ()
        check_sql, check_params = constraint.check_condition.to_sql()
        return f" CHECK ({check_sql})", tuple(check_params)

    def format_default_constraint(self, constraint) -> Tuple[str, tuple]:
        from ...dialect.base import SQLDialectBase
        if constraint.default_value is None:
            raise ValueError("DEFAULT constraint must have a default value specified.")
        if isinstance(constraint.default_value, BaseExpression):
            default_sql, default_params = constraint.default_value.to_sql()
            return f" DEFAULT {default_sql}", tuple(default_params)
        if isinstance(constraint.default_value, str):
            escaped = SQLDialectBase._escape_sql_string(constraint.default_value)
            return f" DEFAULT '{escaped}'", ()
        return f" DEFAULT {constraint.default_value}", ()

    def format_column_fk_constraint(self, constraint) -> Tuple[str, tuple]:
        from ...expression.statements import ReferentialAction
        if constraint.foreign_key_reference is None:
            raise ValueError("Foreign key constraint must have a foreign_key_reference specified.")
        referenced_table, referenced_columns = constraint.foreign_key_reference
        ref_cols_str = ", ".join(self.format_identifier(col) for col in referenced_columns)
        result = f" REFERENCES {self.format_identifier(referenced_table)}({ref_cols_str})"
        if constraint.on_delete is not None and constraint.on_delete != ReferentialAction.NO_ACTION:
            result += f" ON DELETE {constraint.on_delete.value}"
        if constraint.on_update is not None and constraint.on_update != ReferentialAction.NO_ACTION:
            result += f" ON UPDATE {constraint.on_update.value}"
        if constraint.deferrable is True:
            if constraint.initially_deferred is True:
                result += " DEFERRABLE INITIALLY DEFERRED"
            elif constraint.initially_deferred is False:
                result += " DEFERRABLE INITIALLY IMMEDIATE"
            else:
                result += " DEFERRABLE"
        elif constraint.deferrable is False:
            result += " NOT DEFERRABLE"
        return result, ()

    def format_pk_constraint(self, t_const) -> str:
        if not t_const.columns:
            raise ValueError("PRIMARY KEY constraint must have at least one column specified.")
        cols_str = ", ".join(self.format_identifier(col) for col in t_const.columns)
        return f"PRIMARY KEY ({cols_str})"

    def format_unique_constraint(self, t_const) -> str:
        if not t_const.columns:
            raise ValueError("UNIQUE constraint must have at least one column specified.")
        cols_str = ", ".join(self.format_identifier(col) for col in t_const.columns)
        return f"UNIQUE ({cols_str})"

    def format_table_check_constraint(self, t_const) -> Tuple[str, tuple]:
        if t_const.check_condition is None:
            raise ValueError("CHECK constraint must have a check condition specified.")
        check_sql, check_params = t_const.check_condition.to_sql()
        return f"CHECK ({check_sql})", tuple(check_params)

    def format_foreign_key_constraint(self, t_const) -> str:
        from ...expression.statements import ReferentialAction, ForeignKeyConstraint
        if not t_const.columns:
            raise ValueError("FOREIGN KEY constraint must have at least one local column specified.")
        if not t_const.foreign_key_columns:
            raise ValueError("FOREIGN KEY constraint must have at least one foreign key column specified.")
        if not t_const.foreign_key_table:
            raise ValueError("FOREIGN KEY constraint must have a foreign key table specified.")
        cols_str = ", ".join(self.format_identifier(col) for col in t_const.columns)
        ref_cols_str = ", ".join(self.format_identifier(col) for col in t_const.foreign_key_columns)
        result = f"FOREIGN KEY ({cols_str}) REFERENCES {self.format_identifier(t_const.foreign_key_table)}({ref_cols_str})"
        if isinstance(t_const, ForeignKeyConstraint):
            if t_const.on_delete is not None and t_const.on_delete != ReferentialAction.NO_ACTION:
                result += f" ON DELETE {t_const.on_delete.value}"
            if t_const.on_update is not None and t_const.on_update != ReferentialAction.NO_ACTION:
                result += f" ON UPDATE {t_const.on_update.value}"
        return result

    def format_table_constraint_sql(self, t_const) -> Tuple[str, tuple]:
        from ...expression.statements import TableConstraintType
        const_parts = []
        params = []
        if t_const.name:
            const_parts.append(f"CONSTRAINT {self.format_identifier(t_const.name)}")
        ctype = t_const.constraint_type
        if ctype == TableConstraintType.PRIMARY_KEY:
            const_parts.append(self.format_pk_constraint(t_const))
        elif ctype == TableConstraintType.UNIQUE:
            const_parts.append(self.format_unique_constraint(t_const))
        elif ctype == TableConstraintType.CHECK:
            sql, params = self.format_table_check_constraint(t_const)
            const_parts.append(sql)
        elif ctype == TableConstraintType.FOREIGN_KEY:
            const_parts.append(self.format_foreign_key_constraint(t_const))
        return " ".join(const_parts) if const_parts else "", tuple(params)

    def format_storage_options(self, storage_options: Dict[str, Any]) -> Tuple[str, tuple]:
        from ...dialect.base import SQLDialectBase
        storage_parts = []
        params = []
        for key, value in storage_options.items():
            quoted_key = self.format_identifier(key)
            if isinstance(value, str):
                storage_parts.append(f"{quoted_key} = '{SQLDialectBase._escape_sql_string(value)}'")
            elif isinstance(value, (int, float)):
                storage_parts.append(f"{quoted_key} = {value}")
            else:
                storage_parts.append(f"{quoted_key} = {self.get_parameter_placeholder()}")
                params.append(value)
        if storage_parts:
            return " WITH (" + ", ".join(storage_parts) + ")", tuple(params)
        return "", ()

    def format_add_column_action(self, action) -> Tuple[str, tuple]:
        column_sql, column_params = self.format_column_definition(action.column)
        return f"ADD COLUMN {column_sql}", column_params

    def format_drop_column_action(self, action) -> Tuple[str, tuple]:
        if hasattr(action, "if_exists") and action.if_exists:
            return f"DROP COLUMN IF EXISTS {self.format_identifier(action.column_name)}", ()
        return f"DROP COLUMN {self.format_identifier(action.column_name)}", ()

    def format_alter_column_action(self, action) -> Tuple[str, tuple]:
        all_params: List[Any] = []
        operation_str = action.operation.value if hasattr(action.operation, "value") else str(action.operation)
        column_part = f"ALTER COLUMN {self.format_identifier(action.column_name)} {operation_str}"
        if hasattr(action, "new_value") and action.new_value is not None:
            if operation_str == "SET DATA TYPE":
                from ...dialect.base import SQLDialectBase
                if not SQLDialectBase._validate_data_type(str(action.new_value)):
                    raise ValueError(f"Invalid data type specification: '{action.new_value}'")
                column_part += f" {action.new_value}"
            elif isinstance(action.new_value, str):
                column_part += f" {self.get_parameter_placeholder()}"
                all_params.append(action.new_value)
            elif isinstance(action.new_value, ToSQLProtocol):
                value_sql, value_params = action.new_value.to_sql()
                column_part += f" {value_sql}"
                all_params.extend(value_params)
            else:
                column_part += f" {self.get_parameter_placeholder()}"
                all_params.append(action.new_value)
        if hasattr(action, "cascade") and action.cascade:
            column_part += " CASCADE"
        return column_part, tuple(all_params)

    def format_add_table_constraint_action(self, action) -> Tuple[str, tuple]:
        from ...expression.statements import TableConstraintType, ReferentialAction, ForeignKeyConstraint
        from ..exceptions import UnsupportedFeatureError
        if not self.supports_add_constraint():
            raise UnsupportedFeatureError(self.name, "ALTER TABLE ADD CONSTRAINT")
        all_params: List[Any] = []
        parts = []
        if action.constraint.name:
            parts.append(f"CONSTRAINT {self.format_identifier(action.constraint.name)}")
        ctype = action.constraint.constraint_type
        if ctype == TableConstraintType.PRIMARY_KEY:
            if action.constraint.columns:
                cols_str = ", ".join(self.format_identifier(col) for col in action.constraint.columns)
                parts.append(f"PRIMARY KEY ({cols_str})")
            else:
                parts.append("PRIMARY KEY")
        elif ctype == TableConstraintType.UNIQUE:
            if action.constraint.columns:
                cols_str = ", ".join(self.format_identifier(col) for col in action.constraint.columns)
                parts.append(f"UNIQUE ({cols_str})")
            else:
                parts.append("UNIQUE")
        elif ctype == TableConstraintType.CHECK and action.constraint.check_condition:
            check_sql, check_params = action.constraint.check_condition.to_sql()
            parts.append(f"CHECK ({check_sql})")
            all_params.extend(check_params)
        elif ctype == TableConstraintType.FOREIGN_KEY:
            if action.constraint.columns and action.constraint.foreign_key_table:
                cols_str = ", ".join(self.format_identifier(col) for col in action.constraint.columns)
                ref_table = self.format_identifier(action.constraint.foreign_key_table)
                ref_cols_str = (
                    ", ".join(self.format_identifier(col) for col in action.constraint.foreign_key_columns)
                    if action.constraint.foreign_key_columns
                    else ""
                )
                if ref_cols_str:
                    parts.append(f"FOREIGN KEY ({cols_str}) REFERENCES {ref_table}({ref_cols_str})")
                else:
                    parts.append(f"FOREIGN KEY ({cols_str}) REFERENCES {ref_table}")
            else:
                parts.append("FOREIGN KEY")
            if isinstance(action.constraint, ForeignKeyConstraint):
                if action.constraint.match_type:
                    _VALID_MATCH_TYPES = frozenset({"SIMPLE", "PARTIAL", "FULL"})
                    mt = action.constraint.match_type.upper()
                    if mt not in _VALID_MATCH_TYPES:
                        raise ValueError(
                            f"Invalid MATCH type '{action.constraint.match_type}'. "
                            f"Must be one of: {', '.join(sorted(_VALID_MATCH_TYPES))}"
                        )
                    parts.append(f"MATCH {mt}")
                if action.constraint.on_delete != ReferentialAction.NO_ACTION:
                    parts.append(f"ON DELETE {action.constraint.on_delete.value}")
                if action.constraint.on_update != ReferentialAction.NO_ACTION:
                    parts.append(f"ON UPDATE {action.constraint.on_update.value}")
        else:
            parts.append("UNKNOWN CONSTRAINT")
        if action.constraint.deferrable is True:
            if action.constraint.initially_deferred is True:
                parts.append("DEFERRABLE INITIALLY DEFERRED")
            elif action.constraint.initially_deferred is False:
                parts.append("DEFERRABLE INITIALLY IMMEDIATE")
            else:
                parts.append("DEFERRABLE")
        elif action.constraint.deferrable is False:
            parts.append("NOT DEFERRABLE")
        return f"ADD {' '.join(parts)}", tuple(all_params)

    def format_drop_table_constraint_action(self, action) -> Tuple[str, tuple]:
        from ..exceptions import UnsupportedFeatureError
        if not self.supports_drop_constraint():
            raise UnsupportedFeatureError(self.name, "ALTER TABLE DROP CONSTRAINT")
        result = f"DROP CONSTRAINT {self.format_identifier(action.constraint_name)}"
        if hasattr(action, "cascade") and action.cascade:
            result += " CASCADE"
        return result, ()

    def format_add_index_action(self, action) -> Tuple[str, tuple]:
        columns = ", ".join(
            self.format_identifier(col) for col in action.index.columns
        )
        return (
            f"ADD INDEX {self.format_identifier(action.index.name)} ({columns})",
            (),
        )

    def format_drop_index_action(self, action) -> Tuple[str, tuple]:
        if hasattr(action, "if_exists") and action.if_exists:
            return f"DROP INDEX IF EXISTS {self.format_identifier(action.index)}", ()
        return f"DROP INDEX {self.format_identifier(action.index)}", ()

    def format_rename_column_action(self, action) -> Tuple[str, tuple]:
        return (
            f"RENAME COLUMN {self.format_identifier(action.old_name)} TO {self.format_identifier(action.new_name)}",
            (),
        )

    def format_rename_table_action(self, action) -> Tuple[str, tuple]:
        return f"RENAME TO {self.format_identifier(action.new_name)}", ()

    def format_modify_column_action(self, action) -> Tuple[str, tuple]:
        from ..exceptions import UnsupportedFeatureError
        raise UnsupportedFeatureError(self.name, "MODIFY COLUMN")

    def format_change_column_action(self, action) -> Tuple[str, tuple]:
        from ..exceptions import UnsupportedFeatureError
        raise UnsupportedFeatureError(self.name, "CHANGE COLUMN")
