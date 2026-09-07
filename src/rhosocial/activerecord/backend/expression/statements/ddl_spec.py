# src/rhosocial/activerecord/backend/expression/statements/ddl_spec.py
"""Declarative DDL feature specifications (Specs).

Specs are plain objects that capture a user's *intent* for a table's
structure without binding to any backend dialect. They are the currency of
the dialect-claiming layer: a model declares feature Specs (field-level via
``Annotated`` markers, table-level via the ``__table_constraints__`` /
``__table_indexes__`` declaration slots), and each backend decides whether
it accepts a Spec and, if so, how to translate it into expression-layer
objects (``ColumnConstraint`` / ``TableConstraint`` / ``IndexDefinition`` /
``PartitionClause`` / ...) through ``dialect.build_spec``.

Design rules:

1. **No dialect at declaration time** — all fields are plain Python values,
   or lazy predicate factories ``(dialect) -> SQLPredicate`` (CHECK / partial
   index conditions only). The user never touches a backend.
2. **Backend-correctable translation** — a generic Spec's default translation
   is only a starting point; each backend may override it or reject the Spec
   (``build_spec`` returns ``None``).
3. **Unclaimed means silently ignored** — when ``build_spec`` returns ``None``
   the Spec contributes nothing; whether that is acceptable is the backend's
   decision (it may raise inside ``build_spec``). Users do not set
   ``required`` / ``suggested`` flags.

The ``DDLSpec`` base class is intentionally empty (a pure marker). All
claiming / translation / error decisions live in the dialect's
``build_spec`` implementation, not in the Spec itself.
"""

from typing import Any, Callable, Optional, Sequence, Union

# A lazy predicate factory: evaluated with a dialect when the DDL is built.
LazyPredicate = Callable[["Any"], "Any"]  # (dialect) -> SQLPredicate

# A value that may be a plain value or a dialect-parameterized factory.
LazyValue = Union[Any, Callable[["Any"], Any]]


class DDLSpec:
    """Base class for all DDL feature specifications (pure empty marker).

    Carries no fields and implements no logic. Subclasses only add
    declaration data; every behavioral decision (claim / translate / raise)
    is the dialect's ``build_spec`` responsibility.
    """

    __slots__ = ()


class CheckSpec(DDLSpec):
    """A CHECK constraint on one or more columns.

    ``condition`` may be a ready ``SQLPredicate`` or a lazy factory
    ``(dialect) -> SQLPredicate`` so the predicate can be built with the
    dialect that is only known at DDL-generation time.
    """

    __slots__ = ("condition", "name", "columns")

    def __init__(
        self,
        condition: Union["Any", LazyPredicate],
        *,
        name: Optional[str] = None,
        columns: Optional[Sequence[str]] = None,
    ):
        if condition is None:
            raise ValueError("CheckSpec requires a non-null condition")
        self.condition = condition
        self.name = name
        self.columns = list(columns) if columns is not None else None


class UniqueSpec(DDLSpec):
    """A UNIQUE constraint over one or more columns."""

    __slots__ = ("columns", "name")

    def __init__(
        self,
        columns: Sequence[str],
        *,
        name: Optional[str] = None,
    ):
        if not columns:
            raise ValueError("UniqueSpec requires at least one column")
        self.columns = list(columns)
        self.name = name


class NotNullSpec(DDLSpec):
    """A NOT NULL constraint on a single column."""

    __slots__ = ("column", "name")

    def __init__(self, column: str, *, name: Optional[str] = None):
        if not column:
            raise ValueError("NotNullSpec requires a column name")
        self.column = column
        self.name = name


class PrimaryKeySpec(DDLSpec):
    """A PRIMARY KEY over one or more columns.

    A single-column key is rendered as a column-level PK; a multi-column key
    as a table-level composite PK constraint.
    """

    __slots__ = ("columns", "name")

    def __init__(
        self,
        columns: Sequence[str],
        *,
        name: Optional[str] = None,
    ):
        if not columns:
            raise ValueError("PrimaryKeySpec requires at least one column")
        self.columns = list(columns)
        self.name = name


class DefaultSpec(DDLSpec):
    """A literal DEFAULT value for a single column.

    ``value`` may be a plain value or a lazy factory ``(dialect) -> Any``.
    Literal defaults are the portable common denominator; expression-based
    defaults (e.g. ``nextval``) are backend-specific and belong in backend
    Spec classes (e.g. ``PostgresSequenceDefault`` / ``OracleSequenceDefault``).
    """

    __slots__ = ("column", "value", "name")

    def __init__(
        self,
        column: str,
        value: LazyValue = None,
        *,
        name: Optional[str] = None,
    ):
        if not column:
            raise ValueError("DefaultSpec requires a column name")
        self.column = column
        self.value = value
        self.name = name


class ForeignKeySpec(DDLSpec):
    """A FOREIGN KEY referencing another table.

    ``local_columns`` are the referencing columns on this table;
    ``ref_table`` / ``ref_columns`` identify the referenced side.
    """

    __slots__ = (
        "local_columns",
        "ref_table",
        "ref_columns",
        "on_delete",
        "on_update",
        "name",
    )

    def __init__(
        self,
        local_columns: Sequence[str],
        ref_table: str,
        ref_columns: Optional[Sequence[str]] = None,
        *,
        on_delete: Optional[str] = None,
        on_update: Optional[str] = None,
        name: Optional[str] = None,
    ):
        if not local_columns:
            raise ValueError("ForeignKeySpec requires at least one local column")
        if not ref_table:
            raise ValueError("ForeignKeySpec requires a referenced table name")
        self.local_columns = list(local_columns)
        self.ref_table = ref_table
        self.ref_columns = list(ref_columns) if ref_columns is not None else None
        self.on_delete = on_delete
        self.on_update = on_update
        self.name = name


class IndexSpec(DDLSpec):
    """An index over one or more columns.

    For a partial index, ``partial_condition`` may be a ready ``SQLPredicate``
    or a lazy factory ``(dialect) -> SQLPredicate``.
    """

    __slots__ = (
        "columns",
        "name",
        "unique",
        "type",
        "partial_condition",
        "include_columns",
        "dialect_options",
    )

    def __init__(
        self,
        columns: Sequence[str],
        *,
        name: Optional[str] = None,
        unique: bool = False,
        type: Optional[str] = None,
        partial_condition: Optional[Union["Any", LazyPredicate]] = None,
        include_columns: Optional[Sequence[str]] = None,
        dialect_options: Optional[dict] = None,
    ):
        if not columns:
            raise ValueError("IndexSpec requires at least one column")
        self.columns = list(columns)
        self.name = name
        self.unique = unique
        self.type = type
        self.partial_condition = partial_condition
        self.include_columns = list(include_columns) if include_columns else None
        self.dialect_options = dialect_options


class PartitionSpec(DDLSpec):
    """Marker base for backend-defined partition declaration classes.

    The core defines no partition classes and performs no matching. Each
    backend provides its own partition Spec subclasses and recognizes them in
    ``build_spec`` via ``isinstance``, translating them into the dialect's own
    partition expression (e.g. ``PartitionClause``). Backends that recognize
    no partition Spec (e.g. SQLite) simply return ``None`` and the table is
    created unpartitioned.
    """

    __slots__ = ()


class PartialIndexSpec(IndexSpec):
    """A partial (filtered) index.

    Shorthand for an ``IndexSpec`` that always carries a partial condition.
    The condition may be a ready ``SQLPredicate`` or a lazy
    ``(dialect) -> SQLPredicate`` factory. Backends without partial-index
    support reject it (``build_spec`` returns ``None``).
    """

    __slots__ = ()

    def __init__(
        self,
        columns: Sequence[str],
        condition: Union["Any", LazyPredicate],
        *,
        name: Optional[str] = None,
        unique: bool = False,
        include_columns: Optional[Sequence[str]] = None,
        dialect_options: Optional[dict] = None,
    ):
        super().__init__(
            columns=columns,
            name=name,
            unique=unique,
            partial_condition=condition,
            include_columns=include_columns,
            dialect_options=dialect_options,
        )


class ColumnTypeSpec(DDLSpec):
    """A column-type capability spec (e.g. JSON column).

    Marks that a column should use a backend-native type when the backend
    supports it; backends that do not may degrade to a fallback type or
    reject the Spec (return ``None``).
    """

    __slots__ = ("column",)

    def __init__(self, column: str):
        if not column:
            raise ValueError(f"{type(self).__name__} requires a column name")
        self.column = column


class JsonColumnSpec(ColumnTypeSpec):
    """Declare a column that should be a JSON column.

    Backends with native JSON support claim it and render the native JSON
    type; others may degrade to a text fallback or reject it.
    """

    __slots__ = ()


class GeneratedColumnSpec(DDLSpec):
    """A generated (computed) column.

    ``expression`` is a ``(dialect) -> BaseExpression`` factory (or a ready
    expression); ``stored`` selects STORED vs VIRTUAL where the backend
    distinguishes them. Backends without generated-column support reject it.
    """

    __slots__ = ("column", "expression", "stored")

    def __init__(
        self,
        column: str,
        expression: Union["Any", LazyPredicate],
        *,
        stored: bool = True,
    ):
        if not column:
            raise ValueError("GeneratedColumnSpec requires a column name")
        if expression is None:
            raise ValueError("GeneratedColumnSpec requires an expression")
        self.column = column
        self.expression = expression
        self.stored = stored


class ColumnPatchSpec(DDLSpec):
    """Internal marker for backend-built column patches.

    A backend's ``build_spec`` returns a ``ColumnPatchSpec`` instance to
    signal the generator that the Spec must be applied onto an existing
    ``ColumnDefinition`` (by name) rather than appended to a constraint or
    index list. The backend sets ``patched_data_type`` / ``generated`` and the
    generator merges them onto the matching column.
    """

    __slots__ = ("column", "patched_data_type", "generated_expression", "generated_type")

    def __init__(
        self,
        column: str,
        *,
        patched_data_type: "Any" = None,
        generated_expression: "Any" = None,
        generated_type: "Any" = None,
    ):
        self.column = column
        self.patched_data_type = patched_data_type
        self.generated_expression = generated_expression
        self.generated_type = generated_type