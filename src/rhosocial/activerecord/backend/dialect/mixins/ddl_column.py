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


class DDLColumnMixin:
    """Mixin for DDL column definition and ALTER TABLE action formatting."""

    def supports_foreign_key_on_delete(self) -> bool:
        """Whether FOREIGN KEY ON DELETE is supported (defaults to True)."""
        return True

    def supports_foreign_key_on_update(self) -> bool:
        """Whether FOREIGN KEY ON UPDATE is supported (defaults to True)."""
        return True

    def supports_fk_match(self) -> bool:
        """Whether FOREIGN KEY MATCH is supported (defaults to False)."""
        return False

    def supports_column_comment(self) -> bool:
        """Whether COLUMN COMMENT is supported (defaults to False)."""
        return False

    def format_column_comment_clause(self, clause: "ColumnCommentClause") -> Tuple[str, tuple]:
        """Render the inline ``COMMENT '<text>'`` column clause.

        Generic reusable implementation: ``COMMENT '<escaped>'`` with a
        leading space, so it composes directly after the column definition
        fragment.  Dialects that advertise :meth:`supports_column_comment`
        inherit this rendering as-is; dialects with a different grammar
        (BigQuery's ``OPTIONS(description='<text>')``) override the method.

        Args:
            clause: The :class:`ColumnCommentClause` carrying the text.

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
        escaped = self._escape_sql_string(clause.comment)
        return f" COMMENT '{escaped}'", ()

    def supports_column_collation(self) -> bool:
        """Whether a column-level ``COLLATE <name>`` attribute is supported.

        Defaults to True — the SQL-standard form is valid on every backend
        that renders column definitions; backends whose column COLLATE is
        meaningless override this to return False.
        """
        return True

    def supports_column_character_set(self) -> bool:
        """Whether a column-level ``CHARACTER SET <name>`` attribute is
        supported.

        Defaults to False — character sets are a MySQL/MariaDB concept, not
        part of the generic dialect; those backends override this to return
        True.
        """
        return False

    def format_column_attribute(self, attr: "ColumnClause") -> Tuple[str, Tuple]:
        """Render one selected column clause as a definition fragment.

        The subject is an expression-layer node: :class:`CollationClause`,
        :class:`CharacterSetClause`, :class:`IdentityClause` or
        :class:`AutoIncrementClause`. Each names its own formatter through
        ``format_method``, so this method only has to dispatch.

        An AR-layer ``ColumnAttribute`` is accepted at the entrance and
        translated before dispatch, because no deriver turns a model's
        declarations into clauses yet -- that layer does not exist, so this is
        currently the only route from ``UseColumnAttributes`` to SQL. The
        translation lives in its own method so it can be deleted whole when a
        deriver lands. It has to be here rather than in
        :meth:`format_column_attributes` because backend
        ``format_column_definition`` overrides call this method directly.
        """
        from ..exceptions import UnsupportedFeatureError
        from ...expression.statements.ddl_table import (
            CharacterSetClause,
            CollationClause,
        )

        if not isinstance(attr, BaseExpression):
            # An AR-layer ColumnAttribute, not an expression. The test is the
            # type, not `hasattr(attr, "format_method")`: that probed a field
            # every expression declares, and it also answered False for an
            # expression whose base property raises -- which is a different
            # question than "is this one of ours". §11.2: asserting to a known
            # base is the way to ask what an argument is.
            original = attr
            attr = self.translate_ar_attribute(original)
            if attr is None:
                raise UnsupportedFeatureError(
                    self.name,
                    f"COLUMN CLAUSE {type(original).__name__}",
                    f"{self.name} cannot render this column clause; declare it "
                    f"only on backends that support it.",
                )
        if isinstance(attr, CollationClause):
            if not self.supports_column_collation():
                raise UnsupportedFeatureError(self.name, "column-level COLLATE")
            return self.format_collation_clause(attr)
        if isinstance(attr, CharacterSetClause):
            if not self.supports_column_character_set():
                raise UnsupportedFeatureError(self.name, "column-level CHARACTER SET")
            return self.format_character_set_clause(attr)
        formatter = getattr(self, attr.format_method, None)
        if formatter is None:
            raise UnsupportedFeatureError(
                self.name,
                f"{type(attr).__name__} formatter",
                f"{self.name} has no formatter for the column clause "
                f"{type(attr).__name__}; declare it only on backends that "
                f"support it.",
            )
        return formatter(attr)

    def translate_ar_attribute(self, attr: Any) -> Any:
        """Turn an AR-layer ``ColumnAttribute`` into an expression-layer clause.

        Transitional, and the reason is a missing layer rather than a
        preference: nothing in the library turns a model's ``UseColumnAttributes``
        declaration into column clauses, so the AR-layer objects reach
        ``ColumnDefinition.attributes`` directly and the dialect has to accept
        them. Once that translation layer exists it belongs there, and this
        method goes with it. Public because backend ``format_column_definition``
        overrides call it: a protocol member that outside callers need is
        public even when its implementation is transitional.
        """
        from ....base.ddl import (
            CharacterSetAttribute,
            CollationAttribute,
            IdentityAttribute,
        )
        from ...expression.statements.ddl_table import (
            CharacterSetClause,
            CollationClause,
            IdentityClause,
        )

        if isinstance(attr, IdentityAttribute):
            # The AR-layer IdentityAttribute keeps its tri-state until the AR
            # layer's exposure of the split is decided (out of scope for this
            # round); translate it to the expression layer's two parameters.
            return IdentityClause(
                self,
                attr.generation,
                start=attr.start,
                increment=attr.increment,
                minvalue=attr.minvalue,
                maxvalue=attr.maxvalue,
                cycle=attr.cycle is True,
                no_cycle=attr.cycle is False,
            )
        if isinstance(attr, CollationAttribute):
            return CollationClause(self, attr.name)
        if isinstance(attr, CharacterSetAttribute):
            return CharacterSetClause(self, attr.name)
        return None

    def format_column(self, expr: "Column") -> Tuple[str, Tuple]:
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

    def supports_add_column_if_not_exists(self) -> bool:
        """Whether ``ADD COLUMN IF NOT EXISTS`` is supported.

        Defaults to ``False``; backends that support the vendor extension
        override this to return ``True``.
        """
        return False

    def supports_drop_column_if_exists(self) -> bool:
        """Whether ``DROP COLUMN IF EXISTS`` is supported.

        Defaults to ``False``; backends that support the vendor extension
        override this to return ``True``.
        """
        return False

    def supports_drop_constraint_if_exists(self) -> bool:
        """Whether ``DROP CONSTRAINT IF EXISTS`` is supported.

        Defaults to ``False``; backends that support the vendor extension
        override this to return ``True``.
        """
        return False

    def format_column_attributes(self, col_def: "ColumnDefinition") -> Tuple[str, Tuple]:
        """Render all of a column's clauses as one definition fragment.

        Shared by the generic formatter and by backend ``format_column_definition``
        overrides (which otherwise would not render the ``attributes`` channel).
        Returns the concatenated fragments with a leading space each, and the
        accumulated parameters.

        Order is the order the clauses were built in; this method does not sort.
        """
        sql = ""
        params: List[Any] = []
        for attr in col_def.attributes or ():
            attr_sql, attr_params = self.format_column_attribute(attr)
            sql += attr_sql
            params.extend(attr_params)
        return sql, tuple(params)

    def format_collation_clause(self, clause: "CollationClause") -> Tuple[str, Tuple]:
        """Render a column's ``COLLATE <name>`` clause.

        Generic reusable implementation: ``COLLATE <name>`` with the name
        spelled bare, which is what every backend emitted before the clause
        became an expression node. Quoting it as an identifier would be the
        more defensive choice, but it changes the SQL of seven backends and is
        not this change's business. Backends that want a quoted specification
        rather than a bare name (Snowflake, BigQuery) override this.

        Args:
            clause: The clause carrying the collation name.

        Returns:
            A ``(sql, params)`` tuple (params is always empty for DDL).
        """
        return f" COLLATE {clause.name}", ()

    def format_character_set_clause(
        self, clause: "CharacterSetClause"
    ) -> Tuple[str, Tuple]:
        """Render a column's ``CHARACTER SET <name>`` clause.

        Generic reusable implementation: ``CHARACTER SET <name>`` with the name
        spelled bare, for the same reason as :meth:`format_collation_clause`.

        Args:
            clause: The clause carrying the character set name.

        Returns:
            A ``(sql, params)`` tuple (params is always empty for DDL).
        """
        return f" CHARACTER SET {clause.name}", ()

    def format_column_definition(self, col_def: "ColumnDefinition") -> Tuple[str, Tuple]:
        """Format a column definition clause (name, type, constraints, comment).

        Args:
            col_def: The column definition expression to render.

        Returns:
            A ``(sql, params)`` tuple. DDL accepts no bind parameters, so
            ``params`` is always empty.
        """
        all_params: List[Any] = []
        type_sql, _ = col_def.data_type.to_sql()
        col_sql = f"{self.format_identifier(col_def.name)} {type_sql}"

        attr_sql, attr_params = self.format_column_attributes(col_def)
        col_sql += attr_sql
        all_params.extend(attr_params)
        for constraint in col_def.constraints:
            suffix, params = self.format_column_constraint(constraint)
            col_sql += suffix
            all_params.extend(params)

        if col_def.generated_expression is not None:
            gen_sql, gen_params = col_def.generated_expression.to_sql()
            col_sql += gen_sql
            all_params.extend(gen_params)

        if col_def.comment is not None:
            comment_sql, comment_params = self.format_column_comment_clause(col_def.comment)
            col_sql += comment_sql
            all_params.extend(comment_params)
        return col_sql, tuple(all_params)

    def format_column_generated_constraint(
        self, constraint: "ColumnGeneratedConstraint"
    ) -> Tuple[str, Tuple]:
        """Format a column-level ``GENERATED ALWAYS AS`` branch.

        Renders ``GENERATED ALWAYS AS (<expr>) STORED|VIRTUAL`` and delegates
        to :meth:`supports_generated_columns` /
        :meth:`supports_stored_generated_columns` /
        :meth:`supports_virtual_generated_columns` for capability gating.

        Backends that use non-standard syntax (e.g. Firebird's ``COMPUTED BY``)
        should override this method.

        Args:
            constraint: The branch carrying the generating expression and the
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

        inner_sql = self._format_ddl_condition(constraint.expression)

        if constraint.storage_type == GeneratedColumnType.STORED:
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

    def _format_constraint_enforcement(self, constraint: "ColumnConstraint") -> str:
        """Render the ``[NOT] ENFORCED`` trait a constraint asked for.

        The kinds that may carry the trait come from the standard-derived
        whitelist (SQL:2016 fixes them to PRIMARY KEY, UNIQUE, FOREIGN KEY,
        and CHECK); a dialect narrows that set inside its own constraint
        formatter and may not widen it.

        Returns:
            ``""`` when the constraint asked for neither spelling, else the
            ``ENFORCED`` / ``NOT ENFORCED`` fragment.

        Raises:
            TypeError: The flags are not bools.
            ValueError: The constraint asked for both spellings at once.
            UnsupportedFeatureError: The dialect does not support the trait.
        """
        enforced = constraint.enforced
        not_enforced = constraint.not_enforced
        if not enforced and not not_enforced:
            return ""
        if not isinstance(enforced, bool) or not isinstance(not_enforced, bool):
            raise TypeError("constraint enforced/not_enforced must be bools")
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

            raise UnsupportedFeatureError(self.name, "ENFORCED/NOT ENFORCED constraint")
        return "ENFORCED" if enforced else "NOT ENFORCED"

    def _format_constraint_validation(self, constraint: "TableConstraint") -> str:
        """Render the ``NOT VALID`` trait a table constraint asked for.

        Serves ``ALTER TABLE ADD CONSTRAINT``; PostgreSQL accepts the trait on
        CHECK and FOREIGN KEY only, and that restriction lives here -- asked of
        the branch, which is what names the kind.

        Returns:
            ``""`` when the constraint asked for no validation state or the
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

        validation = constraint.validation
        if validation is None:
            return ""
        if not isinstance(validation, ConstraintValidation):
            raise TypeError(
                "constraint validation must be a ConstraintValidation, got "
                f"{type(validation).__name__}"
            )
        if validation is ConstraintValidation.VALIDATE:
            return ""
        if not isinstance(constraint.branch, (TableCheckConstraint, TableForeignKeyConstraint)):
            raise ValueError("NOT VALID is only valid for CHECK and FOREIGN KEY constraints")
        if not self.supports_constraint_novalidate():
            raise UnsupportedFeatureError(self.name, "NOT VALID constraint")
        return " NOT VALID"

    def _format_ddl_condition(self, predicate: Any) -> str:
        """Render a DDL-side condition tree: inline text, no bind values.

        A DDL syntax position accepts no bind parameters, and the tree is
        rendered as the caller wrote it -- no pass lifts anything into it.
        Every ``Literal`` in a condition tree belongs to the caller, so each one
        says whether it binds. Miss that and this is where it shows: the tree
        renders, the parameters are non-empty, and the statement would carry a
        bind value into DDL that has nowhere to put it.

        The check is therefore the contract, not a safety net. It names the
        fix rather than guarding against a hypothetical.
        """
        check_sql, check_params = predicate.to_sql()
        if check_params:
            raise ValueError(
                "DDL condition must not contain bind parameters; pass each "
                "value as Literal(value, inline=True)"
            )
        return check_sql

    def format_column_constraint(self, constraint: "ColumnConstraint") -> Tuple[str, Tuple]:
        """Format one column-level constraint clause.

        Renders what the grammar hangs on the **production** -- the
        ``CONSTRAINT <name>`` prefix, then the branch's own body, then the
        trailing traits -- and dispatches to the branch's formatter for the
        body. Which kind this is, is the branch's business, not this
        method's: the fat node that used to switch on a ``constraint_type``
        field here is gone, and so is the silent acceptance of a trait the
        kind cannot carry (the clause refuses it at construction).

        Args:
            constraint: The column constraint clause to render.

        Returns:
            A ``(sql, params)`` tuple. The ``sql`` value is prefixed with a
            leading space so it can be appended directly to a column
            definition.

        Raises:
            UnsupportedFeatureError: The dialect refuses the named prefix, the
                trait, or the branch's own construct.
        """
        prefix = ""
        if constraint.name:
            if not self.supports_constraint_naming():
                from ..exceptions import UnsupportedFeatureError

                raise UnsupportedFeatureError(
                    self.name, "CONSTRAINT name on a column constraint"
                )
            prefix = f" CONSTRAINT {self.format_identifier(constraint.name)}"
        branch_sql, branch_params = self.format_constraint_branch(constraint.branch)
        return f"{prefix}{branch_sql}{self.format_constraint_traits(constraint)}", tuple(
            branch_params
        )

    def format_constraint_branch(self, branch: "BaseExpression") -> Tuple[str, tuple]:
        """Render a constraint branch through its own formatter.

        The branch declares which formatter spells it (``format_method``),
        so a dialect that spells one kind differently overrides that one
        formatter and nothing else.

        Args:
            branch: The branch node to render.

        Returns:
            A ``(sql, params)`` tuple, with a leading space for the
            column-level branches.
        """
        formatter = getattr(self, branch.format_method, None)
        if formatter is None:
            raise NotImplementedError(
                f"{self.name} has no {branch.format_method}() for "
                f"{type(branch).__name__}; declare the constraint on backends "
                f"that support it."
            )
        return formatter(branch)

    def format_constraint_traits(self, constraint: "ColumnConstraint") -> Tuple[str, str]:
        """Render the production-level traits of a column constraint.

        Both halves of one trait: the deferral half (``DEFERRABLE`` /
        ``NOT DEFERRABLE``), which PostgreSQL's grammar puts on PRIMARY KEY,
        UNIQUE and FOREIGN KEY, and the enforcement half (``ENFORCED`` /
        ``NOT ENFORCED``). Only the foreign-key branch used to read them, so
        a request on a PRIMARY KEY was dropped without a word; rendering them
        here is what the production level is for.

        Args:
            constraint: The clause whose traits are rendered.

        Returns:
            The fragment to append, including its leading space, or ``""``.

        Raises:
            UnsupportedFeatureError: The dialect declares neither the deferral
                trait nor the enforcement trait.
        """
        parts = []
        wants_deferral = (
            constraint.deferrable
            or constraint.not_deferrable
            or constraint.initially_deferred
            or constraint.initially_immediate
        )
        if wants_deferral:
            from ..exceptions import UnsupportedFeatureError

            if not self.supports_deferrable_constraint():
                raise UnsupportedFeatureError(
                    self.name, "DEFERRABLE / INITIALLY constraint trait"
                )
            if constraint.deferrable or constraint.not_deferrable:
                parts.append("DEFERRABLE" if constraint.deferrable else "NOT DEFERRABLE")
            if constraint.initially_deferred or constraint.initially_immediate:
                parts.append(
                    "INITIALLY DEFERRED"
                    if constraint.initially_deferred
                    else "INITIALLY IMMEDIATE"
                )
        enforcement = self._format_constraint_enforcement(constraint)
        if enforcement:
            parts.append(enforcement)
        return f" {' '.join(parts)}" if parts else ""

    def format_column_primary_key_constraint(
        self, constraint: "ColumnPrimaryKeyConstraint"
    ) -> Tuple[str, Tuple]:
        """Format a column-level ``PRIMARY KEY`` branch.

        Split out because a dialect may add to the clause itself: SQLite
        spells ``AUTOINCREMENT`` as part of this grammar and nowhere else.

        Args:
            constraint: The branch to render.

        Returns:
            A ``(sql, params)`` tuple with a leading space.

        Raises:
            UnsupportedFeatureError: The dialect has no primary keys.
        """
        from ..exceptions import UnsupportedFeatureError

        if not self.supports_primary_key_constraint():
            raise UnsupportedFeatureError(self.name, "PRIMARY KEY column constraint")
        # The flag is not rendered here: AUTOINCREMENT is part of SQLite's
        # grammar, so the dialect that spells it says so in an override of
        # this formatter. Core renders the constraint the standard defines.
        return " PRIMARY KEY", ()

    def format_column_unique_constraint(
        self, constraint: "ColumnUniqueConstraint"
    ) -> Tuple[str, Tuple]:
        """Format a column-level ``UNIQUE`` branch."""
        from ..exceptions import UnsupportedFeatureError

        if not self.supports_unique_constraint():
            raise UnsupportedFeatureError(self.name, "UNIQUE column constraint")
        return " UNIQUE", ()

    def format_column_not_null_constraint(
        self, constraint: "ColumnNotNullConstraint"
    ) -> Tuple[str, Tuple]:
        """Format a column-level ``NOT NULL`` branch."""
        from ..exceptions import UnsupportedFeatureError

        if not self.supports_not_null_constraint():
            raise UnsupportedFeatureError(self.name, "NOT NULL column constraint")
        return " NOT NULL", ()

    def format_column_nullable_constraint(
        self, constraint: "ColumnNullableConstraint"
    ) -> Tuple[str, Tuple]:
        """Format a column-level ``NULL`` branch.

        An explicitly nullable column is part of every SQL grammar rather
        than an optional construct, so it consults no probe.
        """
        return " NULL", ()

    def format_column_check_constraint(
        self, constraint: "ColumnCheckConstraint"
    ) -> Tuple[str, Tuple]:
        """Format a column-level ``CHECK`` branch.

        Args:
            constraint: The branch whose ``condition`` is rendered.

        Returns:
            A ``(sql, params)`` tuple with a leading space.

        Raises:
            UnsupportedFeatureError: The dialect has no CHECK constraints.
        """
        from ..exceptions import UnsupportedFeatureError

        if not self.supports_check_constraint():
            raise UnsupportedFeatureError(self.name, "CHECK column constraint")
        check_sql = self._format_ddl_condition(constraint.condition)
        return f" CHECK ({check_sql})", ()

    def format_default_value_clause(self, expr: "DefaultValueClause") -> Tuple[str, Tuple]:
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
        self, constraint: "ColumnDefaultConstraint"
    ) -> Tuple[str, Tuple]:
        """Format a column-level ``DEFAULT`` branch.

        The value is always rendered inline (DDL carries no bind parameters;
        ``ColumnDefaultConstraint`` declares ``inline_binding = True``);
        value rendering is delegated to :meth:`format_default_value_clause`.

        Args:
            constraint: The branch whose ``value`` is rendered.

        Returns:
            A ``(sql, params)`` tuple with a leading space.
        """
        from ...expression.statements.ddl_table import DefaultValueClause

        value = constraint.value
        if isinstance(value, DefaultValueClause):
            value_clause = value
        else:
            value_clause = DefaultValueClause(self, value)
        value_sql, _ = self.format_default_value_clause(value_clause)
        return f" DEFAULT {value_sql}", ()

    def format_references_clause(self, expr: "ReferencesClause") -> Tuple[str, Tuple]:
        """Format a ``REFERENCES`` clause (shared by column/table foreign keys).

        Renders ``REFERENCES <table>(<cols>)`` plus the referential actions and
        deferrability. Backends with different syntax override this.

        Args:
            expr: The ``ReferencesClause`` carrying the referenced table/columns
                and optional actions.

        Returns:
            A ``(sql, params)`` tuple (params is always empty for DDL).

        Raises:
            TypeError: ``ReferencesClause.referenced_table`` is not a Table. Another
            object kind would have had its own name rendered as the referenced
            relation.
            ValueError: If the referenced table has no columns.
        """
        from ..exceptions import UnsupportedFeatureError
        from ...expression.statements import ReferentialAction

        if not isinstance(expr.referenced_table, Table):
            raise TypeError(
                f"ReferencesClause.referenced_table must be a Table, "
                f"got {type(expr.referenced_table).__name__}"
            )
        if not expr.referenced_columns:
            raise ValueError("REFERENCES clause requires at least one referenced column.")
        ref_cols_str = ", ".join(self.format_identifier(col) for col in expr.referenced_columns)
        result = f"REFERENCES {expr.referenced_table.to_sql()[0]}({ref_cols_str})"
        if expr.match_type is not None:
            match_type = normalize_foreign_key_match_type(expr.match_type)
            if not self.supports_fk_match():
                raise UnsupportedFeatureError(
                    self.name, "FOREIGN KEY MATCH",
                    f"{self.name} does not support MATCH for foreign keys."
                )
            result += f" MATCH {match_type.value}"
        on_delete = (
            self._referential_action_value(expr.on_delete)
            if expr.on_delete is not None
            else None
        )
        if on_delete is not None and on_delete != ReferentialAction.NO_ACTION.value:
            if not self.supports_foreign_key_on_delete():
                raise UnsupportedFeatureError(
                    self.name, "FOREIGN KEY ON DELETE",
                    f"{self.name} does not support ON DELETE for foreign keys."
                )
            result += f" ON DELETE {on_delete}"
        on_update = (
            self._referential_action_value(expr.on_update)
            if expr.on_update is not None
            else None
        )
        if on_update is not None and on_update != ReferentialAction.NO_ACTION.value:
            if not self.supports_foreign_key_on_update():
                raise UnsupportedFeatureError(
                    self.name, "FOREIGN KEY ON UPDATE",
                    f"{self.name} does not support ON UPDATE for foreign keys."
                )
            result += f" ON UPDATE {on_update}"
        # INITIALLY ... is an independent constraint attribute in the SQL
        # grammar (PostgreSQL accepts it alone), so it is rendered whenever it
        # was requested rather than dropped when DEFERRABLE is absent. Both
        # spellings are authorised by the same capability.
        has_deferral = (
            expr.deferrable
            or expr.not_deferrable
            or expr.initially_deferred
            or expr.initially_immediate
        )
        if has_deferral and not self.supports_deferrable_constraint():

            raise UnsupportedFeatureError(
                self.name, "DEFERRABLE / INITIALLY clause on a foreign key"
            )
        if expr.deferrable or expr.not_deferrable:
            result += " DEFERRABLE" if expr.deferrable else " NOT DEFERRABLE"
        if expr.initially_deferred or expr.initially_immediate:
            result += (
                " INITIALLY DEFERRED"
                if expr.initially_deferred
                else " INITIALLY IMMEDIATE"
            )
        return result, ()

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

    def format_column_fk_constraint(
        self, constraint: "ColumnForeignKeyConstraint"
    ) -> Tuple[str, Tuple]:
        """Format a column-level ``REFERENCES`` branch.

        Delegates the reference body to :meth:`format_references_clause`. The
        deferral traits are the production's to render (see
        :meth:`format_constraint_traits`), so they are not passed down here.

        Args:
            constraint: The branch whose ``references`` are rendered.

        Returns:
            A ``(sql, params)`` tuple with a leading space.

        Raises:
            UnsupportedFeatureError: The dialect has no foreign keys.
        """
        from ..exceptions import UnsupportedFeatureError
        from ...expression.statements.ddl_table import ReferencesClause

        # Known coupling: this is the table-level probe reused for the
        # column-level grammar. A dialect whose *column* REFERENCES clause is
        # unusable while its table-level FOREIGN KEY works (SQL Server) cannot
        # be expressed until the two levels get separate probes.
        if not self.supports_foreign_key_constraint():
            raise UnsupportedFeatureError(self.name, "REFERENCES column constraint")

        referenced_table, referenced_columns = constraint.references

        references = ReferencesClause(
            self,
            referenced_table,
            referenced_columns,
            on_delete=constraint.on_delete,
            on_update=constraint.on_update,
            match_type=constraint.match_type,
        )
        ref_sql, ref_params = self.format_references_clause(references)
        return f" {ref_sql}", tuple(ref_params)

    def format_table_primary_key_constraint(
        self, constraint: "TablePrimaryKeyConstraint"
    ) -> Tuple[str, tuple]:
        """Format the body of a ``PRIMARY KEY`` table constraint.

        Args:
            t_const: The constraint whose ``columns`` are rendered.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is always empty.

        Raises:
            ValueError: If no columns are specified.
        """
        if not constraint.columns:
            raise ValueError("PRIMARY KEY constraint must have at least one column specified.")
        cols_str = ", ".join(self.format_identifier(col) for col in constraint.columns)
        return f"PRIMARY KEY ({cols_str})", ()

    def format_table_unique_constraint(
        self, constraint: "TableUniqueConstraint"
    ) -> Tuple[str, tuple]:
        """Format the body of a ``UNIQUE`` table constraint.

        Args:
            t_const: The constraint whose ``columns`` are rendered.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is always empty.

        Raises:
            ValueError: If no columns are specified.
        """
        if not constraint.columns:
            raise ValueError("UNIQUE constraint must have at least one column specified.")
        cols_str = ", ".join(self.format_identifier(col) for col in constraint.columns)
        return f"UNIQUE ({cols_str})", ()

    def format_table_check_constraint(
        self, constraint: "TableCheckConstraint"
    ) -> Tuple[str, Tuple]:
        """Format a table-level ``CHECK`` constraint body.

        Args:
            t_const: The constraint whose ``check_condition`` is rendered.

        Returns:
            A ``(sql, params)`` tuple.

        Raises:
            ValueError: If ``check_condition`` is ``None``.
        """
        if constraint.condition is None:
            raise ValueError("CHECK constraint must have a check condition specified.")
        check_sql = self._format_ddl_condition(constraint.condition)
        return f"CHECK ({check_sql})", ()

    def format_table_foreign_key_constraint(
        self, constraint: "TableForeignKeyConstraint"
    ) -> Tuple[str, Tuple]:
        """Format a table-level ``FOREIGN KEY`` branch.

        Args:
            constraint: The branch carrying the local columns, the referenced
                table and columns, and the referential actions.

        Returns:
            A ``(sql, params)`` tuple; ``sql`` has no leading space.

        Raises:
            ValueError: The local columns, the referenced columns or the
                referenced table are missing.
        """
        if not constraint.columns:
            raise ValueError("FOREIGN KEY constraint must have at least one local column specified.")
        referenced_table, referenced_columns = constraint.references
        if not referenced_columns:
            raise ValueError("FOREIGN KEY constraint must have at least one foreign key column specified.")
        if not referenced_table:
            raise ValueError("FOREIGN KEY constraint must have a foreign key table specified.")
        from ...expression.statements.ddl_table import ReferencesClause

        cols_str = ", ".join(self.format_identifier(col) for col in constraint.columns)

        references = ReferencesClause(
            self,
            referenced_table,
            list(referenced_columns),
            on_delete=constraint.on_delete,
            on_update=constraint.on_update,
            match_type=constraint.match_type,
        )
        ref_sql, ref_params = self.format_references_clause(references)
        return f"FOREIGN KEY ({cols_str}) {ref_sql}", tuple(ref_params)

    def format_table_exclude_constraint(
        self, constraint: "TableExcludeConstraint"
    ) -> Tuple[str, Tuple]:
        """Format a table-level ``EXCLUDE`` branch.

        Core has no EXCLUDE grammar to fall back on, so the default refuses
        by name rather than rendering SQL a server would reject. The branch
        exists because the constraint is enumerable (规范 4.9's table
        constraint kinds), and a dialect whose server can spell it overrides
        this formatter.

        Args:
            constraint: The branch carrying the columns, the operator and the
                optional index method.

        Returns:
            A ``(sql, params)`` tuple.

        Raises:
            UnsupportedFeatureError: Always, unless a dialect overrides this.
        """
        from ..exceptions import UnsupportedFeatureError

        if not self.supports_exclude_constraint():
            raise UnsupportedFeatureError(self.name, "EXCLUDE constraint")
        raise UnsupportedFeatureError(self.name, "EXCLUDE constraint formatter")

    def format_table_constraint(self, expr: "TableConstraint") -> Tuple[str, Tuple]:
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
        enforcement = self._format_constraint_enforcement(expr)
        if enforcement:
            parts.append(enforcement)
        return " ".join(parts), tuple(branch_params)

    def format_storage_options(self, expr: "StorageOptionsExpression") -> Tuple[str, tuple]:
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

    def format_add_column_action(self, action: "AddColumnAction") -> Tuple[str, Tuple]:
        """Format an ``ADD COLUMN`` ALTER TABLE action.

        Args:
            action: The action carrying the column definition to add.

        Returns:
            A ``(sql, params)`` tuple.

        Raises:
            UnsupportedFeatureError: If IF NOT EXISTS is requested but not
                supported by the dialect.
        """
        from ..exceptions import UnsupportedFeatureError
        column_sql, column_params = self.format_column_definition(action.column)
        if action.if_not_exists:
            if not self.supports_add_column_if_not_exists():
                raise UnsupportedFeatureError(
                    self.name, "ADD COLUMN IF NOT EXISTS",
                    f"{self.name} does not support ADD COLUMN IF NOT EXISTS."
                )
            return f"ADD COLUMN IF NOT EXISTS {column_sql}", column_params
        return f"ADD COLUMN {column_sql}", column_params

    def format_drop_column_action(self, action: "DropColumnAction") -> Tuple[str, Tuple]:
        """Format a ``DROP COLUMN`` ALTER TABLE action.

        Emits ``DROP COLUMN IF EXISTS`` when the action requests it.

        Args:
            action: The action carrying the column name to drop.

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
        if action.if_exists:
            if not self.supports_drop_column_if_exists():
                raise UnsupportedFeatureError(
                    self.name, "DROP COLUMN IF EXISTS",
                    f"{self.name} does not support DROP COLUMN IF EXISTS."
                )
            return f"DROP COLUMN IF EXISTS {self.format_identifier(action.column_name)}", ()
        return f"DROP COLUMN {self.format_identifier(action.column_name)}", ()

    def format_alter_column_action(self, action: "AlterColumnAction") -> Tuple[str, Tuple]:
        """Format an ``ALTER COLUMN`` ALTER TABLE action.

        Handles ``SET DATA TYPE`` (validated type text), string values
        (escaped and inlined), expression values rendered through
        ``to_sql``, and plain values inlined via ``inline_sql_literal``.

        Args:
            action: The action carrying the column name, operation, and
                optional new value.

        Returns:
            A ``(sql, params)`` tuple.

        Raises:
            UnsupportedFeatureError: If the dialect does not support the
                requested alteration (data-type changes and column-property
                changes are gated by separate capability switches).
            ValueError: If a ``SET DATA TYPE`` value is not a valid data type
                specification.
        """
        from ..exceptions import UnsupportedFeatureError
        all_params: List[Any] = []
        from enum import Enum

        # ``operation`` accepts the enum or its raw spelling; which one it
        # is is a type question, so it is asked with isinstance rather than
        # probed for a ``value`` attribute.
        operation_str = (
            action.operation.value if isinstance(action.operation, Enum) else str(action.operation)
        )
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
        column_part = f"ALTER COLUMN {self.format_identifier(action.column_name)} {operation_str}"
        if action.new_value is not None:
            if operation_str == "SET DATA TYPE":
                from ...dialect.base import SQLDialectBase
                if not SQLDialectBase._validate_data_type(str(action.new_value)):
                    raise ValueError(f"Invalid data type specification: '{action.new_value}'")
                column_part += f" {action.new_value}"
            elif isinstance(action.new_value, str):
                # DDL accepts no bind parameters, so the value is written into
                # the SQL text. The literal is the controlled path: it escapes
                # and quotes exactly as DEFAULT does.
                value_sql, value_params = Literal(
                    self, action.new_value, inline=True
                ).to_sql()
                column_part += f" {value_sql}"
            elif isinstance(action.new_value, ToSQLProtocol):
                if isinstance(action.new_value, Literal):
                    # The value carries its own DDL decision; the controlled
                    # path escapes and quotes it exactly as DEFAULT does.
                    value_sql, value_params = Literal(
                        self, action.new_value.value, inline=True
                    ).to_sql()
                else:
                    value_sql, value_params = action.new_value.to_sql()
                    if value_params:
                        raise ValueError(
                            "ALTER COLUMN value must render without bind parameters"
                        )
                column_part += f" {value_sql}"
            else:
                column_part += f" {self.inline_sql_literal(action.new_value)}"
        if action.cascade:
            column_part += " CASCADE"
        return column_part, tuple(all_params)

    def format_add_table_constraint_action(self, action: "AddTableConstraintAction") -> Tuple[str, Tuple]:
        """Format an ``ADD CONSTRAINT`` ALTER TABLE action.

        Args:
            action: The action carrying the table constraint to add.

        Returns:
            A ``(sql, params)`` tuple prefixed with ``ADD``.

        Raises:
            UnsupportedFeatureError: If the dialect does not support
                ``ALTER TABLE ADD CONSTRAINT``.
        """
        from ..exceptions import UnsupportedFeatureError
        if not self.supports_add_constraint():
            raise UnsupportedFeatureError(self.name, "ALTER TABLE ADD CONSTRAINT")
        constraint_sql, params = self.format_table_constraint(action.constraint)
        if not constraint_sql:
            return "ADD UNKNOWN CONSTRAINT", ()
        validation_sql = self._format_constraint_validation(action.constraint)
        return f"ADD {constraint_sql}{validation_sql}", tuple(params)

    def format_alter_constraint_action(self, action: "AlterConstraintAction") -> Tuple[str, Tuple]:
        """Format an ``ALTER CONSTRAINT`` enforcement action.

        The kind restriction — CHECK and FOREIGN KEY only — is this
        operation's own narrowing of the ENFORCABLE kinds and lives in the
        formatter, not in the capability probe.

        Raises:
            TypeError: ``constraint_branch`` is not a CHECK or FOREIGN KEY branch.
            ValueError: The kind cannot carry the ALTER CONSTRAINT trait.
            UnsupportedFeatureError: The dialect has no ALTER CONSTRAINT
                enforcement control.
        """

        branch = action.constraint_branch
        if branch not in (TableCheckConstraint, TableForeignKeyConstraint):
            raise TypeError(
                "constraint_branch must be TableCheckConstraint or "
                f"TableForeignKeyConstraint, got {type(branch).__name__}"
            )
        if branch not in (TableCheckConstraint, TableForeignKeyConstraint):
            raise ValueError(
                "ALTER CONSTRAINT enforcement is only valid for CHECK and FOREIGN KEY constraints"
            )
        if not self.supports_alter_constraint_enforced():
            from ..exceptions import UnsupportedFeatureError

            raise UnsupportedFeatureError(
                self.name,
                "ALTER CONSTRAINT ENFORCED/NOT ENFORCED",
            )
        if not isinstance(action.enforced, bool):
            raise TypeError("enforced must be a bool")
        keyword = "ENFORCED" if action.enforced else "NOT ENFORCED"
        return (
            f"ALTER CONSTRAINT {self.format_identifier(action.constraint_name)} {keyword}",
            (),
        )

    def format_validate_constraint_action(self, action: "ValidateConstraintAction") -> Tuple[str, Tuple]:
        if not self.supports_validate_constraint():
            from ..exceptions import UnsupportedFeatureError

            raise UnsupportedFeatureError(self.name, "VALIDATE CONSTRAINT")
        return f"VALIDATE CONSTRAINT {self.format_identifier(action.constraint_name)}", ()

    def format_drop_table_constraint_action(self, action: "DropTableConstraintAction") -> Tuple[str, Tuple]:
        """Format a ``DROP CONSTRAINT`` ALTER TABLE action.

        Args:
            action: The action carrying the constraint name and optional
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
        if action.if_exists and not self.supports_drop_constraint_if_exists():
            raise UnsupportedFeatureError(
                self.name, "DROP CONSTRAINT IF EXISTS",
                f"{self.name} does not support DROP CONSTRAINT IF EXISTS."
            )
        if_exists = "IF EXISTS " if action.if_exists else ""
        result = f"DROP CONSTRAINT {if_exists}{self.format_identifier(action.constraint_name)}"
        if action.cascade:
            result += " CASCADE"
        return result, ()

    def format_index_definition(self, expr: "IndexDefinition") -> Tuple[str, Tuple]:
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

    def format_add_index_action(self, action: "AddIndexAction") -> Tuple[str, Tuple]:
        """Format an ``ADD INDEX`` ALTER TABLE action.

        Args:
            action: The action carrying the index definition to add.

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
            self.format_identifier(col) for col in action.index.columns
        )
        return (
            f"ADD INDEX {self.format_identifier(action.index.name)} ({columns})",
            (),
        )

    def format_drop_index_action(self, action: "DropIndexAction") -> Tuple[str, Tuple]:
        """Format a ``DROP INDEX`` ALTER TABLE action.

        Emits ``DROP INDEX IF EXISTS`` when the action requests it.

        Args:
            action: The action carrying the index to drop.

        Returns:
            A ``(sql, params)`` tuple with empty parameters.

        Raises:
            TypeError: ``DropIndexAction.index`` is not an Index. Another object kind
            would have had its own name rendered as the index's.
            UnsupportedFeatureError: If the dialect does not support
                ``ALTER TABLE DROP INDEX``.
        """
        if not isinstance(action.index, Index):
            raise TypeError(
                f"DropIndexAction.index must be an Index, "
                f"got {type(action.index).__name__}"
            )
        from ..exceptions import UnsupportedFeatureError
        if not self.supports_alter_table_index_actions():
            raise UnsupportedFeatureError(
                self.name, "ALTER TABLE DROP INDEX",
                f"{self.name} does not support ALTER TABLE DROP INDEX.",
            )
        index_sql, index_params = action.index.to_sql()
        head = "DROP INDEX IF EXISTS" if action.if_exists else "DROP INDEX"
        return f"{head} {index_sql}", index_params

    def format_rename_column_action(self, action: "RenameColumnAction") -> Tuple[str, Tuple]:
        """Format a ``RENAME COLUMN`` ALTER TABLE action.

        Args:
            action: The action carrying the old and new column names.

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
            f"RENAME COLUMN {self.format_identifier(action.old_name)} TO {self.format_identifier(action.new_name)}",
            (),
        )

    def format_rename_table_action(self, action: "RenameTableAction") -> Tuple[str, Tuple]:
        """Format a ``RENAME TO`` ALTER TABLE action.

        Args:
            action: The action carrying the new table name.

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
        return f"RENAME TO {self.format_identifier(action.new_name)}", ()

    def format_modify_column_action(self, action: "ModifyColumnAction") -> Tuple[str, Tuple]:
        """Format a ``MODIFY COLUMN`` ALTER TABLE action.

        The core implementation always raises, since ``MODIFY COLUMN`` is
        MySQL/MariaDB-specific; those backends override this method.

        Args:
            action: The action carrying the column definition to apply.

        Raises:
            UnsupportedFeatureError: Always, at the core layer.
        """
        from ..exceptions import UnsupportedFeatureError
        raise UnsupportedFeatureError(self.name, "MODIFY COLUMN")

    def format_change_column_action(self, action: "ChangeColumnAction") -> Tuple[str, Tuple]:
        """Format a ``CHANGE COLUMN`` ALTER TABLE action.

        The core implementation always raises, since ``CHANGE COLUMN`` is
        MySQL/MariaDB-specific; those backends override this method.

        Args:
            action: The action carrying the old name and new column definition.

        Raises:
            UnsupportedFeatureError: Always, at the core layer.
        """
        from ..exceptions import UnsupportedFeatureError
        raise UnsupportedFeatureError(self.name, "CHANGE COLUMN")
