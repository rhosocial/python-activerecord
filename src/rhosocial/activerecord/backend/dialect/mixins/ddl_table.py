# src/rhosocial/activerecord/backend/dialect/mixins/ddl_table.py
"""Dialect mixins for table DDL and constraint capability detection."""
from typing import Any, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.statements import (
        CreateTableExpression,
        CreateTableAsExpression,
        CreateTableLikeExpression,
        CreateTableCloneExpression,
        CreateTableFromTemplateExpression,
        CreateTableOptions,
        DropTableExpression,
        AlterTableExpression,
    )


class TableMixin:
    """Mixin adding support for table DDL statements.

    Provides capability probes for the various table features and generic
    rendering of CREATE TABLE, DROP TABLE, and ALTER TABLE statements.
    """

    def format_table(self, expr: "TableExpression") -> Tuple[str, tuple]:
        """Format a :class:`~...expression.core.TableExpression`.

        Reads ``name_need_quote``, ``schema_need_quote``, and
        ``alias_need_quote`` directly from the expression.

        Args:
            expr: Table expression carrying the name, optional schema, alias,
                and optional temporal options.

        Returns:
            Tuple of (SQL string, parameters tuple) for the table reference.
        """
        if expr.schema_name:
            table_sql = (
                f"{self.format_identifier(expr.schema_name, expr.schema_need_quote)}."
                f"{self.format_identifier(expr.name, expr.name_need_quote)}"
            )
        else:
            table_sql = self.format_identifier(expr.name, expr.name_need_quote)
        if expr.alias:
            table_sql = f"{table_sql} AS {self.format_identifier(expr.alias, expr.alias_need_quote)}"
        params: tuple = ()
        if expr.temporal_options:
            from ...expression.datetime import TemporalOptionsExpression
            temporal_expr = TemporalOptionsExpression(self, expr.temporal_options)
            result = self.format_temporal_options(temporal_expr)
            if result is not None:
                temporal_sql, temporal_params = result
                table_sql = f"{table_sql} {temporal_sql}"
                params += temporal_params
        return table_sql, params

    def supports_create_table(self) -> bool:
        """Whether CREATE TABLE is supported.

        Defaults to True.
        """
        return True

    def supports_drop_table(self) -> bool:
        """Whether DROP TABLE is supported.

        Defaults to True.
        """
        return True

    def supports_alter_table(self) -> bool:
        """Whether ALTER TABLE is supported.

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

    def supports_if_exists_table(self) -> bool:
        """Whether DROP TABLE IF EXISTS is supported.

        Defaults to False.
        """
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
        """Whether tablespace specification is supported.

        Defaults to False.
        """
        return False

    def supports_drop_column(self) -> bool:
        """Whether DROP COLUMN is supported.

        Defaults to True.
        """
        return True

    def supports_alter_column_type(self) -> bool:
        """Whether altering column data type is supported.

        Defaults to True.
        """
        return True

    def supports_alter_column_properties(self) -> bool:
        """Whether ALTER COLUMN SET DEFAULT / DROP DEFAULT etc. is supported.

        Defaults to False.
        """
        return False

    def supports_alter_table_index_actions(self) -> bool:
        """Whether ADD/DROP INDEX via ALTER TABLE is supported.

        Defaults to False.
        """
        return False

    def supports_multi_action_alter_table(self) -> bool:
        """Whether ALTER TABLE supports multiple comma-separated actions.

        Defaults to True. SQL Server requires one action per statement.
        """
        return True

    def supports_rename_column(self) -> bool:
        """Whether RENAME COLUMN is supported.

        Defaults to True.
        """
        return True

    def supports_rename_table(self) -> bool:
        """Whether RENAME TABLE is supported.

        Defaults to True.
        """
        return True

    def supports_create_table_like(self) -> bool:
        """Whether ``CREATE TABLE ... LIKE`` is supported.

        Defaults to ``False``. Backends that support the vendor extension
        override this to return ``True`` and inherit the generic
        :meth:`format_create_table_like_statement` rendering; backends with a
        different grammar override the formatter instead.
        """
        return False

    def supports_create_table_as(self) -> bool:
        """Whether ``CREATE TABLE ... AS <query>`` (CTAS) is supported.

        Defaults to ``True``: CTAS is broadly portable and the generic
        renderer emits the portable ``AS <query>`` form (no parentheses).
        """
        return True

    def supports_create_table_clone(self) -> bool:
        """Whether ``CREATE TABLE ... CLONE/COPY`` is supported.

        Defaults to ``False``; backends with zero-copy clone (Snowflake,
        BigQuery, ClickHouse) override this to return ``True``.
        """
        return False

    def supports_create_table_using_template(self) -> bool:
        """Whether ``CREATE TABLE ... USING TEMPLATE`` is supported.

        Defaults to ``False``; only Snowflake implements it.
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

    def supports_table_comment(self) -> bool:
        """Whether inline ``COMMENT 'text'`` on ``CREATE TABLE`` is supported.

        Defaults to ``False``; MySQL, MariaDB, and ClickHouse override to True.
        """
        return False

    def format_table_comment(self, comment: str) -> Tuple[str, tuple]:
        """Render a table-level ``COMMENT 'text'`` clause.

        Generic reusable implementation: ``COMMENT '<escaped>'``.  Dialects
        that advertise :meth:`supports_table_comment` inherit this rendering
        as-is; dialects with a different grammar override the method.

        The statement renderer appends the returned clause after the column
        list and storage options, before any PARTITION BY clause.
        """
        escaped = self._escape_sql_string(comment)
        return f"COMMENT '{escaped}'", ()

    def format_create_table_options(self, expr: "CreateTableOptions") -> Tuple[str, tuple]:
        """Format the ``CREATE`` header modifiers (generic reusable implementation).

        Renders the qualifiers between ``CREATE`` and ``TABLE``, in the
        portable order ``OR REPLACE``, then one of ``UNLOGGED`` / ``TRANSIENT``.
        Each flag is capability-gated:

        * ``or_replace`` -> :meth:`supports_create_or_replace_table`
        * ``unlogged``   -> :meth:`supports_unlogged_table`
        * ``transient``  -> :meth:`supports_transient_table`

        Args:
            expr: The CreateTableOptions clause carrying the flags.

        Returns:
            Tuple of (qualifier string, parameters tuple); empty string when no
            flag is set.

        Raises:
            UnsupportedFeatureError: If a requested flag is not supported by
                the dialect.
        """
        from ..exceptions import UnsupportedFeatureError

        parts: List[str] = []
        if expr.or_replace:
            if not self.supports_create_or_replace_table():
                raise UnsupportedFeatureError(self.name, "CREATE OR REPLACE TABLE")
            parts.append("OR REPLACE")
        if expr.unlogged:
            if not self.supports_unlogged_table():
                raise UnsupportedFeatureError(self.name, "CREATE UNLOGGED TABLE")
            parts.append("UNLOGGED")
        if expr.transient:
            if not self.supports_transient_table():
                raise UnsupportedFeatureError(self.name, "CREATE TRANSIENT TABLE")
            parts.append("TRANSIENT")
        return " ".join(parts), ()

    def format_create_table_like_statement(self, expr: "CreateTableLikeExpression") -> Tuple[str, tuple]:
        """Format ``CREATE TABLE ... LIKE`` (generic reusable implementation).

        Renders the common vendor form::

            CREATE [TEMPORARY] TABLE [IF NOT EXISTS] <table> LIKE <source>

        Dialects that advertise :meth:`supports_create_table_like` inherit
        this rendering as-is (e.g. MySQL/MariaDB/Snowflake/BigQuery);
        dialects with a different grammar (PostgreSQL's column-list
        ``(LIKE ... [INCLUDING ...])`` clause, ClickHouse's ``AS``) override
        it. Dialects that do not support the form keep
        :meth:`supports_create_table_like` at ``False``.

        ``expr.like_options`` (PostgreSQL INCLUDING/EXCLUDING) is intentionally
        ignored here; PostgreSQL overrides this method.

        Args:
            expr: The LIKE expression carrying the target ``table`` and the
                source ``like_table``.

        Returns:
            Tuple of (SQL string, parameters tuple) for the statement.

        Raises:
            UnsupportedFeatureError: If :meth:`supports_create_table_like` is
                False for the dialect.
        """
        from ..exceptions import UnsupportedFeatureError
        if not self.supports_create_table_like():
            raise UnsupportedFeatureError(self.name, "CREATE TABLE ... LIKE")
        temp_part = "TEMPORARY " if expr.temporary else ""
        not_exists_part = "IF NOT EXISTS " if expr.if_not_exists else ""
        table_sql, table_params = expr.table.to_sql()
        source_sql, source_params = expr.like_table.to_sql()
        parts = [
            f"CREATE {temp_part}TABLE {not_exists_part}{table_sql}",
            f"LIKE {source_sql}",
        ]
        return " ".join(parts), tuple(table_params) + tuple(source_params)

    def format_create_table_clone_statement(self, expr: "CreateTableCloneExpression") -> Tuple[str, tuple]:
        """Format ``CREATE TABLE ... CLONE/COPY`` (generic reusable implementation).

        Renders::

            CREATE [TEMPORARY] TABLE [IF NOT EXISTS] <table> {CLONE|COPY} <source>
                [COPY GRANTS]

        Backends with different grammar (ClickHouse ``CLONE AS``, BigQuery /
        Snowflake time-travel suffixes) override this method. Dialects that do
        not support the form keep :meth:`supports_create_table_clone` at
        ``False``.

        Args:
            expr: The clone expression carrying the target ``table``, the
                ``source_table``, the ``mode`` (CLONE/COPY) and ``copy_grants``.

        Returns:
            Tuple of (SQL string, parameters tuple) for the statement.

        Raises:
            UnsupportedFeatureError: If :meth:`supports_create_table_clone` is
                False for the dialect.
        """
        from ..exceptions import UnsupportedFeatureError
        if not self.supports_create_table_clone():
            raise UnsupportedFeatureError(self.name, "CREATE TABLE ... CLONE/COPY")
        temp_part = "TEMPORARY " if expr.temporary else ""
        not_exists_part = "IF NOT EXISTS " if expr.if_not_exists else ""
        table_sql, table_params = expr.table.to_sql()
        source_sql, source_params = expr.source_table.to_sql()
        parts = [
            f"CREATE {temp_part}TABLE {not_exists_part}{table_sql}",
            f"{expr.mode.value} {source_sql}",
        ]
        if expr.copy_grants:
            parts.append("COPY GRANTS")
        return " ".join(parts), tuple(table_params) + tuple(source_params)

    def format_create_table_using_template(self, expr: "CreateTableFromTemplateExpression") -> Tuple[str, tuple]:
        """Format ``CREATE TABLE ... USING TEMPLATE`` (generic reusable implementation).

        Renders::

            CREATE [TEMPORARY] TABLE [IF NOT EXISTS] <table>
                USING TEMPLATE <template>

        Args:
            expr: The template expression carrying the target ``table`` and the
                ``template`` query.

        Returns:
            Tuple of (SQL string, parameters tuple) for the statement.

        Raises:
            UnsupportedFeatureError: If
                :meth:`supports_create_table_using_template` is False for the
                dialect.
        """
        from ..exceptions import UnsupportedFeatureError
        if not self.supports_create_table_using_template():
            raise UnsupportedFeatureError(self.name, "CREATE TABLE ... USING TEMPLATE")
        temp_part = "TEMPORARY " if expr.temporary else ""
        not_exists_part = "IF NOT EXISTS " if expr.if_not_exists else ""
        table_sql, table_params = expr.table.to_sql()
        template_sql, template_params = expr.template.to_sql()
        parts = [
            f"CREATE {temp_part}TABLE {not_exists_part}{table_sql}",
            f"USING TEMPLATE {template_sql}",
        ]
        return " ".join(parts), tuple(table_params) + tuple(template_params)

    def format_create_table_statement(self, expr: "CreateTableExpression") -> Tuple[str, tuple]:
        """Format CREATE TABLE statement (generic implementation).

        Handles the explicit-schema form only (columns, constraints, storage,
        tablespace, inherits, partition). CTAS / LIKE / CLONE have their own
        expressions and formatters -- this method does not touch them.

        Args:
            expr: CreateTableExpression carrying the table reference, column
                definitions, constraints, and optional storage, tablespace,
                inherits, and partition clauses.

        Returns:
            Tuple of (SQL string, parameters tuple) for the statement.
        """
        all_params: List[Any] = []
        options_part = ""
        table_options = getattr(expr, "table_options", None)
        if table_options is not None:
            options_sql, options_params = table_options.to_sql()
            if options_sql:
                options_part = options_sql + " "
            all_params.extend(options_params)
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
        for t_const in expr.table_constraints:
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
        return "".join(parts), tuple(all_params)

    def format_create_table_as_statement(self, expr: "CreateTableAsExpression") -> Tuple[str, tuple]:
        """Format ``CREATE TABLE ... AS <query>`` (generic CTAS implementation).

        Emits the portable form::

            CREATE [TEMPORARY] TABLE [IF NOT EXISTS] <table>
                [<storage options>] AS <query> [WITH [NO] DATA]

        The query is rendered **without parentheses** -- parenthesising is
        rejected by SQLite (and several other engines). ``WITH [NO] DATA`` is
        only appended when :attr:`CreateTableAsExpression.with_data` is set
        (PostgreSQL semantics).

        Args:
            expr: CreateTableAsExpression carrying the target table and query.

        Returns:
            Tuple of (SQL string, parameters tuple) for the statement.
        """
        from ..exceptions import UnsupportedFeatureError

        if not self.supports_create_table_as():
            raise UnsupportedFeatureError(self.name, "CREATE TABLE ... AS")

        all_params: List[Any] = []
        temp_part = "TEMPORARY " if expr.temporary else ""
        not_exists_part = "IF NOT EXISTS " if expr.if_not_exists else ""
        table_sql, table_params = expr.table.to_sql()
        all_params.extend(table_params)
        parts = [f"CREATE {temp_part}TABLE {not_exists_part}{table_sql}"]

        if expr.storage_options is not None:
            storage_sql, storage_params = expr.storage_options.to_sql()
            if storage_sql:
                parts.append(storage_sql)
                all_params.extend(storage_params)

        query_sql, query_params = expr.as_query.to_sql()
        parts.append(f"AS {query_sql}")
        all_params.extend(query_params)

        if expr.with_data is True:
            parts.append(" WITH DATA")
        elif expr.with_data is False:
            parts.append(" WITH NO DATA")

        return " ".join(parts), tuple(all_params)

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

        Args:
            expr: DropTableExpression carrying the table reference, optional
                ``if_exists`` flag, and optional ``cascade`` flag.

        Returns:
            Tuple of (SQL string, parameters tuple) for the statement.

        Raises:
            UnsupportedFeatureError: If CASCADE or RESTRICT is requested but not
                supported by the dialect.
        """
        from ..exceptions import UnsupportedFeatureError

        parts = ["DROP TABLE"]
        if expr.if_exists:
            if not self.supports_if_exists_table():
                raise UnsupportedFeatureError(
                    self.name,
                    "DROP TABLE IF EXISTS",
                )
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
        """Format ALTER TABLE statement (generic implementation).

        When the dialect does not support multiple actions in one ALTER TABLE
        (e.g. SQL Server), each action produces a separate statement joined
        by semicolons.

        Args:
            expr: AlterTableExpression carrying the table name and the list of
                actions to render.

        Returns:
            Tuple of (SQL string, parameters tuple) for the statement.
        """
        all_params: List[Any] = []
        action_parts = []
        for action in expr.actions:
            action_part, action_params = action.to_sql()
            action_parts.append(action_part)
            all_params.extend(action_params)

        if not action_parts:
            return f"ALTER TABLE {self.format_identifier(expr.table_name)}", ()

        if self.supports_multi_action_alter_table():
            combined = ", ".join(action_parts)
            return f"ALTER TABLE {self.format_identifier(expr.table_name)} {combined}", tuple(all_params)

        stmts = []
        for part in action_parts:
            stmts.append(f"ALTER TABLE {self.format_identifier(expr.table_name)} {part}")
        return "; ".join(stmts), tuple(all_params)


class ConstraintMixin:
    """Mixin for DDL constraint capability detection.

    Default values are True for all methods, enabling DummyDialect
    to validate the full constraint implementation. Actual backends
    override methods as needed to reflect their real capabilities.
    """

    # Basic constraint types (SQL-86/SQL-92)

    def supports_primary_key_constraint(self) -> bool:
        """Whether PRIMARY KEY constraints are supported.

        Defaults to True.
        """
        return True

    def supports_unique_constraint(self) -> bool:
        """Whether UNIQUE constraints are supported.

        Defaults to True.
        """
        return True

    def supports_not_null_constraint(self) -> bool:
        """Whether NOT NULL constraints are supported.

        Defaults to True.
        """
        return True

    def supports_check_constraint(self) -> bool:
        """Whether CHECK constraints are supported and enforced.

        Defaults to True.
        """
        return True

    def supports_foreign_key_constraint(self) -> bool:
        """Whether FOREIGN KEY constraints are supported.

        Defaults to True.
        """
        return True

    # FK referential actions (SQL-92)

    def supports_fk_on_delete(self) -> bool:
        """Whether ON DELETE referential actions are supported.

        Defaults to True.
        """
        return True

    def supports_fk_on_update(self) -> bool:
        """Whether ON UPDATE referential actions are supported.

        Defaults to True.
        """
        return True

    # FK match modes (SQL:1999)

    def supports_fk_match(self) -> bool:
        """Whether MATCH {SIMPLE|PARTIAL|FULL} is supported.

        Defaults to True.
        """
        return True

    # Constraint deferral (SQL:1999)

    def supports_deferrable_constraint(self) -> bool:
        """Whether DEFERRABLE / INITIALLY DEFERRED/IMMEDIATE is supported.

        Defaults to True.
        """
        return True

    # Constraint enforcement control (SQL:2016)

    def supports_constraint_enforced(self) -> bool:
        """Whether ENFORCED / NOT ENFORCED constraint control is supported.

        Defaults to True.
        """
        return True

    # ALTER TABLE constraint operations (SQL-92)

    def supports_add_constraint(self) -> bool:
        """Whether ALTER TABLE ADD CONSTRAINT is supported.

        Defaults to True.
        """
        return True

    def supports_drop_constraint(self) -> bool:
        """Whether ALTER TABLE DROP CONSTRAINT is supported.

        Defaults to True.
        """
        return True
