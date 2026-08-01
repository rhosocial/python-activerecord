# src/rhosocial/activerecord/backend/dialect/mixins/ddl_table.py
from typing import Any, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.statements import (
        CreateTableExpression,
        DropTableExpression,
        AlterTableExpression,
    )


class TableMixin:
    """Mixin for table DDL support."""

    def supports_create_table(self) -> bool:
        """Whether CREATE TABLE is supported."""
        return True

    def supports_drop_table(self) -> bool:
        """Whether DROP TABLE is supported."""
        return True

    def supports_alter_table(self) -> bool:
        """Whether ALTER TABLE is supported."""
        return True

    def supports_temporary_table(self) -> bool:
        """Whether TEMPORARY tables are supported."""
        return True

    def supports_if_not_exists_table(self) -> bool:
        """Whether CREATE TABLE IF NOT EXISTS is supported."""
        return False

    def supports_if_exists_table(self) -> bool:
        """Whether DROP TABLE IF EXISTS is supported."""
        return False

    def supports_drop_table_cascade(self) -> bool:
        """Whether DROP TABLE accepts the CASCADE keyword (SQL-standard form).

        Defaults to True (optimistic) so that DummyDialect exercises the full
        generic rendering path; actual backends override to reflect whether the
        CASCADE token is valid syntax for their DROP TABLE statement. The
        switch governs syntax only and is silent on whether the database truly
        drops dependent objects (e.g. MySQL/MariaDB parse-but-ignore CASCADE
        still report True).

        Oracle-specific CASCADE CONSTRAINTS / PURGE handling lives in the Oracle
        backend protocol and overrides format_drop_table_statement; this default
        only renders the standard CASCADE token.
        """
        return True

    def supports_drop_table_restrict(self) -> bool:
        """Whether DROP TABLE accepts the RESTRICT keyword.

        Defaults to True (optimistic); backends that do not recognize RESTRICT
        override to False, in which case the generic helper raises
        UnsupportedFeatureError when a caller asks for restrict behavior.
        """
        return True

    def supports_table_tablespace(self) -> bool:
        """Whether tablespace specification is supported."""
        return False

    def supports_drop_column(self) -> bool:
        """Whether DROP COLUMN is supported."""
        return True

    def supports_alter_column_type(self) -> bool:
        """Whether altering column data type is supported."""
        return True

    def supports_rename_column(self) -> bool:
        """Whether RENAME COLUMN is supported."""
        return True

    def supports_rename_table(self) -> bool:
        """Whether RENAME TABLE is supported."""
        return True

    def supports_table_like_syntax(self) -> bool:
        """Whether CREATE TABLE ... LIKE is supported."""
        return False

    def format_create_table_like(self, expr: "CreateTableExpression") -> Tuple[str, tuple]:
        """Format CREATE TABLE ... LIKE statement. Override in dialect."""
        from ..exceptions import UnsupportedFeatureError
        raise UnsupportedFeatureError(self.name, "CREATE TABLE ... LIKE")

    def format_create_table_statement(self, expr: "CreateTableExpression") -> Tuple[str, tuple]:
        """Format CREATE TABLE statement (generic implementation)."""
        all_params: List[Any] = []
        temp_part = "TEMPORARY " if expr.temporary else ""
        not_exists_part = "IF NOT EXISTS " if expr.if_not_exists else ""
        table_sql, table_params = expr.table.to_sql()
        all_params.extend(table_params)
        table_part = f"CREATE {temp_part}TABLE {not_exists_part}{table_sql} "
        column_parts = []
        for col_def in expr.columns:
            col_sql, col_params = self.format_column_definition(col_def)
            column_parts.append(col_sql)
            all_params.extend(col_params)
        all_def_parts = [", ".join(column_parts)]
        for t_const in expr.table_constraints:
            const_sql, const_params = self.format_table_constraint_sql(t_const)
            if const_sql:
                all_def_parts.append(const_sql)
                all_params.extend(const_params)
        full_column_def = "(" + ", ".join(all_def_parts) + ")"
        parts = [table_part + full_column_def]
        if expr.storage_options:
            storage_sql, storage_params = self.format_storage_options(expr.storage_options)
            if storage_sql:
                parts.append(storage_sql)
                all_params.extend(storage_params)
        if expr.tablespace:
            parts.append(f" TABLESPACE {self.format_identifier(expr.tablespace)}")
        if expr.inherits:
            inherits_str = ", ".join(self.format_identifier(table) for table in expr.inherits)
            parts.append(f" INHERITS ({inherits_str})")
        if expr.partition is not None:
            partition_sql, partition_params = expr.partition.to_sql()
            if partition_sql:
                parts.append(partition_sql)
                all_params.extend(partition_params)
        if expr.as_query:
            query_sql, query_params = expr.as_query.to_sql()
            parts.append(f" AS ({query_sql})")
            all_params.extend(query_params)
        return "".join(parts), tuple(all_params)

    def format_drop_table_statement(self, expr: "DropTableExpression") -> Tuple[str, tuple]:
        """Format DROP TABLE statement (generic implementation).

        Renders ``DROP TABLE [IF EXISTS] <table> [CASCADE | RESTRICT]`` with
        capability gating: if the dialect reports ``supports_drop_table_cascade``
        (resp. ``supports_drop_table_restrict``) as False, asking for the
        corresponding behavior raises ``UnsupportedFeatureError`` instead of
        emitting a token the database would reject (or silently drop).

        Backend-specific cascade forms that have no cross-vendor commonality
        (e.g. Oracle's CASCADE CONSTRAINTS plus PURGE) are NOT handled here;
        backends override this method to render their own form.
        """
        from ..exceptions import UnsupportedFeatureError

        parts = ["DROP TABLE"]
        if expr.if_exists and self.supports_if_exists_table():
            parts.append("IF EXISTS")
        table_sql, table_params = expr.table.to_sql()
        parts.append(table_sql)
        if expr.cascade is True:
            if not self.supports_drop_table_cascade():
                raise UnsupportedFeatureError(
                    self.name,
                    "DROP TABLE ... CASCADE",
                )
            parts.append("CASCADE")
        elif expr.cascade is False:
            if not self.supports_drop_table_restrict():
                raise UnsupportedFeatureError(
                    self.name,
                    "DROP TABLE ... RESTRICT",
                )
            parts.append("RESTRICT")
        return " ".join(parts), table_params

    def format_alter_table_statement(self, expr: "AlterTableExpression") -> Tuple[str, tuple]:
        """Format ALTER TABLE statement (generic implementation)."""
        all_params: List[Any] = []
        parts = [f"ALTER TABLE {self.format_identifier(expr.table_name)}"]
        action_parts = []
        for action in expr.actions:
            action_part, action_params = action.to_sql()
            action_parts.append(action_part)
            all_params.extend(action_params)
        if action_parts:
            parts.append(" " + ", ".join(action_parts))
        return " ".join(parts), tuple(all_params)


class ConstraintMixin:
    """Mixin for DDL constraint capability detection.

    Default values are True for all methods, enabling DummyDialect
    to validate the full constraint implementation. Actual backends
    override methods as needed to reflect their real capabilities.
    """

    # Basic constraint types (SQL-86/SQL-92)

    def supports_primary_key_constraint(self) -> bool:
        """Whether PRIMARY KEY constraints are supported."""
        return True

    def supports_unique_constraint(self) -> bool:
        """Whether UNIQUE constraints are supported."""
        return True

    def supports_not_null_constraint(self) -> bool:
        """Whether NOT NULL constraints are supported."""
        return True

    def supports_check_constraint(self) -> bool:
        """Whether CHECK constraints are supported and enforced."""
        return True

    def supports_foreign_key_constraint(self) -> bool:
        """Whether FOREIGN KEY constraints are supported."""
        return True

    # FK referential actions (SQL-92)

    def supports_fk_on_delete(self) -> bool:
        """Whether ON DELETE referential actions are supported."""
        return True

    def supports_fk_on_update(self) -> bool:
        """Whether ON UPDATE referential actions are supported."""
        return True

    # FK match modes (SQL:1999)

    def supports_fk_match(self) -> bool:
        """Whether MATCH {SIMPLE|PARTIAL|FULL} is supported."""
        return True

    # Constraint deferral (SQL:1999)

    def supports_deferrable_constraint(self) -> bool:
        """Whether DEFERRABLE / INITIALLY DEFERRED/IMMEDIATE is supported."""
        return True

    # Constraint enforcement control (SQL:2016)

    def supports_constraint_enforced(self) -> bool:
        """Whether ENFORCED / NOT ENFORCED constraint control is supported."""
        return True

    # ALTER TABLE constraint operations (SQL-92)

    def supports_add_constraint(self) -> bool:
        """Whether ALTER TABLE ADD CONSTRAINT is supported."""
        return True

    def supports_drop_constraint(self) -> bool:
        """Whether ALTER TABLE DROP CONSTRAINT is supported."""
        return True
