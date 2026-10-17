from .dql import QueryStatement
from .ddl_partition import PartitionClause
from ..types import DataType
from ..objects import Table
from ..bases import (
    BaseExpression,
    SQLPredicate,
    SQLQueryAndParams,
    require_exclusive_options,
)
from typing import Any, Dict, List, Optional, Tuple, Union, TYPE_CHECKING
from abc import ABC
from enum import Enum
# src/rhosocial/activerecord/backend/expression/statements/ddl_table.py
"""Table DDL statement expressions and related types."""




if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


class DefaultValueClause(BaseExpression):
    """The value clause of a ``DEFAULT`` constraint.

    A DDL clause node rendered through the dialect's
    ``format_default_value_clause``. It carries the default **value** — either
    a plain Python scalar (rendered inline with dialect-controlled escaping) or
    a ``BaseExpression`` (e.g. a function call or literal) — keeping the
    value/inline logic in one place. It is a self-contained expression so the
    value's escaping/inlining can be overridden per backend.

    A ``DEFAULT`` position accepts no bind parameters, so the class declares
    ``inline_params = True``: the clause renders inline only and never
    produces a bind value.
from rhosocial.activerecord.backend.expression.statements import (
    ColumnCheckConstraint,
    ColumnConstraintBranch,
    ColumnDefaultConstraint,
    ColumnForeignKeyConstraint,
    ColumnGeneratedConstraint,
    ColumnNotNullConstraint,
    ColumnNullableConstraint,
    ColumnPrimaryKeyConstraint,
    ColumnUniqueConstraint,
    TableCheckConstraint,
    TableConstraintBranch,
    TableExcludeConstraint,
    TableForeignKeyConstraint,
    TablePrimaryKeyConstraint,
    TableUniqueConstraint,
)
    """

    inline_params: bool = True

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_default_value_clause"

    def __init__(self, dialect: "SQLDialectBase", value: Any):
        super().__init__(dialect)
        self.value = value


class ColumnClause(BaseExpression):
    """Base for a clause that rides inside a column definition.

    A column definition is a type followed by a sequence of clauses, and these
    are the ones that are neither a constraint nor the type itself: collation,
    character set, identity, auto-increment, the inline comment, a generated
    column. They share one property -- each is a self-contained node with its
    own grammar, so each owns its ``format_method`` and a dialect decides
    whether it can spell it.

    Naming: this is a **DDL column clause**. It is unrelated to the
    ``ColumnBase`` family in ``expression.column_types``, which are
    value-typed column *expressions* (``StringColumn`` and its siblings) and
    live on the query side.

    Subclassing this is what lets ``ColumnDefinition.attributes`` carry a
    typed sequence instead of ``List[Any]``.

    ``format_method`` is deliberately **not** overridden here: the base
    ``BaseExpression`` getter already raises ``NotImplementedError`` for a class
    that names no formatter, which is exactly what this base is. A subclass
    declares its own.
    """


class CollationClause(ColumnClause):
    """The ``COLLATE <name>`` clause of a column definition.

    A DDL clause node rendered through the dialect's ``format_collation_clause``.
    ``COLLATE`` is part of the SQL-standard column-constraint grammar, so the
    capability defaults to True and a dialect overrides
    :meth:`supports_column_collation` only for a version boundary.

    The name is **not** validated here. Which collation names exist is a
    catalogue question a dialect answers in its own validator (Snowflake and
    BigQuery both require a quoted specification rather than a bare
    identifier), so the node carries the name the caller asked for and the
    dialect decides how to spell and whether to accept it.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_collation_clause"

    def __init__(self, dialect: "SQLDialectBase", name: str):
        super().__init__(dialect)
        if not isinstance(name, str) or not name.strip():
            raise ValueError("COLLATE requires a collation name")
        self.name = name


class CharacterSetClause(ColumnClause):
    """The ``CHARACTER SET <name>`` clause of a column definition.

    A DDL clause node rendered through the dialect's
    ``format_character_set_clause``. This is a MySQL/MariaDB family construct,
    so :meth:`supports_column_character_set` defaults to False and those
    backends (plus Firebird) opt in.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_character_set_clause"

    def __init__(self, dialect: "SQLDialectBase", name: str):
        super().__init__(dialect)
        if not isinstance(name, str) or not name.strip():
            raise ValueError("CHARACTER SET requires a character set name")
        self.name = name


class IdentityClause(BaseExpression):
    """The SQL-standard identity clause of a column definition.

    A DDL clause node rendered through the dialect's ``format_identity_clause``.
    It carries the identity **parameters** (generation, start, increment,
    bounds, cycle) for the SQL-standard
    ``GENERATED {ALWAYS|BY DEFAULT} AS IDENTITY (START WITH ... INCREMENT BY ...)``
    grammar. SQL Server and Snowflake override the formatter to render their
    own ``IDENTITY(seed, inc)`` spelling.

    ``AUTO_INCREMENT`` is **not** this node: it has no parameter space (its
    seed is a table-level option), so it is a different mechanism carried by
    :class:`AutoIncrementClause`. ``SERIAL`` is a *type*, not a column clause,
    and stays in the PostgreSQL type family.

    ``generation`` is ``"ALWAYS"`` or ``"BY DEFAULT"`` (``None`` defaults to
    ``BY DEFAULT``); ``start``/``increment``/``minvalue``/``maxvalue`` are
    optional sequence attributes. Every option is gated by its own probe in the
    formatter; an option the dialect cannot express is refused by name, not
    dropped.

    Each two-spelling option has one parameter per spelling: ``cycle`` /
    ``no_cycle``, ``order`` / ``no_order``, ``cache`` / ``no_cache``. Setting
    both of a pair raises ``ValueError``; ``cache`` is a positive count and
    ``no_cache=True`` spells NO CACHE (``cache=0`` is not a spelling).
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_identity_clause"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        generation: Optional[str] = None,
        *,
        start: Optional[int] = None,
        increment: Optional[int] = None,
        minvalue: Optional[int] = None,
        maxvalue: Optional[int] = None,
        cycle: bool = False,
        no_cycle: bool = False,
        order: bool = False,
        no_order: bool = False,
        cache: Optional[int] = None,
        no_cache: bool = False,
    ):
        super().__init__(dialect)
        require_exclusive_options(cycle, no_cycle, "cycle", "no_cycle")
        if cache is not None and no_cache:
            raise ValueError("cache and no_cache are mutually exclusive options")
        if order and no_order:
            raise ValueError("order and no_order are mutually exclusive options")
        if cache is not None and cache <= 0:
            raise ValueError(
                "cache must be a positive integer; use no_cache=True to spell NO CACHE"
            )
        self.generation = generation
        self.start = start
        self.increment = increment
        self.minvalue = minvalue
        self.maxvalue = maxvalue
        self.cycle = cycle
        self.no_cycle = no_cycle
        self.order = order
        self.no_order = no_order
        self.cache = cache
        self.no_cache = no_cache


class AutoIncrementClause(BaseExpression):
    """The bare ``AUTO_INCREMENT`` marker of a column definition.

    A DDL clause node rendered through the dialect's
    ``format_auto_increment_clause``. It carries **no parameters**, and that is
    the point: ``AUTO_INCREMENT`` has no column-level parameter space. Its seed
    and increment are table-level options (``AUTO_INCREMENT = 100``), a
    different mechanism that is out of scope for this node. A parameterised
    identity column is expressed with :class:`IdentityClause` instead.

    The node names the generic mechanism — "this column's value is generated
    by the server, with no parameters" — and the dialect decides the spelling:
    core renders `` AUTO_INCREMENT``; a dialect that cannot express the
    mechanism refuses through its ``supports_auto_increment_column()`` probe.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_auto_increment_clause"

    def __init__(self, dialect: "SQLDialectBase"):
        super().__init__(dialect)


class ReferencesClause(BaseExpression):
    """The ``REFERENCES`` clause of a foreign key.

    A DDL clause node rendered through the dialect's ``format_references_clause``.
    Shared by column-level (``ColumnConstraint``) and table-level
    (``ForeignKeyConstraint``) foreign keys so the reference syntax lives in one
    place: the referenced table/columns plus the referential actions
    (``MATCH`` / ``ON DELETE`` / ``ON UPDATE``) and deferrability.

    ``ReferentialAction`` values are resolved by the dialect's
    ``format_references_clause``; ``on_delete``/``on_update`` are accepted as
    the enum or its string value.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_references_clause"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        referenced_table: "Table",
        referenced_columns: List[str],
        *,
        on_delete: Optional["ReferentialAction"] = None,
        on_update: Optional["ReferentialAction"] = None,
        match_type: Optional["ForeignKeyMatchType"] = None,
        deferrable: bool = False,
        not_deferrable: bool = False,
        initially_deferred: bool = False,
        initially_immediate: bool = False,
    ):
        super().__init__(dialect)
        require_exclusive_options(deferrable, not_deferrable, "deferrable", "not_deferrable")
        require_exclusive_options(
            initially_deferred,
            initially_immediate,
            "initially_deferred",
            "initially_immediate",
        )
        self.referenced_table = referenced_table
        self.referenced_columns = list(referenced_columns or [])
        self.on_delete = on_delete
        self.on_update = on_update
        self.match_type = match_type
        self.deferrable = deferrable
        self.not_deferrable = not_deferrable
        self.initially_deferred = initially_deferred
        self.initially_immediate = initially_immediate


class ColumnCommentClause(BaseExpression):
    """The inline comment clause of a column definition.

    A CREATE TABLE / ALTER TABLE **clause** node rendered through the
    dialect's ``format_column_comment_clause``.  It is deliberately distinct
    from the standalone ``COMMENT ON`` statement (:class:`CommentOnStatement`):
    the inline clause is part of the *column-definition grammar* and only
    exists on dialects that advertise :meth:`supports_column_comment`.

    Dialects render it differently — MySQL/MariaDB/SQLite-family emit
    ``COMMENT '<text>'``, BigQuery emits ``OPTIONS(description='<text>')``;
    PostgreSQL/Oracle/Firebird/SQL Server have no inline column-comment
    grammar and raise ``UnsupportedFeatureError`` instead of silently
    dropping the declared comment.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_column_comment_clause"

    def __init__(self, dialect: "SQLDialectBase", comment: str):
        super().__init__(dialect)
        self.comment = comment


class TableCommentClause(BaseExpression):
    """The inline table-comment clause of ``CREATE TABLE``.

    A CREATE TABLE **clause** node rendered through the dialect's
    ``format_table_comment_clause``.  There is no SQL-standard table-comment
    mechanism: the bare ``COMMENT '<text>'`` table option is a
    MySQL/MariaDB/ClickHouse-family convenience (Snowflake renders
    ``COMMENT = '<text>'``, BigQuery ``OPTIONS(description='<text>')``), while
    the standalone ``COMMENT ON`` statement is a separate de-facto vendor
    mechanism (:class:`CommentOnStatement`), not this clause.

    Rendering is capability-gated: the statement renderer emits this clause
    only on dialects whose :meth:`supports_table_comment` is True, and raises
    ``UnsupportedFeatureError`` on the others instead of silently dropping a
    declared comment.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_table_comment_clause"

    def __init__(self, dialect: "SQLDialectBase", comment: str):
        super().__init__(dialect)
        self.comment = comment


class ColumnDefinition(BaseExpression):
    """Represents a column definition clause within CREATE/ALTER TABLE.

    A DDL clause node rendered through the dialect's
    ``format_column_definition``; its children (data type, constraints,
    generated-column expression, inline comment clause) are proper expression
    nodes, so dialect propagation reaches the whole clause subtree.

    ``comment`` is a :class:`ColumnCommentClause` (or ``None``); bare comment
    text is **not** accepted here — build the clause node explicitly so the
    inline comment always flows through the clause channel.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_column_definition"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: str,
        data_type: "DataType",
        constraints: Optional[List["ColumnConstraint"]] = None,
        comment: Optional["ColumnCommentClause"] = None,
        generated_expression: Optional["ColumnGeneratedConstraint"] = None,
        attributes: Optional[List["ColumnClause"]] = None,
    ):
        super().__init__(dialect)
        if not isinstance(data_type, DataType):
            raise TypeError(
                f"data_type must be a DataType instance, got {type(data_type).__name__}"
            )
        if comment is not None and not isinstance(comment, ColumnCommentClause):
            raise TypeError(
                f"comment must be a ColumnCommentClause, got {type(comment).__name__}"
            )
        self.name = name
        self.data_type = data_type
        self.constraints = list(constraints or [])
        self.comment = comment
        self.generated_expression = generated_expression
        # Column clauses, in the order they should be spelled. An AR-layer
        # ``ColumnAttribute`` is still tolerated here because no deriver
        # translates a model's declarations into clauses yet; the dialect
        # adapts it at render time. See ``DDLColumnMixin.translate_ar_attribute``.
        self.attributes = list(attributes or [])

class GeneratedColumnType(Enum):
    """Types of generated columns (computed columns)."""

    STORED = "STORED"  # Stored on disk, can be indexed
    VIRTUAL = "VIRTUAL"  # Computed on read, not stored


class ReferentialAction(Enum):
    """Actions for referential integrity constraints."""

    CASCADE = "CASCADE"
    RESTRICT = "RESTRICT"
    SET_NULL = "SET NULL"
    SET_DEFAULT = "SET DEFAULT"
    NO_ACTION = "NO ACTION"


class ConstraintValidation(Enum):
    """Constraint validation status (PostgreSQL specific).

    Used as the typed ``validation`` field of :class:`TableConstraint` to
    control whether PostgreSQL validates existing data against the constraint.

    - VALIDATE: Validate all existing data (default behavior)
    - NOVALIDATE: Add constraint without validating existing data (NOT VALID)
    """

    VALIDATE = "VALIDATE"
    NOVALIDATE = "NOT VALID"


class ForeignKeyMatchType(Enum):
    """The MATCH type of a foreign key (SQL:1999).

    A multi-column foreign key matches when *some* column pair matches; MATCH
    narrows that:

    - ``SIMPLE`` — the match condition holds if **any one** column matches.
      This is the SQL default, and ``None`` on a constraint means it.
    - ``PARTIAL`` — the match condition holds only if **all** columns match.
    - ``FULL`` — no partial match is permitted.

    ``__str__`` returns the SQL spelling rather than ``ForeignKeyMatchType.FULL``
    because a dialect formatter may interpolate the member directly, and a
    member that renders as its Python name would put invalid SQL on the wire.
    """

    SIMPLE = "SIMPLE"
    PARTIAL = "PARTIAL"
    FULL = "FULL"

    def __str__(self) -> str:
        """The SQL spelling of this match type."""
        return self.value


class ColumnConstraintBranch(BaseExpression, ABC):
    """Base class for the branches of a column-level constraint.

    A column constraint is a grammar production with one alternative per
    kind, so each alternative is a branch node holding only what is specific
    to it. :class:`ColumnConstraint` holds the production-level parts -- the
    ``CONSTRAINT <name>`` prefix and the trailing traits -- and refers to a
    branch rather than being one, because the two live at different levels of
    the grammar (规则文档 E1/E2, Layout).

    A branch never renders itself: :meth:`format_column_constraint` renders
    the production and dispatches to the branch's own formatter.
    """


class ColumnPrimaryKeyConstraint(ColumnConstraintBranch):
    """``PRIMARY KEY``, optionally SQLite's ``AUTOINCREMENT``."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        is_auto_increment: bool = False,
    ):
        super().__init__(dialect)
        self.is_auto_increment = is_auto_increment

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_column_primary_key_constraint"


class ColumnUniqueConstraint(ColumnConstraintBranch):
    """``UNIQUE``."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_column_unique_constraint"


class ColumnNotNullConstraint(ColumnConstraintBranch):
    """``NOT NULL``."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_column_not_null_constraint"


class ColumnNullableConstraint(ColumnConstraintBranch):
    """``NULL`` -- the column is allowed to hold no value.

    The name is the adjective rather than the keyword on purpose: what the
    constraint states about a column is that it is *nullable*, which is also
    how a reader tells this branch apart from the ``NULL`` value a literal
    holds.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_column_nullable_constraint"


class ColumnCheckConstraint(ColumnConstraintBranch):
    """``CHECK (<condition>)``.

    A CHECK position accepts no bind parameters, so the class declares
    ``inline_params = True``; the dialect renders the condition inline-only
    and refuses any residual bind value.
    """

    inline_params: bool = True

    def __init__(
        self,
        dialect: "SQLDialectBase",
        condition: "SQLPredicate",
    ):
        if condition is None:
            raise ValueError(
                "ColumnCheckConstraint needs a condition: CHECK without one "
                "states nothing."
            )
        super().__init__(dialect)
        self.condition = condition

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_column_check_constraint"


class ColumnDefaultConstraint(ColumnConstraintBranch):
    """``DEFAULT <value>``.

    Not an ENFORCABLE kind: SQL:2016 gives the enforcement trait to PRIMARY
    KEY, UNIQUE, FOREIGN KEY and CHECK only, so this branch carries no way to
    ask for it.

    A DEFAULT position accepts no bind parameters, so the class declares
    ``inline_params = True``; the value renders inline only.
    """

    inline_params: bool = True

    def __init__(
        self,
        dialect: "SQLDialectBase",
        value: Any,
    ):
        if value is None:
            raise ValueError(
                "ColumnDefaultConstraint needs a value: DEFAULT without one "
                "states nothing. The refusal is here rather than at render "
                "time because a clause with no value cannot be rendered at all."
            )
        super().__init__(dialect)
        self.value = value

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_column_default_constraint"


class ColumnForeignKeyConstraint(ColumnConstraintBranch):
    """A column-level ``FOREIGN KEY``: the column, and where it points."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        references: Tuple["Table", List[str]],
        on_delete: Optional["ReferentialAction"] = None,
        on_update: Optional["ReferentialAction"] = None,
        match_type: Optional["ForeignKeyMatchType"] = None,
    ):
        super().__init__(dialect)
        if references is None or references[0] is None:
            raise ValueError(
                "ColumnForeignKeyConstraint needs references: the (Table, "
                "[columns]) it points at. A foreign key without one points "
                "nowhere."
            )
        if not isinstance(references[0], Table):
            raise TypeError(
                f"ColumnForeignKeyConstraint.references must pair a Table "
                f"with its columns, got {type(references[0]).__name__}"
            )
        self.references = references
        self.on_delete = on_delete
        self.on_update = on_update
        self.match_type = match_type

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_column_fk_constraint"


class ColumnGeneratedConstraint(ColumnConstraintBranch):
    """``GENERATED ALWAYS AS (<expression>) [STORED|VIRTUAL]``.

    The column-level counterpart of the generated-column production. It is a
    constraint branch rather than a free-standing node, so it rides wherever a
    column constraint rides and answers to the same level's prefix.

    A generated-column expression is a DDL position, so the class declares
    ``inline_params = True``; the expression renders inline-only.
    """

    inline_params: bool = True

    def __init__(
        self,
        dialect: "SQLDialectBase",
        expression: "BaseExpression",
        storage_type: Optional[GeneratedColumnType] = None,
    ):
        super().__init__(dialect)
        self.expression = expression
        # The default is the node's, not the formatter's: what "generated
        # column" means without a storage clause is settled once, here.
        self.storage_type = storage_type or GeneratedColumnType.VIRTUAL

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_column_generated_constraint"


class ColumnConstraint(BaseExpression):
    """One column-level constraint clause: ``[CONSTRAINT <name>] <branch> [traits]``.

    The production, not one of its alternatives. What the grammar hangs on
    the production -- the ``CONSTRAINT <name>`` prefix and the trailing
    ``DEFERRABLE`` / ``INITIALLY`` / ``ENFORCED`` traits -- lives here; what
    belongs to one alternative lives in the :class:`ColumnConstraintBranch`
    this refers to. Two levels because that is where the grammar puts them,
    not for convenience: it is what lets a backend re-spell one kind without
    touching the prefix or the traits, and what makes a request the kind
    cannot honour impossible to express at all.

    Args:
        dialect: The dialect that renders the clause.
        branch: The alternative this clause states -- a
            :class:`ColumnConstraintBranch`. Required: a constraint clause
            without one says nothing.
        name: The ``CONSTRAINT <name>`` prefix. Authorised by
            ``supports_constraint_naming``.
        deferrable / not_deferrable: the deferral trait. Authorised by
            ``supports_deferrable_constraint``; carried only by the PRIMARY
            KEY, UNIQUE and FOREIGN KEY branches, so asking for it on another
            branch is a ``TypeError`` raised by :meth:`validate_branch_traits`
            rather than a request that is quietly dropped.
        initially_deferred / initially_immediate: the timing half of the same
            trait, which the standard lets appear without the deferral half.
        enforced / not_enforced: the SQL:2016 enforcement trait, carried by
            the PRIMARY KEY, UNIQUE, FOREIGN KEY and CHECK branches.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_column_constraint"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        *,
        branch: ColumnConstraintBranch,
        name: Optional[str] = None,
        deferrable: bool = False,
        not_deferrable: bool = False,
        initially_deferred: bool = False,
        initially_immediate: bool = False,
        enforced: bool = False,
        not_enforced: bool = False,
    ):
        from rhosocial.activerecord.backend.expression import (
            ColumnConstraintBranch,
        )
        super().__init__(dialect)
        if not isinstance(branch, ColumnConstraintBranch):
            raise TypeError(
                f"ColumnConstraint.branch must be a ColumnConstraintBranch, "
                f"got {type(branch).__name__}"
            )
        require_exclusive_options(deferrable, not_deferrable, "deferrable", "not_deferrable")
        require_exclusive_options(
            initially_deferred,
            initially_immediate,
            "initially_deferred",
            "initially_immediate",
        )
        require_exclusive_options(enforced, not_enforced, "enforced", "not_enforced")
        self.branch = branch
        self.name = name
        self.deferrable = deferrable
        self.not_deferrable = not_deferrable
        self.initially_deferred = initially_deferred
        self.initially_immediate = initially_immediate
        self.enforced = enforced
        self.not_enforced = not_enforced
        self.validate_branch_traits(branch)

    def validate_branch_traits(self, branch: ColumnConstraintBranch) -> None:
        """Refuse a trait the branch's kind cannot carry.

        The branches that can carry each trait are named by
        :attr:`DEFERRABLE_BRANCHES` and :attr:`ENFORCABLE_BRANCHES`. Before
        the branches existed, a request on a kind that had no meaning for it
        was accepted and then dropped without a word; here it cannot be
        written in the first place.
        """
        wants_deferral = self.deferrable or self.not_deferrable
        if (wants_deferral or self.initially_deferred or self.initially_immediate) and (
            type(branch) not in self.DEFERRABLE_BRANCHES
        ):
            raise ValueError(
                f"DEFERRABLE / INITIALLY cannot ride a "
                f"{type(branch).__name__}; the SQL:2016 kinds are "
                f"PRIMARY KEY, UNIQUE and FOREIGN KEY"
            )
        if (self.enforced or self.not_enforced) and type(branch) not in self.ENFORCABLE_BRANCHES:
            raise ValueError(
                f"ENFORCED/NOT ENFORCED cannot ride a {type(branch).__name__}; "
                f"the SQL:2016 kinds are PRIMARY KEY, UNIQUE, FOREIGN KEY and CHECK"
            )

    #: Branches whose kind can carry the deferral trait.
    DEFERRABLE_BRANCHES = frozenset(
        {ColumnPrimaryKeyConstraint, ColumnUniqueConstraint, ColumnForeignKeyConstraint}
    )

    #: Branches whose kind can carry the enforcement trait (SQL:2016).
    ENFORCABLE_BRANCHES = frozenset(
        {
            ColumnPrimaryKeyConstraint,
            ColumnUniqueConstraint,
            ColumnForeignKeyConstraint,
            ColumnCheckConstraint,
        }
    )

    @property
    def constraint_type(self):
        """The removed tag, reported rather than silently absent.

        ``constraint_type`` said which kind a fat node was pretending to be.
        The branch says it now, in a class rather than in a field, so a
        caller still asking for the tag is told where the answer moved.
        """
        from rhosocial.activerecord.backend.expression import (
            ColumnCheckConstraint,
            ColumnDefaultConstraint,
            ColumnForeignKeyConstraint,
            ColumnGeneratedConstraint,
            ColumnNotNullConstraint,
            ColumnNullableConstraint,
            ColumnPrimaryKeyConstraint,
            ColumnUniqueConstraint,
        )
        kind = {
            ColumnPrimaryKeyConstraint: "PRIMARY KEY",
            ColumnUniqueConstraint: "UNIQUE",
            ColumnNotNullConstraint: "NOT NULL",
            ColumnNullableConstraint: "NULL",
            ColumnCheckConstraint: "CHECK",
            ColumnDefaultConstraint: "DEFAULT",
            ColumnForeignKeyConstraint: "FOREIGN KEY",
            ColumnGeneratedConstraint: "GENERATED",
        }.get(type(self.branch), type(self.branch).__name__)
        raise AttributeError(
            f"ColumnConstraint.constraint_type is gone; the kind is the branch "
            f"({type(self.branch).__name__}, which is a {kind} constraint)"
        )


class TableConstraintBranch(BaseExpression, ABC):
    """Base class for the branches of a table-level constraint.

    The table counterpart of :class:`ColumnConstraintBranch`: one node per
    alternative of the table-constraint production, each holding only its own
    fields, with :class:`TableConstraint` holding the production-level prefix,
    the ``NOT VALID`` trait and the enforcement trait.
    """


class TablePrimaryKeyConstraint(TableConstraintBranch):
    """A table-level ``PRIMARY KEY`` over one or more columns."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        columns: List[str],
    ):
        super().__init__(dialect)
        self.columns = list(columns)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_table_primary_key_constraint"


class TableUniqueConstraint(TableConstraintBranch):
    """A table-level ``UNIQUE`` over one or more columns."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        columns: List[str],
    ):
        super().__init__(dialect)
        self.columns = list(columns)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_table_unique_constraint"


class TableCheckConstraint(TableConstraintBranch):
    """A table-level ``CHECK (<condition>)``.

    A CHECK position accepts no bind parameters, so the class declares
    ``inline_params = True``; the dialect renders the condition inline-only
    and refuses any residual bind value.
    """

    inline_params: bool = True

    def __init__(
        self,
        dialect: "SQLDialectBase",
        condition: "SQLPredicate",
    ):
        if condition is None:
            raise ValueError(
                "TableCheckConstraint needs a condition: CHECK without one "
                "states nothing."
            )
        super().__init__(dialect)
        self.condition = condition

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_table_check_constraint"


class TableForeignKeyConstraint(TableConstraintBranch):
    """A table-level ``FOREIGN KEY`` over one or more columns."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        columns: List[str],
        references: Tuple["Table", Optional[List[str]]],
        on_delete: Optional["ReferentialAction"] = None,
        on_update: Optional["ReferentialAction"] = None,
        match_type: Optional["ForeignKeyMatchType"] = None,
    ):
        super().__init__(dialect)
        if references is None or references[0] is None:
            raise ValueError(
                "TableForeignKeyConstraint needs references: the (Table, "
                "[columns]) it points at."
            )
        self.columns = list(columns or [])
        self.references = references
        self.on_delete = on_delete
        self.on_update = on_update
        self.match_type = match_type

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_table_foreign_key_constraint"


class TableExcludeConstraint(TableConstraintBranch):
    """``EXCLUDE`` -- the exclusion constraint.

    Enumerable, so it is modelled rather than refused: one branch, and the
    dialects that cannot spell it refuse it by name through
    :meth:`supports_exclude_constraint` instead of rendering SQL their server
    will reject. Only PostgreSQL can spell it today; the probe is what says so
    per dialect.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        columns: List[str],
        operator: str = "=",
        index_method: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.columns = list(columns)
        self.operator = operator
        self.index_method = index_method

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_table_exclude_constraint"


class TableConstraint(BaseExpression):
    """One table-level constraint clause: ``[CONSTRAINT <name>] <branch> [traits]``.

    The production, with the alternative it states named by :attr:`branch`.
    The table counterpart of :class:`ColumnConstraint`: ``name`` and the
    ``NOT VALID`` trait are production-level because the grammars put them
    there, and the columns, the referenced table and the check condition
    belong to the branches.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_table_constraint"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        *,
        branch: TableConstraintBranch,
        name: Optional[str] = None,
        deferrable: bool = False,
        not_deferrable: bool = False,
        initially_deferred: bool = False,
        initially_immediate: bool = False,
        validation: Optional[ConstraintValidation] = None,
        enforced: bool = False,
        not_enforced: bool = False,
    ):
        from rhosocial.activerecord.backend.expression import (
            TableConstraintBranch,
        )
        super().__init__(dialect)
        if not isinstance(branch, TableConstraintBranch):
            raise TypeError(
                f"TableConstraint.branch must be a TableConstraintBranch, "
                f"got {type(branch).__name__}"
            )
        require_exclusive_options(enforced, not_enforced, "enforced", "not_enforced")
        require_exclusive_options(deferrable, not_deferrable, "deferrable", "not_deferrable")
        require_exclusive_options(
            initially_deferred,
            initially_immediate,
            "initially_deferred",
            "initially_immediate",
        )
        self.branch = branch
        self.name = name
        self.deferrable = deferrable
        self.not_deferrable = not_deferrable
        self.initially_deferred = initially_deferred
        self.initially_immediate = initially_immediate
        # PostgreSQL: NOT VALID for an added constraint (None = default VALIDATE).
        self.validation = validation
        # MariaDB/SQL Server: CHECK ... [NOT] ENFORCED (None = backend default).
        self.enforced = enforced
        self.not_enforced = not_enforced
        if (self.enforced or self.not_enforced) and type(branch) not in self.ENFORCABLE_BRANCHES:
            raise ValueError(
                f"ENFORCED/NOT ENFORCED cannot ride a {type(branch).__name__}; "
                f"the SQL:2016 kinds are PRIMARY KEY, UNIQUE, FOREIGN KEY and CHECK"
            )
        wants_deferral = self.deferrable or self.not_deferrable
        if (wants_deferral or self.initially_deferred or self.initially_immediate) and (
            type(branch) not in self.DEFERRABLE_BRANCHES
        ):
            raise ValueError(
                f"DEFERRABLE / INITIALLY cannot ride a {type(branch).__name__}; "
                f"the SQL:2016 kinds are PRIMARY KEY, UNIQUE and FOREIGN KEY"
            )

    #: Branches whose kind can carry the enforcement trait (SQL:2016).
    ENFORCABLE_BRANCHES = frozenset(
        {
            TablePrimaryKeyConstraint,
            TableUniqueConstraint,
            TableForeignKeyConstraint,
            TableCheckConstraint,
        }
    )

    #: Branches whose kind can carry the deferral trait.
    DEFERRABLE_BRANCHES = frozenset(
        {TablePrimaryKeyConstraint, TableUniqueConstraint, TableForeignKeyConstraint}
    )

    @property
    def constraint_type(self):
        """The removed tag, reported rather than silently absent."""
        from rhosocial.activerecord.backend.expression import (
            TableCheckConstraint,
            TableExcludeConstraint,
            TableForeignKeyConstraint,
            TablePrimaryKeyConstraint,
            TableUniqueConstraint,
        )
        kind = {
            TablePrimaryKeyConstraint: "PRIMARY KEY",
            TableUniqueConstraint: "UNIQUE",
            TableForeignKeyConstraint: "FOREIGN KEY",
            TableCheckConstraint: "CHECK",
            TableExcludeConstraint: "EXCLUDE",
        }.get(type(self.branch), type(self.branch).__name__)
        raise AttributeError(
            f"TableConstraint.constraint_type is gone; the kind is the branch "
            f"({type(self.branch).__name__}, which is a {kind} constraint)"
        )


class ForeignKeyConstraint(TableConstraint):
    """A table-level FOREIGN KEY, with the referential actions defaulted.

    Construction sugar over :class:`TableForeignKeyConstraint`: the standard
    implies ``NO ACTION`` when the action is not written, so this fills it in
    where the plain branch leaves "not specified" as ``None``.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_table_constraint"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        columns: List[str],
        foreign_key_table: "Table",
        foreign_key_columns: List[str],
        on_delete: "ReferentialAction" = ReferentialAction.NO_ACTION,
        on_update: "ReferentialAction" = ReferentialAction.NO_ACTION,
        match_type: Optional["ForeignKeyMatchType"] = None,
        name: Optional[str] = None,
        deferrable: bool = False,
        not_deferrable: bool = False,
        initially_deferred: bool = False,
        initially_immediate: bool = False,
        validation: Optional[ConstraintValidation] = None,
        enforced: bool = False,
        not_enforced: bool = False,
    ):
        from rhosocial.activerecord.backend.expression import (
            TableForeignKeyConstraint,
        )
        super().__init__(
            dialect,
            branch=TableForeignKeyConstraint(
                dialect,
                columns or [],
                (foreign_key_table, foreign_key_columns) if foreign_key_table else (None, None),
                on_delete,
                on_update,
                match_type,
            ),
            name=name,
            deferrable=deferrable,
            not_deferrable=not_deferrable,
            initially_deferred=initially_deferred,
            initially_immediate=initially_immediate,
            validation=validation,
            enforced=enforced,
            not_enforced=not_enforced,
        )

    # The referential fields live on the branch now. They are exposed here as
    # views rather than stored twice: the sugar declares these parameters, and
    # ``get_params()`` -- the single serialization path -- looks each declared
    # parameter up by name.

    @property
    def columns(self) -> List[str]:
        """The local columns, as the branch records them."""
        return self.branch.columns

    @property
    def foreign_key_table(self) -> Optional["Table"]:
        """The referenced relation, as the branch records it."""
        return self.branch.references[0]

    @property
    def foreign_key_columns(self) -> Optional[List[str]]:
        """The referenced columns, as the branch records them."""
        return self.branch.references[1]

    @property
    def on_delete(self) -> Optional["ReferentialAction"]:
        """The delete action, as the branch records it."""
        return self.branch.on_delete

    @property
    def on_update(self) -> Optional["ReferentialAction"]:
        """The update action, as the branch records it."""
        return self.branch.on_update

    @property
    def match_type(self) -> Optional["ForeignKeyMatchType"]:
        """The MATCH type, as the branch records it."""
        return self.branch.match_type


class IndexDefinition(BaseExpression):
    """Represents an index definition clause for CREATE TABLE / ADD INDEX.

    ``columns`` accepts plain column names or :class:`BaseExpression`
    instances (functional/expression index columns, e.g. ``LOWER(name)``).

    Statement-level options (§5.16, plan 方案 A) are carried per index so the
    standalone ``CREATE INDEX`` / ``DROP INDEX`` statements can differ one by
    one. ``if_exists`` / ``if_not_exists`` are present-or-absent clauses, so
    they are plain ``bool`` flags: ``None`` (the model-layer marker's "not
    declared") is coerced to ``False``. They are ignored by the inline path
    (an index riding inside CREATE TABLE cannot carry statement options; the
    deriver raises on the inline path instead).
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_index_definition"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: str,
        columns: List[Union[str, "BaseExpression"]],
        unique: bool = False,
        type: Optional[str] = None,
        partial_condition: Optional["SQLPredicate"] = None,
        include_columns: Optional[List[str]] = None,
        if_not_exists: bool = False,
        tablespace: Optional[str] = None,
        if_exists: bool = False,
        concurrent: Optional[bool] = None,
    ):
        super().__init__(dialect)
        self.name = name
        self.columns = list(columns)
        self.unique = unique
        self.type = type
        self.partial_condition = partial_condition
        self.include_columns = include_columns
        # Statement-level options (§5.16): ``if_not_exists`` (create path),
        # ``tablespace`` (create path), ``if_exists`` (drop path) and
        # ``concurrent`` (create/drop shared). Present-or-absent clauses: a
        # plain bool, never a tri-state.
        self.if_not_exists = bool(if_not_exists)
        self.tablespace = tablespace
        self.if_exists = bool(if_exists)
        self.concurrent = concurrent


class CreateTableOptions(BaseExpression):
    """Generic creation modifiers for ``CREATE TABLE``.

    Holds only the **generic** (SQL-standard or broadly shared) options:

    **Header modifier** (between ``CREATE`` and ``TABLE``):

    * ``or_replace`` -- ``CREATE OR REPLACE TABLE`` (standard; widely supported)

    **Table-level option** (after the column list):

    * ``comment`` -- inline table-comment clause, carried as a
      :class:`TableCommentClause`. There is **no** SQL-standard table comment
      mechanism: the bare ``COMMENT '<text>'`` table option is a
      MySQL/MariaDB/ClickHouse-family dialect convenience (Snowflake renders
      ``COMMENT = '<text>'``, BigQuery ``OPTIONS(description='<text>')``), and
      the standalone ``COMMENT ON`` statement is a separate de-facto vendor
      mechanism (:class:`CommentOnStatement`), not this clause. Bare comment
      text is **not** accepted — build the clause node explicitly; rendering
      is capability-gated by the statement renderer through
      :meth:`supports_table_comment`, which raises ``UnsupportedFeatureError``
      on dialects without the grammar instead of silently dropping a declared
      comment.

    Backend-specific creation options (``UNLOGGED`` / ``TRANSIENT`` /
    ``ENGINE`` / ``CHARSET`` / table ``COLLATE`` / ``MEMORY_OPTIMIZED`` /
    ``DURABILITY`` / …) live on a backend's own ``XxxCreateTableOptions``
    subclass — they are **not** generic and there is no ``dialect_options``
    bag.

    ``or_replace`` is rendered by ``format_create_table_options``; the
    statement renderer composes the returned qualifier right after ``CREATE``.
    ``comment`` is a clause node rendered by the statement renderer after the
    column list.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_create_table_options"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        *,
        or_replace: bool = False,
        comment: Optional["TableCommentClause"] = None,
    ):
        super().__init__(dialect)
        if comment is not None and not isinstance(comment, TableCommentClause):
            raise TypeError(
                f"comment must be a TableCommentClause, got {type(comment).__name__}"
            )
        self.or_replace = or_replace
        self.comment = comment


class CreateTableStatement(BaseExpression):
    """Represents a comprehensive CREATE TABLE statement supporting full SQL standard features."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: "Table",
        columns: List[ColumnDefinition],  # List of column definitions with constraints
        indexes: Optional[List[IndexDefinition]] = None,  # Table indexes
        table_constraints: Optional[List[TableConstraint]] = None,  # Table-level constraints
        temporary: bool = False,  # TEMPORARY table flag
        if_not_exists: bool = False,  # IF NOT EXISTS flag
        inherits: Optional[List[str]] = None,  # PostgreSQL INHERITS clause
        tablespace: Optional[str] = None,  # Table tablespace (PostgreSQL/Oracle)
        storage_options: Optional["StorageOptionsExpression"] = None,  # Storage options clause
        *,  # Force keyword arguments
        partition: Optional["PartitionClause"] = None,  # Table partitioning specification
        table_options: Optional["CreateTableOptions"] = None,  # CREATE header modifiers
    ):
        super().__init__(dialect)
        self.table = table
        self.columns = columns  # List of column definitions with embedded constraints
        self.indexes = indexes or []  # List of indexes to create
        self.table_constraints = table_constraints or []  # List of table-level constraints
        self.temporary = temporary  # Temporary table flag
        self.if_not_exists = if_not_exists  # IF NOT EXISTS flag
        self.inherits = inherits or []  # Tables to inherit from (PostgreSQL-specific)
        self.tablespace = tablespace  # Tablespace specification
        self.storage_options = storage_options  # Storage options clause (StorageOptionsExpression)
        # Validate partition parameter type
        if partition is not None and not isinstance(partition, PartitionClause):
            raise TypeError(f"partition must be a PartitionClause instance, got {type(partition).__name__}")
        self.partition = partition
        self.table_options = table_options  # CreateTableOptions (header modifiers)

    @property
    def table_name(self) -> str:
        """Get the table name (for backward compatibility)."""
        return self.table.name

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_create_table_statement"


class CreateTableAsStatement(BaseExpression):
    """Represents ``CREATE TABLE ... AS <query>`` (CTAS).

    The table's structure is derived from the result of a query.  Unlike the
    explicit-schema form (:class:`CreateTableStatement`), the body is a query,
    not a column list.

    Rendering is delegated to the dialect's ``format_create_table_as_statement``.
    The generic implementation emits ``AS <query>`` **without parentheses**
    (parenthesising the query is rejected by SQLite and several other engines).
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_create_table_as_statement"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: "Table",
        as_query: "QueryStatement",
        *,
        columns: Optional[List[ColumnDefinition]] = None,
        temporary: bool = False,
        if_not_exists: bool = False,
        storage_options: Optional["StorageOptionsExpression"] = None,
        with_data: bool = False,
        no_data: bool = False,
    ):
        super().__init__(dialect)
        require_exclusive_options(with_data, no_data, "with_data", "no_data")
        self.table = table
        if as_query is None:
            raise ValueError("as_query is required for CreateTableAsStatement")
        self.as_query = as_query
        self.columns = list(columns or [])
        self.temporary = temporary
        self.if_not_exists = if_not_exists
        self.storage_options = storage_options
        self.with_data = with_data
        self.no_data = no_data

    @property
    def table_name(self) -> str:
        """Get the target table name."""
        return self.table.name


class CreateTableLikeStatement(BaseExpression):
    """Represents ``CREATE TABLE ... LIKE <source_table>``.

    Creates a new empty table copying the *definition* (column attributes,
    indexes) of an existing table, without copying data.  This is a vendor
    extension with no SQL-standard syntax:

    * MySQL / MariaDB: ``CREATE TABLE t LIKE src``
    * Snowflake:       ``CREATE TABLE t LIKE src [COPY GRANTS]``
    * BigQuery:        ``CREATE TABLE t LIKE src [OPTIONS (...)]``
    * PostgreSQL:      clause form ``CREATE TABLE t (LIKE src [INCLUDING ...])``
    * ClickHouse:      uses ``AS src`` / ``CLONE AS src`` -- model through
      :class:`CreateTableAsStatement` / :class:`CreateTableCloneStatement`,
      not this class.

    The generic ``format_create_table_like_statement`` raises
    :class:`UnsupportedFeatureError`; dialects that support the form override it.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_create_table_like_statement"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: "Table",
        like_table: "Table",
        *,
        temporary: bool = False,
        if_not_exists: bool = False,
        like_options: Optional[Any] = None,
    ):
        super().__init__(dialect)
        self.table = table
        self.like_table = like_table
        self.temporary = temporary
        self.if_not_exists = if_not_exists
        # PostgreSQL-specific INCLUDING/EXCLUDING options (dict or list).
        self.like_options = like_options

    @property
    def table_name(self) -> str:
        """Get the target table name."""
        return self.table.name


class CreateTableCloneMode(Enum):
    """Mode of a definition/data copy operation."""

    CLONE = "CLONE"
    COPY = "COPY"


class CreateTableCloneStatement(BaseExpression):
    """Represents ``CREATE TABLE ... CLONE/COPY <source_table>``.

    Zero-copy (or metadata/data copy) creation from an existing table:

    * Snowflake: ``CREATE TABLE t CLONE src [AT|BEFORE (...)] [COPY GRANTS]``
    * BigQuery:  ``CREATE TABLE t CLONE src`` / ``CREATE TABLE t COPY src``
    * ClickHouse: ``CREATE TABLE t CLONE AS src``

    ``mode`` selects CLONE vs COPY where a dialect distinguishes them.
    ``at`` / ``before`` carry time-travel specifications (Snowflake/BigQuery).
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_create_table_clone_statement"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: "Table",
        source_table: "Table",
        *,
        mode: CreateTableCloneMode = CreateTableCloneMode.CLONE,
        temporary: bool = False,
        if_not_exists: bool = False,
        at: Optional[Any] = None,
        before: Optional[Any] = None,
        copy_grants: bool = False,
    ):
        super().__init__(dialect)
        if not isinstance(mode, CreateTableCloneMode):
            raise TypeError(f"mode must be a CreateTableCloneMode, got {type(mode).__name__}")
        self.table = table
        self.source_table = source_table
        self.mode = mode
        self.temporary = temporary
        self.if_not_exists = if_not_exists
        self.at = at
        self.before = before
        self.copy_grants = copy_grants

    @property
    def table_name(self) -> str:
        """Get the target table name."""
        return self.table.name


class CreateTableFromTemplateStatement(BaseExpression):
    """Represents Snowflake ``CREATE TABLE ... USING TEMPLATE <query>``.

    Derives the table's column definitions from staged files described by a
    query (typically ``INFER_SCHEMA``).  Dialects that do not support this form
    raise :class:`UnsupportedFeatureError` from
    ``format_create_table_from_template_statement``.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_create_table_from_template_statement"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: "Table",
        template: "QueryStatement",
        *,
        temporary: bool = False,
        if_not_exists: bool = False,
    ):
        super().__init__(dialect)
        self.table = table
        if template is None:
            raise ValueError("template is required for CreateTableFromTemplateStatement")
        self.template = template
        self.temporary = temporary
        self.if_not_exists = if_not_exists

    @property
    def table_name(self) -> str:
        """Get the target table name."""
        return self.table.name


class DropTableStatement(BaseExpression):
    """Represents a DROP TABLE statement conforming to SQL standard.

    SQL Standard Syntax:
        DROP TABLE [IF EXISTS] <table_name> [CASCADE | RESTRICT]

    The CASCADE/RESTRICT options control dependent object handling:
    - CASCADE: Automatically drops dependent objects (views, foreign keys)
    - RESTRICT: Refuses to drop if dependencies exist (default in SQL standard)

    Each spelling has its own parameter (``cascade`` / ``restrict``); leaving
    both unset omits the clause, and setting both raises ``ValueError``.

    Capability gating is enforced by the dialect's ``format_drop_table_statement``
    helper via the protocol switches ``supports_drop_table_cascade()`` and
    ``supports_drop_table_restrict()``: asking for a behavior the dialect does
    not support raises ``UnsupportedFeatureError`` rather than emitting a token
    the database would reject (or silently drop).

    Database-specific behavior:
    - PostgreSQL: Full CASCADE/RESTRICT support (both switches True)
    - MySQL/MariaDB: CASCADE keyword is parsed but ignored (no functional
      effect); the switches are True to reflect valid syntax, NOT valid
      semantics. Refer to the dialect docstring for the no-op caveat.
    - Oracle: Uses the backend-specific ``CASCADE CONSTRAINTS [PURGE]`` form
      (narrower than SQL-standard CASCADE: only drops referencing constraints,
      not views/triggers). Declared via Oracle's backend protocol and rendered
      by an Oracle-specific override of ``format_drop_table_statement``.
    - SQLite: CASCADE/RESTRICT not recognized; both switches False -> raising.
    - SQL Server: No CASCADE/RESTRICT support; both switches False -> raising.
    - Firebird: No CASCADE/RESTRICT support; both switches False -> raising.

    Args:
        dialect: The SQL dialect to use for formatting
        table: The Table being dropped
        if_exists: Add IF EXISTS clause to avoid error if table doesn't exist
        cascade: Emit CASCADE (or the dialect-specific equivalent form)
        restrict: Emit RESTRICT (or raise if unsupported)
        purge: Oracle PURGE via a typed flag which, combined with cascade=True,
            appends PURGE after the dialect-specific cascade form.

    Examples:
        # Simple drop
        DropTableStatement(dialect, Table(dialect, "users"))
        # -> DROP TABLE users

        # With IF EXISTS
        DropTableStatement(dialect, "users", if_exists=True)
        # -> DROP TABLE IF EXISTS users  (on dialects supporting IF EXISTS)

        # With CASCADE (PostgreSQL / MySQL / MariaDB)
        DropTableStatement(dialect, "users", cascade=True)
        # -> DROP TABLE users CASCADE

        # With CASCADE on Oracle (dialect renders its own form)
        DropTableStatement(oracle_dialect, "users", cascade=True, purge=True)
        # -> DROP TABLE users CASCADE CONSTRAINTS PURGE

        # With schema-qualified table
        DropTableStatement(dialect, Table(dialect, "users", schema_name="public"))
        # -> DROP TABLE public.users
    """
    
    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_drop_table_statement"
    
    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: "Table",
        if_exists: bool = False,
        cascade: bool = False,
        restrict: bool = False,
        purge: bool = False,
    ):
        super().__init__(dialect)
        require_exclusive_options(cascade, restrict, "cascade", "restrict")
        self.table = table
        self.if_exists = if_exists
        self.cascade = cascade
        self.restrict = restrict
        self.purge = purge


class StorageOptionsExpression(BaseExpression):
    """Represents a ``WITH (...)`` or storage-options clause.

    Holds a mapping of option names to values.  The dialect formatter renders
    each pair as ``key = <value>`` where the value is inlined via
    ``inline_sql_literal``.

    Storage options are a DDL position, so the class declares
    ``inline_params = True``: values render inline only.
    """

    inline_params: bool = True

    def __init__(
        self,
        dialect: "SQLDialectBase",
        options: Dict[str, Any],
    ):
        super().__init__(dialect)
        self.options = options

    def to_sql(self) -> SQLQueryAndParams:
        """Delegate to the dialect's ``format_storage_options``."""
        return self.dialect.format_storage_options(self)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_storage_options"
