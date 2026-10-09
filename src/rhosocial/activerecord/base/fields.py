# src/rhosocial/activerecord/base/fields.py
"""
This module provides classes and functions related to field definitions and annotations.
"""

import enum
import types
import typing
from typing import Any, Callable, List, Optional, Type, Union, TYPE_CHECKING

from ..backend.expression.statements.ddl_table import (
    ColumnConstraint,
    ColumnConstraintType,
    GeneratedColumnExpression,
    IndexDefinition,
)
from ..backend.type_adapter import SQLTypeAdapter

if TYPE_CHECKING:
    from ..backend.expression.bases import BaseExpression, SQLDialectBase, SQLPredicate
    from ..backend.expression.column_types import ColumnBase
    from ..backend.expression.statements.ddl_table import (
        ReferentialAction,
    )
    from ..backend.expression.types import DataType
    from .ddl import ColumnAttribute


class DDLAnnotation:
    """Base marker for field annotations that affect DDL generation.

    Core markers and backend-owned markers use this common base so the DDL
    metadata collector can distinguish DDL declarations from unrelated
    annotation metadata.  A backend marker must be accompanied by an explicit
    handler registered in the model's ``_feature_handlers`` collection.
    """


class UseColumn:
    """
    A marker class used within `typing.Annotated` to specify a custom column name
    for a model field that differs from the Python field name.

    Example:
        from typing import Annotated

        class User(ActiveRecord):
            # Python field name is 'user_id', but database column is 'id'
            user_id: Annotated[int, UseColumn("id")]

            # Python field name is 'email_address', database column is 'email'
            email_address: Annotated[str, UseColumn("email")]

    Notes:
        - Each field can have at most one UseColumn annotation
        - Column name validation happens at metaclass time for single field
        - Cross-field uniqueness validation happens at model initialization
    """

    def __init__(self, column_name: str):
        """
        Initializes the UseColumn marker.

        Args:
            column_name: The database column name to use for this field.
                        Must be a non-empty string.

        Raises:
            TypeError: If column_name is not a string.
            ValueError: If column_name is empty.
        """
        if not isinstance(column_name, str):
            raise TypeError(
                f"Invalid type for column_name. Expected str, but received type {type(column_name).__name__}."
            )
        if not column_name.strip():
            raise ValueError("Column name cannot be empty.")
        self.column_name = column_name.strip()


class UseAdapter:
    """
    A marker class used within `typing.Annotated` to specify a concrete
    SQLTypeAdapter and its target driver-compatible type for a model field.

    Example:
        from datetime import datetime

        class User(ActiveRecord):
            # This field will use MyCustomAdapter to convert datetime to str
            custom_field: Annotated[
                datetime,
                UseAdapter(MyCustomAdapter(), str)
            ]
    """

    def __init__(self, adapter: SQLTypeAdapter, target_db_type: Type):
        """
        Initializes the UseAdapter marker.

        Args:
            adapter: An instance of a class that inherits from SQLTypeAdapter.
            target_db_type: The Python type that the adapter will convert the value to,
                          which must be compatible with the database driver.

        Raises:
            TypeError: If the provided adapter is not an instance of SQLTypeAdapter.
        """
        if not isinstance(adapter, SQLTypeAdapter):
            raise TypeError(
                f"Invalid type for adapter. Expected an instance of SQLTypeAdapter, "
                f"but received type {type(adapter).__name__}."
            )
        self.adapter = adapter
        self.target_db_type = target_db_type


class UseSqlType(DDLAnnotation):
    """Marker for ``Annotated[T, UseSqlType(*type_defs)]``.

    Declares the SQL ``DataType`` candidates associated with a model field.
    ``DDLSource`` exposes the candidates in declaration order; dialect binding,
    capability selection, and fallback policy belong to external consumers.

    Each instance may be a core generic type or a backend-specific type such as
    ``PostgresUUIDType``. Declaration order expresses backend priority without
    coupling the declaration layer to any particular dialect.

    Examples::

        # Generic — portable across backends
        status: Annotated[str, UseSqlType(VarCharType(length=50))]

        # Backend-priority: PostgreSQL UUID, generic text elsewhere
        identifier: Annotated[str, UseSqlType(
            PostgresUUIDType(), TextType(),
        )]

    Attributes:
        data_types: Tuple of the declared ``DataType`` instances (deduplicated,
            first occurrence wins), in declaration order.
        data_type: The first (primary) ``DataType`` instance — kept as a
            convenience alias for single-type use.
    """

    def __init__(self, *data_types: "DataType"):
        from ..backend.expression.types import DataType

        if not data_types:
            raise TypeError(
                "UseSqlType requires at least one DataType instance, e.g. "
                "UseSqlType(VarCharType(length=50))."
            )
        for t in data_types:
            if not isinstance(t, DataType) or type(t) is DataType:
                # Candidate types are restricted to DataType subclasses: only
                # a derived class carries the semantics of a concrete type,
                # the abstract base itself names nothing (Gate 0, §5.1).
                raise TypeError(
                    f"UseSqlType expects one or more DataType subclasses "
                    f"(not {type(t).__name__} itself), got "
                    f"{type(t).__name__}. Per-dialect string-keyed mappings are "
                    f"not supported: use a generic type (each backend resolves "
                    f"it natively), a backend-specific type, or several types "
                    f"in declaration order."
                )
        # Deduplicate by value-object equality; keep first occurrence.
        seen: list = []
        for t in data_types:
            if t not in seen:
                seen.append(t)
        self.data_types: tuple = tuple(seen)
        self.data_type = self.data_types[0]

    def __repr__(self) -> str:
        return f"UseSqlType({', '.join(repr(t) for t in self.data_types)})"


class UseColumnType:
    """Marker for ``Annotated[T, UseColumnType(*column_classes)]``.

    Declares which **column class** (the operation set a value offers) a model
    field's expressions use, instead of letting the backend suggest one. It is
    the column-side twin of :class:`UseSqlType`, and the two are **strictly
    independent**:

    * ``UseSqlType`` serves the DDL only -- which ``DataType`` the column is
      created with -- and takes no part in CRUD or expression rendering;
    * ``UseColumnType`` serves the column operations only -- what
      ``Model.c.<field>`` can do -- and never influences DDL.

    A model may declare either, both, or neither, and the framework does not
    check them against each other. A field may say ``age: int`` with
    ``UseSqlType(VarCharType())`` or ``UseColumnType(StringColumn())`` and both
    are honoured: the first decides the stored type, the second decides the
    operations, and neither is inferred from the other. This is deliberate --
    "which operations does this value support" and "how is it stored" are
    different questions, and a model that wants an unusual answer to either one
    should be able to give it without having to lie about the other.

    It is **not** a :class:`DDLAnnotation`: the DDL collector must not see it,
    or the strict independence above would be one refactor away from being
    false.

    Exactly one column class may be declared for now. The signature is variadic
    (``UseSqlType`` is too, and for the same reason: declaration order is the
    candidate order) but multi-candidate selection needs the operation-capability
    declaration to answer "does this backend cover every operation of this
    class", which does not exist yet -- so rather than silently taking the first
    candidate and pretending the negotiation happened, a multi-candidate
    declaration is refused here, at the point of the mistake, and says what it
    is waiting for.

    Examples::

        # A plain text value that is stored as something other than text
        label: Annotated[str, UseColumnType(StringColumn)]
        blob: Annotated[bytes, UseColumnType(BinaryColumn)]

        # Both sides declared independently: stored as an integer, offered as
        # arithmetic on a whole number -- same thing here, and deliberately not
        # cross-checked
        qty: Annotated[int, UseSqlType(IntType()), UseColumnType(IntegerColumn)]

    Raises:
        TypeError: No column class was given, or one of them is not a
            :class:`~...backend.expression.column_types.ColumnBase` subclass.
    """

    def __init__(self, *column_classes: Type["ColumnBase"]):
        from ..backend.expression.column_types import ColumnBase

        if not column_classes:
            raise TypeError(
                "UseColumnType requires at least one ColumnBase subclass, "
                "e.g. UseColumnType(StringColumn)."
            )
        for column_class in column_classes:
            if not (isinstance(column_class, type) and issubclass(column_class, ColumnBase)):
                # Class objects only: a column class is a type, never an
                # instance. One that carried state would make the value a
                # declaration rather than a class, and the resolution layer
                # would have no way to hand the same class to every expression.
                raise TypeError(
                    f"UseColumnType expects ColumnBase subclasses (classes "
                    f"derived from ColumnBase), got "
                    f"{column_class!r}. Column classes name operations, not "
                    f"values, so pass the class itself rather than an "
                    f"instance of it."
                )
        if len(column_classes) > 1:
            # Refused rather than resolved first-wins. Choosing among several
            # candidates is a negotiation with the backend's capability
            # declaration ("does this dialect cover every operation of this
            # class"), and taking the first without asking would make the
            # declaration a lie the caller cannot see. See the multi-candidate
            # ruling in column-type-refactor.md (议题 2).
            raise TypeError(
                f"UseColumnType was given {len(column_classes)} column "
                f"classes ({', '.join(c.__name__ for c in column_classes)}), "
                f"but multi-candidate resolution needs the capability "
                f"declaration mechanism, which does not exist yet: choosing "
                f"among candidates means asking the dialect whether it covers "
                f"every operation of a class, and there is no answer to read "
                f"yet. Declare a single column class for now; when the "
                f"capability declaration lands, this signature keeps its "
                f"variadic shape and the candidates will be ordered by "
                f"declaration order as UseSqlType's are."
            )
        self.column_classes: tuple = tuple(column_classes)
        #: The declared class — a convenience alias, since only one may be
        #: declared. Present for the same reason as ``UseSqlType.data_type``:
        #: the single-candidate case is what readers ask for, and it is what
        #: the resolution layer reads.
        self.column_class: Type[ColumnBase] = self.column_classes[0]

    def __repr__(self) -> str:
        return f"UseColumnType({', '.join(c.__name__ for c in self.column_classes)})"


def declared_column_type(metadata: Any) -> Optional[UseColumnType]:
    """The :class:`UseColumnType` among an ``Annotated`` field's markers, if any.

    A reader and nothing else: it looks at what pydantic collected and returns
    the declaration, or ``None``. It does not resolve anything. Choosing the
    column class is the model layer's lookup (:func:`resolve_column_class`),
    and the marker being here at all is only about *where pydantic puts it*:
    ``FieldInfo.annotation`` is the bare type with ``Annotated`` already split
    off, and the markers live in ``FieldInfo.metadata``. A model layer that
    looked at the annotation directly would not find this declaration at all,
    which is why the read is explicit here rather than buried in resolution.

    Args:
        metadata: Pydantic's ``FieldInfo.metadata`` -- the marker list an
            ``Annotated`` field was decomposed into.

    Returns:
        The declared :class:`UseColumnType`, or ``None``.

    Raises:
        TypeError: More than one declaration on the same field. A field says
        once what its column class is; two markers would mean picking one
            silently, and the caller cannot see which was chosen.
    """
    found = [item for item in (metadata or ()) if isinstance(item, UseColumnType)]
    if len(found) > 1:
        raise TypeError(
            f"{len(found)} UseColumnType declarations on a single field. A field "
            f"declares the column class it uses once; a model that wants a "
            f"different one declares it on a different model."
        )
    return found[0] if found else None


class ColumnTypeResolutionError(TypeError):
    """No column class could be chosen for an annotation, and none may be guessed.

    Raised by :func:`resolve_column_class` when the annotation is outside the
    tables a dialect answers, or when the dialect answered ``None`` for it.
    A ``TypeError`` because the wrong *thing* was asked for: a field the
    framework cannot type is a mistake in the model, and finding it where the
    field is read costs nothing next to a driver error naming a column.
    """


def strip_annotation(annotation: Any) -> Any:
    """Peel ``Annotated`` and ``Optional`` off *annotation*.

    ``Annotated[str, UseColumn("name")]`` -> ``str``; ``Optional[dict]`` ->
    ``dict``. Declaration markers are not consulted here: they describe
    storage, constraints and the operation set, not the Python value.
    """
    # `typing.get_origin(Annotated[...])` returns the `Annotated` special form
    # on 3.9+, but on 3.8 `typing` has no `Annotated` attribute at all, so the
    # identity check raises AttributeError. The presence of `__metadata__` is
    # how the runtime marks an annotated alias on every supported version.
    while hasattr(annotation, "__metadata__"):
        annotation = typing.get_args(annotation)[0]

    origin = typing.get_origin(annotation)
    if origin is typing.Union or origin is getattr(types, "UnionType", None):
        members = [a for a in typing.get_args(annotation) if a is not type(None)]
        if len(members) == 1:
            return strip_annotation(members[0])
    return annotation


def resolve_column_class(
    dialect: "SQLDialectBase",
    annotation: Any,
    declared: Optional[UseColumnType] = None,
) -> Type["ColumnBase"]:
    """The column class to use for *annotation* on *dialect*.

    The model layer's lookup, in order:

    ① an explicit ``UseColumnType`` (*declared*) answers without reading any
       table -- naming a column class is what makes it the escape hatch for an
       annotation no table can classify;
    ② the common-type table (``dialect.suggested_column_types()``), keyed by
       the normalised entry: exact match, then ``enum.Enum``, then a subclass
       walk over the table's keys in their declared order, then the pydantic
       bridge;
    ③ the backend's extra table (``dialect.suggested_extra_column_types()``),
       keyed by the annotation itself;
    ④ neither -> :class:`ColumnTypeResolutionError`, naming what is missing.
    """
    if declared is not None:
        return declared.column_class

    table = dialect.suggested_column_types()
    entry = _column_entry_for(annotation, table)

    if entry is not None:
        if entry not in table:
            # Reachable only through the enum branch: the subclass walk can
            # only return a key the table already has.
            raise ColumnTypeResolutionError(
                f"{type(dialect).__name__}.suggested_column_types() does not "
                f"answer for {_entry_name(entry)}, which is one of the common "
                f"types. Every entry must be answered -- with a column class, "
                f"or with None when the backend genuinely has no workaround."
            )
        suggested = table[entry]
        if suggested is None:
            raise ColumnTypeResolutionError(
                f"{type(dialect).__name__} has no column class for "
                f"{_entry_name(entry)}. Declare one explicitly with "
                f"UseColumnType(SomeColumn) if this field's value supports "
                f"operations this backend has no class for."
            )
        _require_column_class(type(dialect).__name__, "suggested_column_types", entry, suggested)
        return suggested

    extras = dialect.suggested_extra_column_types()
    suggested = extras.get(strip_annotation(annotation))
    if suggested is not None:
        _require_column_class(
            type(dialect).__name__, "suggested_extra_column_types", annotation, suggested
        )
        return suggested

    raise ColumnTypeResolutionError(
        f"Cannot choose a column class for {_describe_annotation(annotation)}: "
        f"it is not one of the common types and no UseColumnType declares one. "
        f"The types this backend answers are: "
        f"{', '.join(_entry_name(key) for key in table)}. Declare the "
        f"operations this field's value carries with UseColumnType(SomeColumn), "
        f"or annotate the field with one of the types above."
    )


def _column_entry_for(annotation: Any, keys: Any) -> Optional[Any]:
    """The table key *annotation* normalises to, or ``None``.

    Three rules and the pydantic bridge: exact key match, ``enum.Enum``
    subclass, then a subclass walk in *keys* order (``class MyStr(str)`` ->
    ``str``). The bridge is consulted last, so it can turn a failure into an
    answer and can never change an answer that already existed; its result is
    re-checked against the same keys.
    """
    peeled = strip_annotation(annotation)
    if peeled in keys:
        return peeled

    if isinstance(peeled, type):
        if issubclass(peeled, enum.Enum):
            # Checked before the walk: an enum that also subclasses something
            # else (`class Weekday(int, Enum)`) must stay an enum.
            return enum.Enum
        for key in keys:
            if isinstance(key, type) and key is not peeled and issubclass(peeled, key):
                return key

    from .pydantic_fields import normalize_pydantic_annotation

    bridged = normalize_pydantic_annotation(peeled)
    if bridged is not None and bridged in keys:
        return bridged
    return None


def _require_column_class(dialect_name: str, table: str, key: Any, suggested: Any) -> None:
    from ..backend.expression.column_types import ColumnBase

    if not (isinstance(suggested, type) and issubclass(suggested, ColumnBase)):
        raise ColumnTypeResolutionError(
            f"{dialect_name}.{table}()[{_entry_name(key)}] is {suggested!r}, "
            f"which is not a ColumnBase subclass."
        )


def _entry_name(entry: Any) -> str:
    module = getattr(entry, "__module__", None)
    name = getattr(entry, "__name__", None) or repr(entry)
    if module and module not in ("builtins",):
        return f"{module}.{name}"
    return name


def _describe_annotation(annotation: Any) -> str:
    name = getattr(annotation, "__name__", None) or repr(annotation)
    return f"{name!r} (the annotation {annotation!r})"


class UseIndex(DDLAnnotation):
    """Marker for ``Annotated[T, UseIndex(name, ...)]``.

    Declares a single-column index that the DDL generator will emit inline
    with the CREATE TABLE statement (or as a separate CREATE INDEX for backends
    that do not support inline indexes).

    For multi-column (composite) indexes, declare ``__table_indexes__`` on the model
    class instead.

    Example::

        email:    Annotated[str, UseIndex("idx_email", unique=True)]
        country:  Annotated[str, UseIndex("idx_country")]
    """

    def __init__(
        self,
        name: str,
        *,
        unique: bool = False,
        type: Optional[str] = None,
        partial_condition: Optional[Union["SQLPredicate", "Callable"]] = None,
        include_columns: Optional[List[str]] = None,
        if_not_exists: Optional[bool] = None,
        tablespace: Optional[str] = None,
        if_exists: Optional[bool] = None,
        concurrent: Optional[bool] = None,
    ):
        if not name:
            raise ValueError("UseIndex requires a non-empty index name.")
        self.name = name
        self.unique = unique
        self.type = type
        # May be a ready SQLPredicate or a lazy ``(dialect) -> SQLPredicate``
        # factory, resolved by the generator at DDL-build time.
        self.partial_condition = partial_condition
        self.include_columns = include_columns
        # Statement-level options (§5.16): ``if_not_exists`` (create path),
        # ``tablespace`` (create path), ``if_exists`` (drop path) and
        # ``concurrent`` (create/drop shared). ``None`` means "not explicitly
        # declared" — an explicit declaration wins over entry-level parameters.
        self.if_not_exists = if_not_exists
        self.tablespace = tablespace
        self.if_exists = if_exists
        self.concurrent = concurrent

    def to_index_definition(self, column_name: str, dialect: "SQLDialectBase") -> "IndexDefinition":
        """Build an IndexDefinition that references *column_name*.

        The dialect is supplied by the DDL generator at build time.
        """
        return IndexDefinition(dialect,
            name=self.name,
            columns=[column_name],
            unique=self.unique,
            type=self.type,
            partial_condition=self.partial_condition,
            include_columns=self.include_columns,
            if_not_exists=self.if_not_exists,
            tablespace=self.tablespace,
            if_exists=self.if_exists,
            concurrent=self.concurrent,
        )

    def __repr__(self) -> str:
        return (
            f"UseIndex({self.name!r}, unique={self.unique!r}, type={self.type!r})"
        )


class UseConstraint(DDLAnnotation):
    """Marker for ``Annotated[T, UseConstraint(constraint_type, ...)]``.

    Declares a constraint applied directly to the annotated column in the
    generated CREATE TABLE statement.

    Rejected constraint types (declaration raises immediately):

    - ``PRIMARY_KEY`` — the **only** constraint the marker refuses on
      semantic grounds: the primary key has a single source, the
      ``__primary_key__`` constant (accessed through ``primary_key()``);
      a single-column PK lands on the column, a composite PK becomes a
      table-level constraint.
    - ``IDENTITY`` / ``COLLATE`` — migrated to the column-attribute channel:
      declare ``UseColumnAttributes(IdentityAttribute(...))`` or
      ``UseColumnAttributes(CollationAttribute(...))`` instead.

    Accepted constraint types: NOT NULL / UNIQUE / CHECK / FOREIGN KEY /
    DEFAULT.

    For table-level constraints (CHECK spanning multiple columns, composite
    UNIQUE, composite FOREIGN KEY), declare ``__table_constraints__`` on the
    model class instead.

    Example::

        # Column-level CHECK (SQL-standard, generic)
        status: Annotated[str, UseConstraint(
            ColumnConstraintType.CHECK,
            check_condition=lambda d: Column(d, "status").in_(["open", "paid"]),
        )]
    """

    def __init__(
        self,
        constraint_type: "ColumnConstraintType",
        *,
        name: Optional[str] = None,
        check_condition: Optional[Union["SQLPredicate", "Callable"]] = None,
        foreign_key_reference: Optional[tuple] = None,
        default_value: Any = None,
        is_auto_increment: bool = False,
        on_delete: Optional["ReferentialAction"] = None,
        on_update: Optional["ReferentialAction"] = None,
        deferrable: Optional[bool] = None,
        initially_deferred: Optional[bool] = None,
        enforced: Optional[bool] = None,
    ):
        # check_condition may be a ready SQLPredicate or a lazy
        # ``(dialect) -> SQLPredicate`` factory; the generator resolves it.
        # The marker is constructed at model-declaration time (no dialect
        # yet) — the constraint node defers binding and the DDL generator
        # binds it through the dialect setter.
        if constraint_type == ColumnConstraintType.PRIMARY_KEY:
            raise ValueError(
                "UseConstraint does not accept PRIMARY_KEY: the primary key "
                "has a single source, the __primary_key__ constant (or a "
                "primary_key() override). A single-column PK lands on the "
                "column automatically; a composite PK becomes a table-level "
                "constraint."
            )
        self.constraint = ColumnConstraint(None,
            constraint_type=constraint_type,
            name=name,
            check_condition=check_condition,
            foreign_key_reference=foreign_key_reference,
            default_value=default_value,
            is_auto_increment=is_auto_increment,
            on_delete=on_delete,
            on_update=on_update,
            # The AR-layer marker keeps its tri-state until the AR layer's
            # exposure of the split is decided (out of scope for this round);
            # translate it to the expression layer's two parameters.
            deferrable=deferrable is True,
            not_deferrable=deferrable is False,
            initially_deferred=initially_deferred is True,
            initially_immediate=initially_deferred is False,
            enforced=enforced is True,
            not_enforced=enforced is False,
        )

    def __repr__(self) -> str:
        return f"UseConstraint({self.constraint.constraint_type.name})"


class UseColumnAttributes(DDLAnnotation):
    """Marker for ``Annotated[T, UseColumnAttributes(attr, ...)]``.

    Declares one or more dialect-free :class:`ColumnAttribute` objects
    (identity, collation, character set, …). The AR layer collects them per
    column and hands the list to the backend dialect, which selects the
    applicable attributes and renders them in the column definition.

    Candidate types are restricted to :class:`ColumnAttribute` subclasses
    (Gate 0): each attribute kind carries its own semantics, and the three
    families (constraints / indexes / attributes) are mutually exclusive by
    design — the same semantic is never carried twice.
    """

    def __init__(self, *attributes: "ColumnAttribute"):
        from .ddl import ColumnAttribute

        if not attributes:
            raise TypeError(
                "UseColumnAttributes requires at least one ColumnAttribute "
                "instance, e.g. UseColumnAttributes(IdentityAttribute())."
            )
        seen: list = []
        for attr in attributes:
            if not isinstance(attr, ColumnAttribute):
                raise TypeError(
                    f"UseColumnAttributes expects ColumnAttribute instances, "
                    f"got {type(attr).__name__}. Constraints are declared "
                    f"through UseConstraint, indexes through UseIndex."
                )
            if attr not in seen:
                seen.append(attr)
        self.attributes: list = seen

    def __repr__(self) -> str:
        kinds = ", ".join(type(attr).__name__ for attr in self.attributes)
        return f"UseColumnAttributes({kinds})"


class UseComment(DDLAnnotation):
    """Marker for ``Annotated[T, UseComment("...")]``.

    Declares the column comment rendered with the column definition (on
    backends that support column comments). Equivalent to overriding
    :meth:`column_comment`, but declarative.
    """

    def __init__(self, comment: str):
        if not isinstance(comment, str):
            raise TypeError(
                f"UseComment expects a str, got {type(comment).__name__}."
            )
        if not comment.strip():
            raise ValueError("UseComment requires a non-empty comment.")
        self.comment = comment

    def __repr__(self) -> str:
        return f"UseComment({self.comment!r})"


class UseGeneratedColumn(DDLAnnotation):
    """Marker for ``Annotated[T, UseGeneratedColumn(expr)]``.

    Declares a generated (computed) column whose value the database derives
    from *expr*. Equivalent to overriding :meth:`generated_column`, but
    declarative.

    *expr* is either a ready :class:`GeneratedColumnExpression` or a lazy
    ``(dialect) -> GeneratedColumnExpression`` factory. A factory is the
    usual form: the annotation is evaluated at class-definition time, before
    any dialect exists, so a generated column that references other columns
    must build its expression once the deriver supplies the dialect.
    """

    def __init__(self, expression: Any):
        if not callable(expression) and not isinstance(expression, GeneratedColumnExpression):
            raise TypeError(
                "UseGeneratedColumn expects a GeneratedColumnExpression or a "
                "(dialect) -> GeneratedColumnExpression factory, got "
                f"{type(expression).__name__}."
            )
        self.expression = expression

    def __repr__(self) -> str:
        return f"UseGeneratedColumn({self.expression!r})"


class DerivedField:
    """
    A marker/descriptor for declaring derived (computed) fields on ActiveRecord models.

    Derived fields are non-column fields whose values are computed by the database
    at query time. They are opt-in via the `derived` parameter on find_all/find_one.
    At query time the expression is injected into SELECT with an alias, and the
    result is mapped back to the instance by that alias.

    Derived fields are not tracked by Pydantic (declared as ClassVar) nor by dirty
    field tracking, and their values are read-only on instances.

    Expression definition approaches:

    1. Field proxy (recommended): reference columns via Model.c, which automatically
       injects the dialect. No manual dialect handling needed.

         class Product(ActiveRecord):
             c: ClassVar[FieldProxy] = FieldProxy()
             price: float
             quantity: int
             discounted: ClassVar[Annotated[float, DerivedField(
                 lambda d: Product.c.price * Literal(d, 0.9),
             )]]

    2. Manual Column construction: use the dialect parameter (d) passed to the
       factory to build expressions directly.

         class Product(ActiveRecord):
             price: float
             total_value: ClassVar[Annotated[float, DerivedField(
                 lambda d: Column(d, "price") * Column(d, "quantity"),
             )]]

        If you need to build an expression outside the lambda, obtain the dialect
        from the backend:

         dialect = Product.backend().dialect
         expr = Column(dialect, "price") * Literal(dialect, 2)
    """

    def __init__(
        self,
        expression: "Union[BaseExpression, Any]",
    ):
        if callable(expression) and not hasattr(expression, "to_sql"):
            self._factory = expression
        else:
            _e = expression
            self._factory = lambda d: _e

        self.python_type: type = Any
        self.adapter: Optional[SQLTypeAdapter] = None
        self.column_name: Optional[str] = None
        self.field_name: Optional[str] = None
        self._source_id: Optional[int] = None

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance.__dict__.get(self.field_name, None)

    def resolve(self, dialect: "SQLDialectBase") -> "BaseExpression":
        return self._factory(dialect)