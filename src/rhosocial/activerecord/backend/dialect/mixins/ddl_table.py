# .../ddl_table.py
"""Composition base for TableMixin. Feature groups live in per-statement mixins."""

from rhosocial.activerecord.backend.expression.statements import (
    TableCheckConstraint,
    TableConstraint,
    TableForeignKeyConstraint,
)
from ...expression.statements.ddl_alter import AlterTableAction, DropTableConstraintAction
from ...expression.objects import Table
from typing import Any, List, Tuple, TYPE_CHECKING
from enum import Enum
from .create_table_mixin import CreateTableMixin
from .drop_table_mixin import DropTableMixin
from .alter_table_mixin import AlterTableMixin
from .create_table_as_mixin import CreateTableAsMixin
from .create_table_like_mixin import CreateTableLikeMixin
from .create_table_clone_mixin import CreateTableCloneMixin
from .create_table_using_template_mixin import CreateTableUsingTemplateMixin

class TableMixin(CreateTableMixin, DropTableMixin, AlterTableMixin, CreateTableAsMixin, CreateTableLikeMixin, CreateTableCloneMixin, CreateTableUsingTemplateMixin):
    """Composition of per-statement table mixins. No own members (not a feature group)."""

    pass


    def _ddl_bind_parameter_reason(self, feature: str) -> str:
        """Why this dialect does not carry bind parameters in a CTAS body.

        A backend that refuses them for a *measured* reason overrides this
        and quotes the engine's own answer, so the refusal says why rather
        than only that. This default names the fact and leaves it there.
        """
        return f"{self.name} does not carry bind parameters in a CTAS body."

class ConstraintMixin:
    """Mixin for DDL constraint capability detection.

    Default values are True for all methods, enabling DummyDialect
    to validate the full constraint implementation. Actual backends
    override methods as needed to reflect their real capabilities.
    """

    # Basic constraint types (SQL-86/SQL-92)

    def supports_constraint_novalidate(self) -> bool:
        return False

    def supports_exclude_constraint(self) -> bool:
        """Whether EXCLUDE table constraints are supported."""
        return False

    def supports_drop_column(self) -> bool:
        """Whether ``ALTER TABLE ... DROP COLUMN`` is supported.

        DROP COLUMN is a baseline ALTER capability across SQL dialects, and the
        generic ``format_drop_column_action`` renders a portable spelling. A
        backend that genuinely cannot drop a column overrides this to False
        (e.g. Oracle in this codebase). Defaulting to False here silently
        suppressed a valid capability on backends that never needed to override
        it (SQL Server, BigQuery, Snowflake).
        """
        return True

    def supports_foreign_key_on_delete(self) -> bool:
        """Whether FOREIGN KEY ON DELETE is supported (defaults to True)."""
        return True

    def supports_foreign_key_on_update(self) -> bool:
        """Whether FOREIGN KEY ON UPDATE is supported (defaults to True)."""
        return True

    def supports_column_character_set(self) -> bool:
        """Whether a column-level ``CHARACTER SET <name>`` attribute is
        supported.

        Defaults to False — character sets are a MySQL/MariaDB concept, not
        part of the generic dialect; those backends override this to return
        True.
        """
        return False

    def supports_column_collation(self) -> bool:
        """Whether a column-level ``COLLATE <name>`` attribute is supported.

        Defaults to True — the SQL-standard form is valid on every backend
        that renders column definitions; backends whose column COLLATE is
        meaningless override this to return False.
        """
        return True

    def supports_column_comment(self) -> bool:
        """Whether COLUMN COMMENT is supported (defaults to False)."""
        return False

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

    def supports_constraint_naming(self) -> bool:
        """Whether a constraint may carry a ``CONSTRAINT <name>`` prefix.

        The SQL-92 grammar opens both constraint productions with
        ``[CONSTRAINT <constraint name>]``, so this defaults to ``True`` —
        a constructor is something every grammar has. A dialect overrides
        it only to refuse the prefix.
        """
        return True

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

    def format_foreign_key_constraint(self, expr: 'TableConstraint') -> Tuple[str, tuple]:
        raise NotImplementedError("format_foreign_key_constraint")

    def format_column_fk_constraint(
        self, expr: "ColumnForeignKeyConstraint"
    ) -> Tuple[str, Tuple]:
        """Format a column-level ``REFERENCES`` branch.

        Delegates the reference body to :meth:`format_references_clause`. The
        deferral traits are the production's to render (see
        :meth:`format_constraint_traits`), so they are not passed down here.

        Args:
            expr: The branch whose ``references`` are rendered.

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
            raise UnsupportedFeatureError(self.name, "REFERENCES column expr")

        referenced_table, referenced_columns = expr.references

        references = ReferencesClause(
            self,
            referenced_table,
            referenced_columns,
            on_delete=expr.on_delete,
            on_update=expr.on_update,
            match_type=expr.match_type,
        )
        ref_sql, ref_params = self.format_references_clause(references)
        return f" {ref_sql}", tuple(ref_params)

    def supports_fk_match(self) -> bool:
        """Whether MATCH {SIMPLE|PARTIAL|FULL} is supported.

        Defaults to True.
        """
        return True

    def supports_deferrable_constraint(self) -> bool:
        """Whether DEFERRABLE / INITIALLY DEFERRED/IMMEDIATE is supported.

        A SQL:1999 *modifier*, not a constructor, so it defaults to
        ``False`` and the dialects that have it opt in explicitly
        (PostgreSQL, Oracle, SQLite — measured, foreign keys only on
        SQLite).
        """
        return False

    def supports_constraint_enforced(self) -> bool:
        """Whether ENFORCED / NOT ENFORCED constraint control is supported.

        A SQL:2016 *modifier*, not a constructor, so it defaults to
        ``False`` and the dialects that have it opt in explicitly
        (MySQL >= 8.0.16, PostgreSQL >= 18, BigQuery — each narrowing the
        kinds it accepts inside its own table-constraint formatter).
        """
        return False

    def supports_alter_constraint_enforced(self) -> bool:
        """Whether ALTER CONSTRAINT enforcement control is supported."""
        return False

    def supports_validate_constraint(self) -> bool:
        """Whether VALIDATE CONSTRAINT is supported."""
        return False

    def format_alter_constraint_action(self, expr: "AlterConstraintAction") -> Tuple[str, Tuple]:
        """Format an ``ALTER CONSTRAINT`` enforcement expr.

        The kind restriction — CHECK and FOREIGN KEY only — is this
        operation's own narrowing of the ENFORCABLE kinds and lives in the
        formatter, not in the capability probe.

        Raises:
            TypeError: ``constraint_branch`` is not a CHECK or FOREIGN KEY branch.
            ValueError: The kind cannot carry the ALTER CONSTRAINT trait.
            UnsupportedFeatureError: The dialect has no ALTER CONSTRAINT
                enforcement control.
        """

        branch = expr.constraint_branch
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
        if not isinstance(expr.enforced, bool):
            raise TypeError("enforced must be a bool")
        keyword = "ENFORCED" if expr.enforced else "NOT ENFORCED"
        return (
            f"ALTER CONSTRAINT {self.format_identifier(expr.constraint_name)} {keyword}",
            (),
        )

    def format_validate_constraint_action(self, expr: "ValidateConstraintAction") -> Tuple[str, Tuple]:
        if not self.supports_validate_constraint():
            from ..exceptions import UnsupportedFeatureError

            raise UnsupportedFeatureError(self.name, "VALIDATE CONSTRAINT")
        return f"VALIDATE CONSTRAINT {self.format_identifier(expr.constraint_name)}", ()

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

    def _resolve_drop_constraint_address(self, expr: "DropTableConstraintAction") -> str:
        """Decide which address a ``DROP CONSTRAINT`` names the constraint by.

        A constraint may be addressed by name (``constraint_name``) or by its
        declaration (``constraint``).  Exactly one decision is made here, in
        this order, so a formatter never invents its own preference:

        1. No declaration: the name is required (``ValueError`` otherwise) and
           the answer is ``"name"``.
        2. A declaration and no name: the answer is ``"kind"`` when the dialect
           advertises :meth:`supports_drop_constraint_by_kind`; otherwise
           ``UnsupportedFeatureError`` naming ``DROP CONSTRAINT by kind``.
        3. Both: the declaration merely **confirms** the name.  If the
           declaration carries that same name the answer is ``"name"`` -- the
           declaration adds no second address.  If the names differ, or the
           declaration is unnamed, the two addresses disagree and an
           **ambiguous address** is refused with ``UnsupportedFeatureError``
           naming ``DROP CONSTRAINT address``.  Never silently pick one.

        Args:
            expr: The action whose addresses are resolved.

        Returns:
            ``"name"`` when the drop is addressed by ``constraint_name``,
            ``"kind"`` when it is addressed by the declaration's kind.

        Raises:
            TypeError: ``expr.constraint`` is present but not a
                :class:`TableConstraint`.
            ValueError: Neither address is present.
            UnsupportedFeatureError: A declaration-only drop on a dialect that
                cannot spell drops by kind, or an ambiguous address.
        """
        from ..exceptions import UnsupportedFeatureError

        constraint = expr.constraint
        if constraint is not None and not isinstance(constraint, TableConstraint):
            raise TypeError(
                "DropTableConstraintAction.constraint must be a TableConstraint, "
                f"got {type(constraint).__name__}"
            )
        if constraint is None:
            if expr.constraint_name is None:
                raise ValueError(
                    "DropTableConstraintAction requires constraint_name or constraint"
                )
            return "name"
        if expr.constraint_name is None:
            if self.supports_drop_constraint_by_kind():
                return "kind"
            raise UnsupportedFeatureError(
                self.name, "DROP CONSTRAINT by kind",
                f"{self.name} does not support DROP CONSTRAINT by kind; "
                f"address the constraint by name instead."
            )
        if constraint.name is not None and constraint.name == expr.constraint_name:
            # The declaration confirms the name; it adds no second address.
            return "name"
        raise UnsupportedFeatureError(
            self.name, "DROP CONSTRAINT address",
            f"{self.name} received two addresses for one constraint: "
            f"constraint_name {expr.constraint_name!r} and declaration name "
            f"{constraint.name!r}. An ambiguous address is refused; make the "
            f"declaration's name match constraint_name, or pass only one address."
        )

    def supports_drop_constraint_by_kind(self) -> bool:
        """Whether a constraint may be dropped by its declaration's kind.

        ``True`` means the dialect renders ``DROP PRIMARY KEY`` /
        ``DROP UNIQUE (<cols>)`` / ``DROP FOREIGN KEY (<cols>)`` rather than
        ``DROP CONSTRAINT <name>``.  Defaults to ``False`` so no existing
        backend changes behaviour.

        When an action carries both a name and a declaration, the declaration
        only **confirms** the name if it carries that same name; the drop is
        then spelled by name.  An unequal or unnamed declaration is an
        **ambiguous address** and is refused, never resolved by preference
        (see :meth:`_resolve_drop_constraint_address`).
        """
        return False

def _normalize_constraint_type(constraint_type: Any, constraint_enum: type, label: str) -> Any:
    if isinstance(constraint_type, constraint_enum):
        return constraint_type
    # Accepts the enum or its spelling, and a spelling may arrive as an enum of
    # another family that spells the same words -- which is a type question, so
    # it is asked with isinstance instead of probed for ``value`` / ``name``.
    if isinstance(constraint_type, Enum):
        raw_value, raw_name = constraint_type.value, constraint_type.name
    else:
        raw_value = raw_name = constraint_type
    candidates = []
    for candidate in (raw_value, raw_name):
        if isinstance(candidate, str):
            normalized = " ".join(candidate.strip().split()).upper()
            candidates.extend((normalized, normalized.replace(" ", "_")))
    for candidate in candidates:
        try:
            return constraint_enum(candidate)
        except ValueError:
            continue
    raise ValueError(
        f"{label} must be a {constraint_enum.__name__} or its string value"
    )

def normalize_foreign_key_match_type(match_type: Any) -> Any:
    """Return the :class:`ForeignKeyMatchType` for ``match_type``.

    ``None`` passes through: a constraint that names no MATCH type is asking for
    the SQL default, which is not the same as asking for ``SIMPLE`` explicitly
    (a dialect may spell the default and the explicit form differently, or
    refuse one of them).
    """
    from ...expression.statements.ddl_table import ForeignKeyMatchType

    if match_type is None:
        return None
    return _normalize_constraint_type(
        match_type,
        ForeignKeyMatchType,
        "foreign key MATCH type",
    )
