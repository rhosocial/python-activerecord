from ..protocols.ddl.ddl_column_support import DDLColumnSupport
from rhosocial.activerecord.backend.expression.statements import (
    TableCheckConstraint,
    TableForeignKeyConstraint,
)
from .ddl_table import normalize_foreign_key_match_type
from ...expression.objects import Index, Table
from ...expression.core import Literal
from ...expression.bases import BaseExpression, ToSQLProtocol
from typing import Any, List, Tuple, TYPE_CHECKING
# src/rhosocial/activerecord/backend/dialect/mixins/ddl_column.py
"""DDL column formatting: column references, definitions, constraints, and
ALTER TABLE column/constraint actions."""

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.statements.ddl_table import (
        ColumnCheckConstraint,
        ColumnConstraint,
        ColumnDefaultConstraint,
        ColumnForeignKeyConstraint,
        ColumnGeneratedConstraint,
        ColumnNotNullConstraint,
        ColumnNullableConstraint,
        ColumnPrimaryKeyConstraint,
        ColumnUniqueConstraint,
        TableCheckConstraint,
        TableConstraint,
        TableExcludeConstraint,
        TableForeignKeyConstraint,
        TablePrimaryKeyConstraint,
        TableUniqueConstraint,
    )
    from ...expression.core import Column
    from ...expression.statements.ddl_alter import (
        AddColumnAction,
        AddIndexAction,
        AddTableConstraintAction,
        AlterColumnAction,
        AlterConstraintAction,
        ChangeColumnAction,
        DropColumnAction,
        DropIndexAction,
        DropTableConstraintAction,
        ModifyColumnAction,
        RenameColumnAction,
        RenameTableAction,
        ValidateConstraintAction,
    )
    from ...expression.statements.ddl_table import (
        CharacterSetClause,
        CollationClause,
        ColumnClause,
        ColumnCommentClause,
        ColumnDefinition,
        DefaultValueClause,
        IndexDefinition,
        ReferencesClause,
        StorageOptionsExpression,
    )


class DDLColumnMixin(DDLColumnSupport):
    """Mixin for DDL column definition and ALTER TABLE action formatting."""





    def format_column_comment_clause(self, expr: "ColumnCommentClause") -> "Tuple[str, tuple]":
        """Render the inline ``COMMENT '<text>'`` column expr.

        Generic reusable implementation: ``COMMENT '<escaped>'`` with a
        leading space, so it composes directly after the column definition
        fragment.  Dialects that advertise :meth:`supports_column_comment`
        inherit this rendering as-is; dialects with a different grammar
        (BigQuery's ``OPTIONS(description='<text>')``) override the method.

        Args:
            expr: The :class:`ColumnCommentClause` carrying the text.

        Returns:
            Tuple of (SQL fragment with leading space, parameters tuple).

        Raises:
            UnsupportedFeatureError: If :meth:`supports_column_comment` is
                False for the dialect.
        """
        from ..exceptions import UnsupportedFeatureError

        if not self.supports_column_comment():
            raise UnsupportedFeatureError(
                self.name, "COLUMN COMMENT",
                f"{self.name} does not support COLUMN COMMENT."
            )
        escaped = self.escape_sql_string(expr.comment)
        return f" COMMENT '{escaped}'", ()





    def format_column(self, expr: "Column") -> "Tuple[str, tuple]":
        """Format a :class:`~...expression.core.Column`.

        Renders an optional ``schema.table.column`` qualifier chain followed
        by an optional alias. Each component is quoted independently according
        to the expression's ``schema_need_quote``, ``table_need_quote``,
        ``name_need_quote``, and ``alias_need_quote`` fields.

        Args:
            expr: The column reference to render.

        Returns:
            A ``(sql, params)`` tuple. Column references never carry bind
            parameters, so ``params`` is always empty.
        """
        if expr.schema_name and expr.table:
            col_sql = (
                f"{self.format_identifier(expr.schema_name, expr.schema_need_quote)}."
                f"{self.format_identifier(expr.table, expr.table_need_quote)}."
                f"{self.format_identifier(expr.name, expr.name_need_quote)}"
            )
        elif expr.table:
            col_sql = (
                f"{self.format_identifier(expr.table, expr.table_need_quote)}."
                f"{self.format_identifier(expr.name, expr.name_need_quote)}"
            )
        else:
            col_sql = self.format_identifier(expr.name, expr.name_need_quote)

        if expr.alias:
            col_sql = f"{col_sql} AS {self.format_identifier(expr.alias, expr.alias_need_quote)}"
        return col_sql, ()




    def format_column_attributes(self, expr: "ColumnDefinition") -> "Tuple[str, tuple]":
        """Render all of a column's clauses as one definition fragment.

        Shared by the generic formatter and by backend ``format_column_definition``
        overrides (which otherwise would not render the ``attributes`` channel).
        Returns the concatenated fragments with a leading space each, and the
        accumulated parameters.

        Order is the order the clauses were built in; this method does not sort.
        """
        sql = ""
        params: List[Any] = []
        for attr in expr.attributes or ():
            attr_sql, attr_params = self.format_column_attribute(attr)
            sql += attr_sql
            params.extend(attr_params)
        return sql, tuple(params)

    def format_collation_clause(self, expr: "CollationClause") -> "Tuple[str, tuple]":
        """Render a column's ``COLLATE <name>`` expr.

        Generic reusable implementation: ``COLLATE <name>`` with the name
        spelled bare, which is what every backend emitted before the expr
        became an expression node. Quoting it as an identifier would be the
        more defensive choice, but it changes the SQL of seven backends and is
        not this change's business. Backends that want a quoted specification
        rather than a bare name (Snowflake, BigQuery) override this.

        Args:
            expr: The expr carrying the collation name.

        Returns:
            A ``(sql, params)`` tuple (params is always empty for DDL).
        """
        return f" COLLATE {expr.name}", ()

    def format_character_set_clause(
        self, expr: "CharacterSetClause"
    ) -> "Tuple[str, tuple]":
        """Render a column's ``CHARACTER SET <name>`` expr.

        Generic reusable implementation: ``CHARACTER SET <name>`` with the name
        spelled bare, for the same reason as :meth:`format_collation_clause`.

        Args:
            expr: The expr carrying the character set name.

        Returns:
            A ``(sql, params)`` tuple (params is always empty for DDL).
        """
        return f" CHARACTER SET {expr.name}", ()

    def format_column_definition(self, expr: "ColumnDefinition") -> "Tuple[str, tuple]":
        """Format a column definition clause (name, type, constraints, comment).

        Args:
            expr: The column definition expression to render.

        Returns:
            A ``(sql, params)`` tuple. DDL accepts no bind parameters, so
            ``params`` is always empty.
        """
        all_params: List[Any] = []
        type_sql, _ = expr.data_type.to_sql()
        col_sql = f"{self.format_identifier(expr.name)} {type_sql}"

        attr_sql, attr_params = self.format_column_attributes(expr)
        col_sql += attr_sql
        all_params.extend(attr_params)
        for constraint in expr.constraints:
            suffix, params = self.format_column_constraint(constraint)
            col_sql += suffix
            all_params.extend(params)

        if expr.generated_expression is not None:
            gen_sql, gen_params = expr.generated_expression.to_sql()
            col_sql += gen_sql
            all_params.extend(gen_params)

        if expr.comment is not None:
            comment_sql, comment_params = self.format_column_comment_clause(expr.comment)
            col_sql += comment_sql
            all_params.extend(comment_params)
        return col_sql, tuple(all_params)

    def format_column_generated_constraint(
        self, expr: "ColumnGeneratedConstraint"
    ) -> "Tuple[str, tuple]":
        """Format a column-level ``GENERATED ALWAYS AS`` branch.

        Renders ``GENERATED ALWAYS AS (<expr>) STORED|VIRTUAL`` and delegates
        to :meth:`supports_generated_columns` /
        :meth:`supports_stored_generated_columns` /
        :meth:`supports_virtual_generated_columns` for capability gating.

        Backends that use non-standard syntax (e.g. Firebird's ``COMPUTED BY``)
        should override this method.

        Args:
            expr: The branch carrying the generating expression and the
                storage type.

        Returns:
            A ``(sql, params)`` tuple with a leading space.

        Raises:
            UnsupportedFeatureError: If generated columns (or the requested
                storage type) are not supported by this dialect.
        """
        from ...expression.statements.ddl_table import GeneratedColumnType
        from ..exceptions import UnsupportedFeatureError

        if not self.supports_generated_columns():
            raise UnsupportedFeatureError(
                self.name,
                "Generated columns",
                f"{self.name} does not support generated (computed) columns.",
            )

        inner_sql, inner_params = expr.expression.to_sql()

        if expr.storage_type == GeneratedColumnType.STORED:
            if not self.supports_stored_generated_columns():
                raise UnsupportedFeatureError(
                    self.name,
                    "STORED generated columns",
                    f"{self.name} does not support STORED generated columns.",
                )
            storage = " STORED"
        else:
            if not self.supports_virtual_generated_columns():
                raise UnsupportedFeatureError(
                    self.name,
                    "VIRTUAL generated columns",
                    f"{self.name} does not support VIRTUAL generated columns.",
                )
            storage = " VIRTUAL"

        return f" GENERATED ALWAYS AS ({inner_sql}){storage}", ()

    def format_constraint_enforcement(self, expr: "ColumnConstraint") -> str:
        """Render the ``[NOT] ENFORCED`` trait a expr asked for.

        The kinds that may carry the trait come from the standard-derived
        whitelist (SQL:2016 fixes them to PRIMARY KEY, UNIQUE, FOREIGN KEY,
        and CHECK); a dialect narrows that set inside its own expr
        formatter and may not widen it.

        Returns:
            ``""`` when the expr asked for neither spelling, else the
            ``ENFORCED`` / ``NOT ENFORCED`` fragment.

        Raises:
            TypeError: The flags are not bools.
            ValueError: The expr asked for both spellings at once.
            UnsupportedFeatureError: The dialect does not support the trait.
        """
        enforced = expr.enforced
        not_enforced = expr.not_enforced
        if not enforced and not not_enforced:
            return ""
        if not isinstance(enforced, bool) or not isinstance(not_enforced, bool):
            raise TypeError("expr enforced/not_enforced must be bools")
        # The clause refuses both spellings at construction, but an attribute
        # assigned afterwards bypasses __init__, so the pair is re-checked
        # here as the last line of defence.
        if enforced and not_enforced:
            raise ValueError("enforced and not_enforced are mutually exclusive")
        # Which kinds may carry the trait is settled by the node now:
        # ``ColumnConstraint``/``TableConstraint`` refuse a branch that cannot,
        # at construction. Nothing here has to guess which kind this is.
        if not self.supports_constraint_enforced():
            from ..exceptions import UnsupportedFeatureError

            raise UnsupportedFeatureError(self.name, "ENFORCED/NOT ENFORCED expr")
        return "ENFORCED" if enforced else "NOT ENFORCED"

    def format_constraint_validation(self, expr: "TableConstraint") -> str:
        """Render the ``NOT VALID`` trait a table expr asked for.

        Serves ``ALTER TABLE ADD CONSTRAINT``; PostgreSQL accepts the trait on
        CHECK and FOREIGN KEY only, and that restriction lives here -- asked of
        the branch, which is what names the kind.

        Returns:
            ``""`` when the expr asked for no validation state or the
            default VALIDATE, else ``" NOT VALID"``.

        Raises:
            TypeError: ``validation`` is not a ``ConstraintValidation``.
            ValueError: The trait rides a branch that cannot carry it.
            UnsupportedFeatureError: The dialect has no ``NOT VALID``.
        """
        from ...expression.statements import (
            ConstraintValidation,
            TableCheckConstraint,
            TableForeignKeyConstraint,
        )
        from ..exceptions import UnsupportedFeatureError

        validation = expr.validation
        if validation is None:
            return ""
        if not isinstance(validation, ConstraintValidation):
            raise TypeError(
                "expr validation must be a ConstraintValidation, got "
                f"{type(validation).__name__}"
            )
        if validation is ConstraintValidation.VALIDATE:
            return ""
        if not isinstance(expr.branch, (TableCheckConstraint, TableForeignKeyConstraint)):
            raise ValueError("NOT VALID is only valid for CHECK and FOREIGN KEY constraints")
        if not self.supports_constraint_novalidate():
            raise UnsupportedFeatureError(self.name, "NOT VALID expr")
        return " NOT VALID"

    def format_column_constraint(self, expr: "ColumnConstraint") -> "Tuple[str, tuple]":
        """Format one column-level expr clause.

        Renders what the grammar hangs on the **production** -- the
        ``CONSTRAINT <name>`` prefix, then the branch's own body, then the
        trailing traits -- and dispatches to the branch's formatter for the
        body. Which kind this is, is the branch's business, not this
        method's: the fat node that used to switch on a ``constraint_type``
        field here is gone, and so is the silent acceptance of a trait the
        kind cannot carry (the clause refuses it at construction).

        Args:
            expr: The column expr clause to render.

        Returns:
            A ``(sql, params)`` tuple. The ``sql`` value is prefixed with a
            leading space so it can be appended directly to a column
            definition.

        Raises:
            UnsupportedFeatureError: The dialect refuses the named prefix, the
                trait, or the branch's own construct.
        """
        prefix = ""
        if expr.name:
            if not self.supports_constraint_naming():
                from ..exceptions import UnsupportedFeatureError

                raise UnsupportedFeatureError(
                    self.name, "CONSTRAINT name on a column expr"
                )
            prefix = f" CONSTRAINT {self.format_identifier(expr.name)}"
        branch_sql, branch_params = self.format_constraint_branch(expr.branch)
        return f"{prefix}{branch_sql}{self.format_constraint_traits(expr)}", tuple(
            branch_params
        )

    def format_constraint_branch(self, expr: "BaseExpression") -> "Tuple[str, tuple]":
        """Render a constraint expr through its own formatter.

        The expr declares which formatter spells it (``format_method``),
        so a dialect that spells one kind differently overrides that one
        formatter and nothing else.

        Args:
            expr: The expr node to render.

        Returns:
            A ``(sql, params)`` tuple, with a leading space for the
            column-level branches.
        """
        formatter = getattr(self, expr.format_method, None)
        if formatter is None:
            raise NotImplementedError(
                f"{self.name} has no {expr.format_method}() for "
                f"{type(expr).__name__}; declare the constraint on backends "
                f"that support it."
            )
        return formatter(expr)

    def format_constraint_traits(self, expr: "ColumnConstraint") -> Tuple[str, str]:
        """Render the production-level traits of a column expr.

        Both halves of one trait: the deferral half (``DEFERRABLE`` /
        ``NOT DEFERRABLE``), which PostgreSQL's grammar puts on PRIMARY KEY,
        UNIQUE and FOREIGN KEY, and the enforcement half (``ENFORCED`` /
        ``NOT ENFORCED``). Only the foreign-key branch used to read them, so
        a request on a PRIMARY KEY was dropped without a word; rendering them
        here is what the production level is for.

        Args:
            expr: The clause whose traits are rendered.

        Returns:
            The fragment to append, including its leading space, or ``""``.

        Raises:
            UnsupportedFeatureError: The dialect declares neither the deferral
                trait nor the enforcement trait.
        """
        parts = []
        wants_deferral = (
            expr.deferrable
            or expr.not_deferrable
            or expr.initially_deferred
            or expr.initially_immediate
        )
        if wants_deferral:
            from ..exceptions import UnsupportedFeatureError

            if not self.supports_deferrable_constraint():
                raise UnsupportedFeatureError(
                    self.name, "DEFERRABLE / INITIALLY expr trait"
                )
            if expr.deferrable or expr.not_deferrable:
                parts.append("DEFERRABLE" if expr.deferrable else "NOT DEFERRABLE")
            if expr.initially_deferred or expr.initially_immediate:
                parts.append(
                    "INITIALLY DEFERRED"
                    if expr.initially_deferred
                    else "INITIALLY IMMEDIATE"
                )
        enforcement = self.format_constraint_enforcement(expr)
        if enforcement:
            parts.append(enforcement)
        return f" {' '.join(parts)}" if parts else ""

    def format_column_primary_key_constraint(
        self, expr: "ColumnPrimaryKeyConstraint"
    ) -> "Tuple[str, tuple]":
        """Format a column-level ``PRIMARY KEY`` branch.

        Split out because a dialect may add to the clause itself: SQLite
        spells ``AUTOINCREMENT`` as part of this grammar and nowhere else.

        Args:
            expr: The branch to render.

        Returns:
            A ``(sql, params)`` tuple with a leading space.

        Raises:
            UnsupportedFeatureError: The dialect has no primary keys.
        """
        from ..exceptions import UnsupportedFeatureError

        if not self.supports_primary_key_constraint():
            raise UnsupportedFeatureError(self.name, "PRIMARY KEY column expr")
        # The flag is not rendered here: AUTOINCREMENT is part of SQLite's
        # grammar, so the dialect that spells it says so in an override of
        # this formatter. Core renders the expr the standard defines.
        return " PRIMARY KEY", ()

    def format_column_unique_constraint(
        self, expr: "ColumnUniqueConstraint"
    ) -> "Tuple[str, tuple]":
        """Format a column-level ``UNIQUE`` branch."""
        from ..exceptions import UnsupportedFeatureError

        if not self.supports_unique_constraint():
            raise UnsupportedFeatureError(self.name, "UNIQUE column expr")
        return " UNIQUE", ()

    def format_column_not_null_constraint(
        self, expr: "ColumnNotNullConstraint"
    ) -> "Tuple[str, tuple]":
        """Format a column-level ``NOT NULL`` branch."""
        from ..exceptions import UnsupportedFeatureError

        if not self.supports_not_null_constraint():
            raise UnsupportedFeatureError(self.name, "NOT NULL column expr")
        return " NOT NULL", ()

    def format_column_nullable_constraint(
        self, expr: "ColumnNullableConstraint"
    ) -> "Tuple[str, tuple]":
        """Format a column-level ``NULL`` branch.

        An explicitly nullable column is part of every SQL grammar rather
        than an optional construct, so it consults no probe.
        """
        return " NULL", ()

    def format_column_check_constraint(
        self, expr: "ColumnCheckConstraint"
    ) -> "Tuple[str, tuple]":
        """Format a column-level ``CHECK`` branch.

        Args:
            expr: The branch whose ``condition`` is rendered.

        Returns:
            A ``(sql, params)`` tuple with a leading space.

        Raises:
            UnsupportedFeatureError: The dialect has no CHECK constraints.
        """
        from ..exceptions import UnsupportedFeatureError

        if not self.supports_check_constraint():
            raise UnsupportedFeatureError(self.name, "CHECK column expr")
        check_sql, check_params = expr.condition.to_sql()
        return f" CHECK ({check_sql})", tuple(check_params)

    def format_default_value_clause(self, expr: "DefaultValueClause") -> "Tuple[str, tuple]":
        """Format the value clause of a ``DEFAULT`` constraint.

        The clause normalised its value at construction: a ``DEFAULT`` position
        carries no bind parameters, so whatever arrives is a ``Literal`` with
        ``inline`` set. Rendering it is therefore the literal's own rendering,
        and anything that still produces a bind value is a value the caller
        marked as binding in a position that cannot bind -- a refusal, not a
        fallback.

        Args:
            expr: The ``DefaultValueClause`` carrying the value.

        Returns:
            A ``(sql, params)`` tuple; params is always empty for DDL.

        Raises:
            ValueError: The expression value still carries bind parameters
                (e.g. a ``RawSQL`` with bound values), which a DEFAULT
                position cannot accept.
        """
        value_sql, value_params = expr.value.to_sql()
        if value_params:
            raise ValueError("DEFAULT value must render without bind parameters")
        return value_sql, ()

    def format_column_default_constraint(
        self, expr: "ColumnDefaultConstraint"
    ) -> "Tuple[str, tuple]":
        """Format a column-level ``DEFAULT`` branch.

        The value is always rendered inline (DDL carries no bind parameters;
        ``ColumnDefaultConstraint`` declares ``inline_binding = True``);
        value rendering is delegated to :meth:`format_default_value_clause`.

        Args:
            expr: The branch whose ``value`` is rendered.

        Returns:
            A ``(sql, params)`` tuple with a leading space.
        """
        from ...expression.statements.ddl_table import DefaultValueClause

        value = expr.value
        if isinstance(value, DefaultValueClause):
            value_clause = value
        else:
            value_clause = DefaultValueClause(self, value)
        value_sql, _ = self.format_default_value_clause(value_clause)
        return f" DEFAULT {value_sql}", ()


    @staticmethod
    def _referential_action_value(action: Any) -> str:
        """Validate and normalize a referential action."""
        from ...expression.statements import ReferentialAction

        if isinstance(action, ReferentialAction):
            return action.value
        if not isinstance(action, str):
            raise TypeError("referential action must be a ReferentialAction or string")
        value = " ".join(action.strip().upper().split())
        for candidate in (value, value.replace(" ", "_")):
            try:
                return ReferentialAction(candidate).value
            except ValueError:
                continue
        raise ValueError(
            f"Invalid referential action '{action}'. Must be one of: "
            f"{', '.join(member.value for member in ReferentialAction)}"
        )


    def format_table_primary_key_constraint(
        self, expr: "TablePrimaryKeyConstraint"
    ) -> "Tuple[str, tuple]":
        """Format the body of a ``PRIMARY KEY`` table expr.

        Args:
            t_const: The expr whose ``columns`` are rendered.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is always empty.

        Raises:
            ValueError: If no columns are specified.
        """
        if not expr.columns:
            raise ValueError("PRIMARY KEY expr must have at least one column specified.")
        cols_str = ", ".join(self.format_identifier(col) for col in expr.columns)
        return f"PRIMARY KEY ({cols_str})", ()

    def format_table_unique_constraint(
        self, expr: "TableUniqueConstraint"
    ) -> "Tuple[str, tuple]":
        """Format the body of a ``UNIQUE`` table expr.

        Args:
            t_const: The expr whose ``columns`` are rendered.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is always empty.

        Raises:
            ValueError: If no columns are specified.
        """
        if not expr.columns:
            raise ValueError("UNIQUE expr must have at least one column specified.")
        cols_str = ", ".join(self.format_identifier(col) for col in expr.columns)
        return f"UNIQUE ({cols_str})", ()

    def format_table_check_constraint(
        self, expr: "TableCheckConstraint"
    ) -> "Tuple[str, tuple]":
        """Format a table-level ``CHECK`` expr body.

        Args:
            t_const: The expr whose ``check_condition`` is rendered.

        Returns:
            A ``(sql, params)`` tuple.

        Raises:
            ValueError: If ``check_condition`` is ``None``.
        """
        if expr.condition is None:
            raise ValueError("CHECK expr must have a check condition specified.")
        check_sql, check_params = expr.condition.to_sql()
        return f"CHECK ({check_sql})", tuple(check_params)

    def format_table_foreign_key_constraint(
        self, expr: "TableForeignKeyConstraint"
    ) -> "Tuple[str, tuple]":
        """Format a table-level ``FOREIGN KEY`` branch.

        Args:
            expr: The branch carrying the local columns, the referenced
                table and columns, and the referential actions.

        Returns:
            A ``(sql, params)`` tuple; ``sql`` has no leading space.

        Raises:
            ValueError: The local columns, the referenced columns or the
                referenced table are missing.
        """
        if not expr.columns:
            raise ValueError("FOREIGN KEY expr must have at least one local column specified.")
        referenced_table, referenced_columns = expr.references
        if not referenced_columns:
            raise ValueError("FOREIGN KEY expr must have at least one foreign key column specified.")
        if not referenced_table:
            raise ValueError("FOREIGN KEY expr must have a foreign key table specified.")
        from ...expression.statements.ddl_table import ReferencesClause

        cols_str = ", ".join(self.format_identifier(col) for col in expr.columns)

        references = ReferencesClause(
            self,
            referenced_table,
            list(referenced_columns),
            on_delete=expr.on_delete,
            on_update=expr.on_update,
            match_type=expr.match_type,
        )
        ref_sql, ref_params = self.format_references_clause(references)
        return f"FOREIGN KEY ({cols_str}) {ref_sql}", tuple(ref_params)

    def format_table_exclude_constraint(
        self, expr: "TableExcludeConstraint"
    ) -> "Tuple[str, tuple]":
        """Format a table-level ``EXCLUDE`` branch.

        Core has no EXCLUDE grammar to fall back on, so the default refuses
        by name rather than rendering SQL a server would reject. The branch
        exists because the expr is enumerable (规范 4.9's table
        expr kinds), and a dialect whose server can spell it overrides
        this formatter.

        Args:
            expr: The branch carrying the columns, the operator and the
                optional index method.

        Returns:
            A ``(sql, params)`` tuple.

        Raises:
            UnsupportedFeatureError: Always, unless a dialect overrides this.
        """
        from ..exceptions import UnsupportedFeatureError

        if not self.supports_exclude_constraint():
            raise UnsupportedFeatureError(self.name, "EXCLUDE expr")
        raise UnsupportedFeatureError(self.name, "EXCLUDE expr formatter")

    def format_table_constraint(self, expr: "TableConstraint") -> "Tuple[str, tuple]":
        """Format a table-level constraint clause.

        The table counterpart of :meth:`format_column_constraint`: the
        ``CONSTRAINT <name>`` prefix, then the branch's body, then the
        enforcement trait. The branch says which kind this is, so this method
        no longer switches on a tag -- and ``EXCLUDE`` is a branch like the
        rest rather than an enum member nothing could render.

        Args:
            expr: The table constraint clause to render.

        Returns:
            A ``(sql, params)`` tuple; ``sql`` is empty when no clause parts
            are produced.

        Raises:
            UnsupportedFeatureError: The dialect refuses the named prefix, the
                trait, or the branch's construct.
        """
        from ..exceptions import UnsupportedFeatureError

        parts = []
        if expr.name:
            if not self.supports_constraint_naming():
                raise UnsupportedFeatureError(
                    self.name, "CONSTRAINT name on a table constraint"
                )
            parts.append(f"CONSTRAINT {self.format_identifier(expr.name)}")
        branch_sql, branch_params = self.format_constraint_branch(expr.branch)
        if branch_sql:
            parts.append(branch_sql)
        wants_deferral = (
            expr.deferrable
            or expr.not_deferrable
            or expr.initially_deferred
            or expr.initially_immediate
        )
        if wants_deferral:
            if not self.supports_deferrable_constraint():
                raise UnsupportedFeatureError(
                    self.name, "DEFERRABLE / INITIALLY constraint trait"
                )
            if expr.deferrable or expr.not_deferrable:
                parts.append("DEFERRABLE" if expr.deferrable else "NOT DEFERRABLE")
            if expr.initially_deferred or expr.initially_immediate:
                parts.append(
                    "INITIALLY DEFERRED"
                    if expr.initially_deferred
                    else "INITIALLY IMMEDIATE"
                )
        enforcement = self.format_constraint_enforcement(expr)
        if enforcement:
            parts.append(enforcement)
        return " ".join(parts), tuple(branch_params)

    def format_storage_options_expression(self, expr: "StorageOptionsExpression") -> "Tuple[str, tuple]":
        """Format a ``WITH (...)`` storage-options clause.

        Each option value is rendered as an inline SQL literal via
        ``inline_sql_literal``.

        Args:
            expr: A :class:`StorageOptionsExpression` holding the options mapping.

        Returns:
            A ``(sql, params)`` tuple; ``sql`` is empty when the mapping is
            empty.
        """
        storage_parts = []
        for key, value in expr.options.items():
            quoted_key = self.format_identifier(key)
            rendered_value = self.inline_sql_literal(value)
            storage_parts.append(f"{quoted_key} = {rendered_value}")
        if storage_parts:
            return " WITH (" + ", ".join(storage_parts) + ")", ()
        return "", ()

    def format_add_column_action(self, expr: "AddColumnAction") -> "Tuple[str, tuple]":
        """Format an ``ADD COLUMN`` ALTER TABLE expr.

        Args:
            expr: The expr carrying the column definition to add.

        Returns:
            A ``(sql, params)`` tuple.

        Raises:
            UnsupportedFeatureError: If IF NOT EXISTS is requested but not
                supported by the dialect.
        """
        from ..exceptions import UnsupportedFeatureError
        column_sql, column_params = self.format_column_definition(expr.column)
        if expr.if_not_exists:
            if not self.supports_add_column_if_not_exists():
                raise UnsupportedFeatureError(
                    self.name, "ADD COLUMN IF NOT EXISTS",
                    f"{self.name} does not support ADD COLUMN IF NOT EXISTS."
                )
            return f"ADD COLUMN IF NOT EXISTS {column_sql}", column_params
        return f"ADD COLUMN {column_sql}", column_params

    def format_drop_column_action(self, expr: "DropColumnAction") -> "Tuple[str, tuple]":
        """Format a ``DROP COLUMN`` ALTER TABLE expr.

        Emits ``DROP COLUMN IF EXISTS`` when the expr requests it.

        Args:
            expr: The expr carrying the column name to drop.

        Returns:
            A ``(sql, params)`` tuple with empty parameters.

        Raises:
            UnsupportedFeatureError: If the dialect does not support
                ``DROP COLUMN``, or if IF EXISTS is requested but not
                supported by the dialect.
        """
        from ..exceptions import UnsupportedFeatureError
        if not self.supports_drop_column():
            raise UnsupportedFeatureError(
                self.name, "ALTER TABLE DROP COLUMN",
                f"{self.name} does not support DROP COLUMN.",
            )
        if expr.if_exists:
            if not self.supports_drop_column_if_exists():
                raise UnsupportedFeatureError(
                    self.name, "DROP COLUMN IF EXISTS",
                    f"{self.name} does not support DROP COLUMN IF EXISTS."
                )
            return f"DROP COLUMN IF EXISTS {self.format_identifier(expr.column_name)}", ()
        return f"DROP COLUMN {self.format_identifier(expr.column_name)}", ()

    def format_alter_column_action(self, expr: "AlterColumnAction") -> "Tuple[str, tuple]":
        """Format an ``ALTER COLUMN`` ALTER TABLE expr.

        Handles ``SET DATA TYPE`` (a type, rendered through the dialect),
        string values (escaped and inlined), expression values rendered
        through ``to_sql``, and plain values inlined via
        ``inline_sql_literal``.

        Args:
            expr: The expr carrying the column name, operation, and
                optional new value.

        Returns:
            A ``(sql, params)`` tuple.

        Raises:
            UnsupportedFeatureError: If the dialect does not support the
                requested alteration (data-type changes and column-property
                changes are gated by separate support switches).
        """
        from ..exceptions import UnsupportedFeatureError
        all_params: List[Any] = []
        
        from ...expression.statements.ddl_alter import operation_spelling

        operation_str = operation_spelling(expr.operation)
        if operation_str == "SET DATA TYPE":
            if not self.supports_alter_column_type():
                raise UnsupportedFeatureError(
                    self.name, "ALTER COLUMN SET DATA TYPE",
                    f"{self.name} does not support changing a column data type.",
                )
        elif not self.supports_alter_column_properties():
            raise UnsupportedFeatureError(
                self.name, "ALTER COLUMN",
                f"{self.name} does not support altering column properties "
                "(SET/DROP DEFAULT, SET/DROP NOT NULL).",
            )
        column_part = f"ALTER COLUMN {self.format_identifier(expr.column_name)} {operation_str}"
        if expr.new_value is not None:
            if operation_str == "SET DATA TYPE":
                type_sql, _ = expr.new_value.to_sql()
                column_part += f" {type_sql}"
            elif isinstance(expr.new_value, str):
                # DDL accepts no bind parameters, so the value is written into
                # the SQL text. The literal is the controlled path: it escapes
                # and quotes exactly as DEFAULT does.
                value_sql, value_params = Literal(
                    self, expr.new_value, inline=True
                ).to_sql()
                column_part += f" {value_sql}"
            elif isinstance(expr.new_value, ToSQLProtocol):
                if isinstance(expr.new_value, Literal):
                    # The value carries its own DDL decision; the controlled
                    # path escapes and quotes it exactly as DEFAULT does.
                    value_sql, value_params = Literal(
                        self, expr.new_value.value, inline=True
                    ).to_sql()
                else:
                    value_sql, value_params = expr.new_value.to_sql()
                    if value_params:
                        raise ValueError(
                            "ALTER COLUMN value must render without bind parameters"
                        )
                column_part += f" {value_sql}"
            else:
                column_part += f" {self.inline_sql_literal(expr.new_value)}"
        if expr.cascade:
            column_part += " CASCADE"
        return column_part, tuple(all_params)

    def format_add_table_constraint_action(self, expr: "AddTableConstraintAction") -> "Tuple[str, tuple]":
        """Format an ``ADD CONSTRAINT`` ALTER TABLE expr.

        Args:
            expr: The expr carrying the table constraint to add.

        Returns:
            A ``(sql, params)`` tuple prefixed with ``ADD``.

        Raises:
            UnsupportedFeatureError: If the dialect does not support
                ``ALTER TABLE ADD CONSTRAINT``.
        """
        from ..exceptions import UnsupportedFeatureError
        if not self.supports_add_constraint():
            raise UnsupportedFeatureError(self.name, "ALTER TABLE ADD CONSTRAINT")
        constraint_sql, params = self.format_table_constraint(expr.constraint)
        if not constraint_sql:
            return "ADD UNKNOWN CONSTRAINT", ()
        validation_sql = self.format_constraint_validation(expr.constraint)
        return f"ADD {constraint_sql}{validation_sql}", tuple(params)



    def format_drop_table_constraint_action(self, expr: "DropTableConstraintAction") -> "Tuple[str, tuple]":
        """Format a ``DROP CONSTRAINT`` ALTER TABLE expr.

        Args:
            expr: The expr carrying the constraint name and optional
                cascade flag.

        Returns:
            A ``(sql, params)`` tuple with empty parameters.

        Raises:
            UnsupportedFeatureError: If the dialect does not support
                ``ALTER TABLE DROP CONSTRAINT``.
        """
        from ..exceptions import UnsupportedFeatureError
        if not self.supports_drop_constraint():
            raise UnsupportedFeatureError(self.name, "ALTER TABLE DROP CONSTRAINT")
        if expr.if_exists and not self.supports_drop_constraint_if_exists():
            raise UnsupportedFeatureError(
                self.name, "DROP CONSTRAINT IF EXISTS",
                f"{self.name} does not support DROP CONSTRAINT IF EXISTS."
            )
        if_exists = "IF EXISTS " if expr.if_exists else ""
        result = f"DROP CONSTRAINT {if_exists}{self.format_identifier(expr.constraint_name)}"
        if expr.cascade:
            result += " CASCADE"
        return result, ()

    def format_index_definition(self, expr: "IndexDefinition") -> "Tuple[str, tuple]":
        """Format an :class:`~...expression.statements.IndexDefinition` clause.

        Args:
            expr: The index definition carrying name, columns, uniqueness,
                and optional index type.

        Returns:
            A ``(sql, params)`` tuple with empty parameters.
        """
        if expr.type and not self.supports_index_type():
            from ..exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(
                self.name, "index type (USING)",
                f"{self.name} does not support index types.",
            )
        all_params: List[Any] = []
        col_parts = []
        for col in expr.columns:
            if isinstance(col, ToSQLProtocol):
                col_sql, col_params = col.to_sql()
                col_parts.append(col_sql)
                all_params.extend(col_params)
            else:
                col_parts.append(self.format_identifier(str(col)))
        cols_str = ", ".join(col_parts)
        unique_str = "UNIQUE " if expr.unique else ""
        type_str = f" USING {expr.type}" if expr.type else ""
        return (
            f"{unique_str}{self.format_identifier(expr.name)}{type_str} ({cols_str})",
            tuple(all_params),
        )

    def format_add_index_action(self, expr: "AddIndexAction") -> "Tuple[str, tuple]":
        """Format an ``ADD INDEX`` ALTER TABLE expr.

        Args:
            expr: The expr carrying the index definition to add.

        Returns:
            A ``(sql, params)`` tuple with empty parameters.

        Raises:
            UnsupportedFeatureError: If the dialect does not support
                ``ALTER TABLE ADD INDEX``.
        """
        from ..exceptions import UnsupportedFeatureError
        if not self.supports_alter_table_index_actions():
            raise UnsupportedFeatureError(
                self.name, "ALTER TABLE ADD INDEX",
                f"{self.name} does not support ALTER TABLE ADD INDEX.",
            )
        columns = ", ".join(
            self.format_identifier(col) for col in expr.index.columns
        )
        return (
            f"ADD INDEX {self.format_identifier(expr.index.name)} ({columns})",
            (),
        )

    def format_drop_index_action(self, expr: "DropIndexAction") -> "Tuple[str, tuple]":
        """Format a ``DROP INDEX`` ALTER TABLE expr.

        Emits ``DROP INDEX IF EXISTS`` when the expr requests it.

        Args:
            expr: The expr carrying the index to drop.

        Returns:
            A ``(sql, params)`` tuple with empty parameters.

        Raises:
            TypeError: ``DropIndexAction.index`` is not an Index. Another object kind
            would have had its own name rendered as the index's.
            UnsupportedFeatureError: If the dialect does not support
                ``ALTER TABLE DROP INDEX``.
        """
        if not isinstance(expr.index, Index):
            raise TypeError(
                f"DropIndexAction.index must be an Index, "
                f"got {type(expr.index).__name__}"
            )
        from ..exceptions import UnsupportedFeatureError
        if not self.supports_alter_table_index_actions():
            raise UnsupportedFeatureError(
                self.name, "ALTER TABLE DROP INDEX",
                f"{self.name} does not support ALTER TABLE DROP INDEX.",
            )
        index_sql, index_params = expr.index.to_sql()
        head = "DROP INDEX IF EXISTS" if expr.if_exists else "DROP INDEX"
        return f"{head} {index_sql}", index_params

    def format_rename_column_action(self, expr: "RenameColumnAction") -> "Tuple[str, tuple]":
        """Format a ``RENAME COLUMN`` ALTER TABLE expr.

        Args:
            expr: The expr carrying the old and new column names.

        Returns:
            A ``(sql, params)`` tuple with empty parameters.

        Raises:
            UnsupportedFeatureError: If the dialect does not support
                ``ALTER TABLE RENAME COLUMN``.
        """
        from ..exceptions import UnsupportedFeatureError
        if not self.supports_rename_column():
            raise UnsupportedFeatureError(
                self.name, "ALTER TABLE RENAME COLUMN",
                f"{self.name} does not support RENAME COLUMN.",
            )
        return (
            f"RENAME COLUMN {self.format_identifier(expr.old_name)} TO {self.format_identifier(expr.new_name)}",
            (),
        )

    def format_rename_table_action(self, expr: "RenameTableAction") -> "Tuple[str, tuple]":
        """Format a ``RENAME TO`` ALTER TABLE expr.

        Args:
            expr: The expr carrying the new table name.

        Returns:
            A ``(sql, params)`` tuple with empty parameters.

        Raises:
            UnsupportedFeatureError: If the dialect does not support
                ``ALTER TABLE RENAME TO``.
        """
        from ..exceptions import UnsupportedFeatureError
        if not self.supports_rename_table():
            raise UnsupportedFeatureError(
                self.name, "ALTER TABLE RENAME TO",
                f"{self.name} does not support RENAME TABLE.",
            )
        return f"RENAME TO {self.format_identifier(expr.new_name)}", ()

    def format_modify_column_action(self, expr: "ModifyColumnAction") -> "Tuple[str, tuple]":
        """Format a ``MODIFY COLUMN`` ALTER TABLE expr.

        The core implementation always raises, since ``MODIFY COLUMN`` is
        MySQL/MariaDB-specific; those backends override this method.

        Args:
            expr: The expr carrying the column definition to apply.

        Raises:
            UnsupportedFeatureError: Always, at the core layer.
        """
        from ..exceptions import UnsupportedFeatureError
        raise UnsupportedFeatureError(self.name, "MODIFY COLUMN")

    def format_change_column_action(self, expr: "ChangeColumnAction") -> "Tuple[str, tuple]":
        """Format a ``CHANGE COLUMN`` ALTER TABLE expr.

        The core implementation always raises, since ``CHANGE COLUMN`` is
        MySQL/MariaDB-specific; those backends override this method.

        Args:
            expr: The expr carrying the old name and new column definition.

        Raises:
            UnsupportedFeatureError: Always, at the core layer.
        """
        from ..exceptions import UnsupportedFeatureError
        raise UnsupportedFeatureError(self.name, "CHANGE COLUMN")
