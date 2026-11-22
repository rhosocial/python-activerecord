# .../mixins/create_table_mixin.py
"""Per-statement mixin for CreateTableSupport. Members/order/signature mirror the protocol."""

from rhosocial.activerecord.backend.expression.statements import (
    TableCheckConstraint,
    TableForeignKeyConstraint,
)
from ...expression.statements.ddl_alter import AlterTableAction
from ...expression.objects import Table
from typing import Any, List, Tuple, TYPE_CHECKING
from enum import Enum

class CreateTableMixin:
    def supports_create_table(self) -> bool:
            """Whether CREATE TABLE is supported.

            Defaults to True.
            """
            return True

    def supports_temporary_table(self) -> bool:
            """Whether TEMPORARY tables are supported.

            Defaults to True.
            """
            return True

    def supports_if_not_exists_table(self) -> bool:
            """Whether CREATE TABLE IF NOT EXISTS is supported.

            Defaults to False.
            """
            return False

    def supports_create_or_replace_table(self) -> bool:
            """Whether ``CREATE OR REPLACE TABLE`` is supported.

            Defaults to ``False``; Snowflake/BigQuery/MariaDB override to True.
            """
            return False

    def supports_unlogged_table(self) -> bool:
            """Whether ``CREATE UNLOGGED TABLE`` is supported.

            Defaults to ``False``; PostgreSQL overrides to True.
            """
            return False

    def supports_transient_table(self) -> bool:
            """Whether ``CREATE TRANSIENT TABLE`` is supported.

            Defaults to ``False``; Snowflake overrides to True.
            """
            return False

    def supports_table_tablespace(self) -> bool:
            """Whether tablespace specification is supported.

            Defaults to False.
            """
            return False

    def supports_table_comment(self) -> bool:
            """Whether inline ``COMMENT 'text'`` on ``CREATE TABLE`` is supported.

            Defaults to ``False``; MySQL, MariaDB, and ClickHouse override to True.
            """
            return False

    def supports_inline_index(self) -> bool:
            """Whether CREATE TABLE accepts inline index definitions.

            Inline index clauses inside CREATE TABLE are a dialect convenience of
            MySQL/MariaDB/ClickHouse; the SQL-standard form is the standalone
            CREATE INDEX statement. The generic ``format_create_table_statement``
            raises UnsupportedFeatureError when an expression carries inline
            indexes but this switch is False.

            Defaults to False (SQL-standard behavior).
            """
            return False

    def supports_table_inheritance(self) -> bool:
            """Whether table inheritance (``INHERITS (parent, ...)``) is supported.

            Defaults to False; PostgreSQL (and compatible dialects) override to
            True. When a declaration carries ``inherits`` and this is False, the
            generic helper raises ``UnsupportedFeatureError`` instead of emitting
            a clause the database would reject.
            """
            return False

    def format_create_table_statement(self, expr: "CreateTableStatement") -> Tuple[str, tuple]:
            """Format CREATE TABLE statement (generic implementation).

            Handles the explicit-schema form only (columns, constraints, storage,
            table comment, tablespace, inherits, partition). CTAS / LIKE / CLONE
            have their own expressions and formatters -- this method does not
            touch them.

            The ``table_options.comment`` inline clause is rendered after the
            column list and storage options, before any PARTITION BY clause, and
            only on dialects whose :meth:`supports_table_comment` is True; on the
            others a declared comment raises ``UnsupportedFeatureError`` instead
            of being silently dropped.

            Args:
                expr: CreateTableStatement carrying the table reference, column
                    definitions, constraints, and optional storage, table comment,
                    tablespace, inherits, and partition clauses.

            Returns:
                Tuple of (SQL string, parameters tuple) for the statement.

            Raises:
                TypeError: ``CreateTableStatement.table`` is not a Table. Another
                object kind would have had its own name rendered as the table's.
            """
            if not isinstance(expr.table, Table):
                raise TypeError(
                    f"CreateTableStatement.table must be a Table, "
                    f"got {type(expr.table).__name__}"
                )
            all_params: List[Any] = []
            options_part = ""
            table_options = expr.table_options
            if table_options is not None:
                options_sql, options_params = table_options.to_sql()
                if options_sql:
                    options_part = options_sql + " "
                all_params.extend(options_params)
            from ..exceptions import UnsupportedFeatureError
            if expr.temporary and not self.supports_temporary_table():
                raise UnsupportedFeatureError(
                    self.name, "TEMPORARY TABLE",
                    f"{self.name} does not support TEMPORARY tables.",
                )
            if expr.if_not_exists and not self.supports_if_not_exists_table():
                raise UnsupportedFeatureError(
                    self.name, "CREATE TABLE IF NOT EXISTS",
                    f"{self.name} does not support CREATE TABLE IF NOT EXISTS.",
                )
            temp_part = "TEMPORARY " if expr.temporary else ""
            not_exists_part = "IF NOT EXISTS " if expr.if_not_exists else ""
            table_sql, table_params = expr.table.to_sql()
            all_params.extend(table_params)
            table_part = f"CREATE {options_part}{temp_part}TABLE {not_exists_part}{table_sql} "
            column_parts = []
            for col_def in expr.columns:
                col_sql, col_params = self.format_column_definition(col_def)
                column_parts.append(col_sql)
                all_params.extend(col_params)
            all_def_parts = [", ".join(column_parts)]
            from ...expression.statements import (
                ConstraintValidation,
            )

            for t_const in expr.table_constraints:
                # NOT VALID only means something when the constraint is *added*;
                # CREATE TABLE validates as it goes, so it is refused here. The
                # guard is about the trait alone: a constraint without one is
                # rendered like any other.
                if t_const.validation is not None and isinstance(
                    t_const.branch, (TableCheckConstraint, TableForeignKeyConstraint)
                ):
                    validation = t_const.validation
                    value = (
                        validation.value
                        if isinstance(validation, ConstraintValidation)
                        else validation
                    )
                    if "".join(str(value).strip().upper().split()) in {"NOTVALID", "NOVALIDATE"}:
                        raise ValueError("NOT VALID is only valid when adding a constraint")
                const_sql, const_params = self.format_table_constraint(t_const)
                if const_sql:
                    all_def_parts.append(const_sql)
                    all_params.extend(const_params)
            full_column_def = "(" + ", ".join(all_def_parts) + ")"
            parts = [table_part + full_column_def]
            if expr.storage_options is not None:
                storage_sql, storage_params = expr.storage_options.to_sql()
                if storage_sql:
                    parts.append(storage_sql)
                    all_params.extend(storage_params)
            table_comment = table_options.comment if table_options is not None else None
            if table_comment is not None:
                comment_sql, comment_params = self.format_table_comment_clause(table_comment)
                parts.append(comment_sql)
                all_params.extend(comment_params)
            if expr.tablespace:
                if not self.supports_table_tablespace():
                    raise UnsupportedFeatureError(
                        self.name, "TABLESPACE",
                        f"{self.name} does not support table tablespaces.",
                    )
                parts.append(f" TABLESPACE {self.format_identifier(expr.tablespace)}")
            if expr.inherits:
                if not self.supports_table_inheritance():
                    raise UnsupportedFeatureError(
                        self.name, "INHERITS",
                        f"{self.name} does not support table inheritance.",
                    )
                inherits_str = ", ".join(self.format_identifier(table) for table in expr.inherits)
                parts.append(f" INHERITS ({inherits_str})")
            if expr.partition is not None:
                partition_sql, partition_params = expr.partition.to_sql()
                if partition_sql:
                    parts.append(partition_sql)
                    all_params.extend(partition_params)
            if expr.indexes:
                raise UnsupportedFeatureError(
                    self.name,
                    "inline index in CREATE TABLE",
                    f"{self.name} does not support inline index definitions in "
                    "CREATE TABLE. Emit standalone CreateIndexStatement instead.",
                )
            return "".join(parts), tuple(all_params)

    def format_create_table_options(self, expr: "CreateTableOptions") -> Tuple[str, tuple]:
            """Format the generic ``CREATE`` header modifier.

            The generic layer renders only the standard ``OR REPLACE`` qualifier
            (capability-gated by :meth:`supports_create_or_replace_table`).
            Backend-specific header modifiers (``UNLOGGED`` / ``TRANSIENT`` / …)
            are added by the owning backend's ``XxxCreateTableOptions`` override,
            which must accept both the generic and its own instance.

            Args:
                expr: The CreateTableOptions clause carrying the flags.

            Returns:
                Tuple of (qualifier string, parameters tuple); empty string when no
                flag is set.

            Raises:
                UnsupportedFeatureError: If ``or_replace`` is requested but the
                    dialect does not support it.
            """
            from ..exceptions import UnsupportedFeatureError

            parts: List[str] = []
            if expr.or_replace:
                if not self.supports_create_or_replace_table():
                    raise UnsupportedFeatureError(self.name, "CREATE OR REPLACE TABLE")
                parts.append("OR REPLACE")
            return " ".join(parts), ()


    def format_table_comment(self, expr: str) -> Tuple[str, tuple]:
        """Render a table-level ``COMMENT 'text'`` clause.

        Generic reusable implementation: ``COMMENT '<escaped>'``.  Dialects
        that advertise :meth:`supports_table_comment` inherit this rendering
        as-is; dialects with a different grammar override the method.

        The statement renderer appends the returned clause after the column
        list and storage options, before any PARTITION BY clause.
        """
        escaped = self.escape_sql_string(expr)
        return f"COMMENT '{escaped}'", ()

    def format_table_comment_clause(self, expr: "TableCommentClause") -> Tuple[str, tuple]:
        """Render the inline table-comment expr of ``CREATE TABLE``.

        Returns the fragment **with a leading space** so the statement
        renderer can append it directly after the column list / storage
        options.  The text grammar is delegated to :meth:`format_table_comment`
        so backends override only the text form (e.g. Snowflake's
        ``COMMENT = '<text>'``, BigQuery's ``OPTIONS(description='<text>')``).

        Args:
            expr: The :class:`TableCommentClause` carrying the text.

        Returns:
            Tuple of (SQL fragment with leading space, parameters tuple).

        Raises:
            UnsupportedFeatureError: If :meth:`supports_table_comment` is
                False for the dialect.
        """
        from ..exceptions import UnsupportedFeatureError

        if not self.supports_table_comment():
            raise UnsupportedFeatureError(
                self.name, "TABLE COMMENT",
                f"{self.name} does not support an inline table comment.",
            )
        text_sql, params = self.format_table_comment(expr.comment)
        return f" {text_sql}", params

