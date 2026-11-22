# src/rhosocial/activerecord/backend/dialect/protocols/ddl/ddl_column_support.py
"""Protocol for base DDL column/action rendering. Pure-format family group."""

from typing import runtime_checkable, Protocol, Tuple, List, Dict, Any, Optional

@runtime_checkable
class DDLColumnSupport(Protocol):
    def format_column_comment_clause(self, expr: "ColumnCommentClause") -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_column(self, expr: "Column") -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_column_attributes(self, expr: "ColumnDefinition") -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_collation_clause(self, expr: "CollationClause") -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_character_set_clause(
    self, expr: "CharacterSetClause"
    ) -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_column_definition(self, expr: "ColumnDefinition") -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_column_generated_constraint(
    self, expr: "ColumnGeneratedConstraint"
    ) -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_constraint_enforcement(self, expr: "ColumnConstraint") -> str:
        ...  # pragma: no cover

    def format_constraint_validation(self, expr: "TableConstraint") -> str:
        ...  # pragma: no cover

    def format_column_constraint(self, expr: "ColumnConstraint") -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_constraint_branch(self, expr: "BaseExpression") -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_constraint_traits(self, expr: "ColumnConstraint") -> Tuple[str, str]:
        ...  # pragma: no cover

    def format_column_primary_key_constraint(
    self, expr: "ColumnPrimaryKeyConstraint"
    ) -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_column_unique_constraint(
    self, expr: "ColumnUniqueConstraint"
    ) -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_column_not_null_constraint(
    self, expr: "ColumnNotNullConstraint"
    ) -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_column_nullable_constraint(
    self, expr: "ColumnNullableConstraint"
    ) -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_column_check_constraint(
    self, expr: "ColumnCheckConstraint"
    ) -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_default_value_clause(self, expr: "DefaultValueClause") -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_column_default_constraint(
    self, expr: "ColumnDefaultConstraint"
    ) -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_table_primary_key_constraint(
    self, expr: "TablePrimaryKeyConstraint"
    ) -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_table_unique_constraint(
    self, expr: "TableUniqueConstraint"
    ) -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_table_check_constraint(
    self, expr: "TableCheckConstraint"
    ) -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_table_foreign_key_constraint(
    self, expr: "TableForeignKeyConstraint"
    ) -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_table_exclude_constraint(
    self, expr: "TableExcludeConstraint"
    ) -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_table_constraint(self, expr: "TableConstraint") -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_storage_options_expression(self, expr: "StorageOptionsExpression") -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_add_column_action(self, expr: "AddColumnAction") -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_drop_column_action(self, expr: "DropColumnAction") -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_alter_column_action(self, expr: "AlterColumnAction") -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_add_table_constraint_action(self, expr: "AddTableConstraintAction") -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_drop_table_constraint_action(self, expr: "DropTableConstraintAction") -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_index_definition(self, expr: "IndexDefinition") -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_add_index_action(self, expr: "AddIndexAction") -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_drop_index_action(self, expr: "DropIndexAction") -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_rename_column_action(self, expr: "RenameColumnAction") -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_rename_table_action(self, expr: "RenameTableAction") -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_modify_column_action(self, expr: "ModifyColumnAction") -> "Tuple[str, tuple]":
        ...  # pragma: no cover

    def format_change_column_action(self, expr: "ChangeColumnAction") -> "Tuple[str, tuple]":
        ...  # pragma: no cover






