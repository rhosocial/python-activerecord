# src/rhosocial/activerecord/base/fields.py
"""
This module provides classes and functions related to field definitions and annotations.
"""

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
    from ..backend.expression.statements.ddl_table import (
        ReferentialAction,
    )
    from ..backend.expression.types import DataType
    from .ddl.attributes import ColumnAttribute


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


class UseSqlType:
    """Marker for ``Annotated[T, UseSqlType(*type_defs)]``.

    Instructs the DDL generator to use the supplied SQL ``DataType`` instance(s)
    when building a ``ColumnDefinition`` for this field, overriding the dialect's
    default type suggestion for ``T``.

    One or more ``DataType`` instances may be declared. At DDL-derivation time
    the first declared type the current dialect supports
    (``dialect.supports_data_types()``) is used; when none matches, derivation
    falls back to the canonical Python-type mapping and the dialect's
    ``suggested_data_types()`` (see ``base.ddl.types.ColumnTypeResolver``), and
    raises if that also yields nothing. Declaration order therefore expresses
    backend priority.

    Each instance may be a core **generic** type (portable — every backend
    renders it, natively or via the SQL-standard default) or a **backend-specific**
    type (``<Backend>*Type``, e.g. ``PostgresJsonBType``, which renders only on
    its owning backend). Backend-specific types render only on backends that
    register them; any other backend skips them (and falls back) rather than
    silently substituting a lossy form.

    Examples::

        # Generic — portable across backends
        status: Annotated[str, UseSqlType(VarCharType(length=50))]

        # Backend-priority: JSONB on PostgreSQL, JSON elsewhere, LONGTEXT on
        # MySQL < 5.7 (where JSON is unavailable)
        payload: Annotated[dict, UseSqlType(
            PostgresJsonBType(), JsonType(), MySQLLongTextType(),
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


class UseIndex:
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


class UseConstraint:
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
            deferrable=deferrable,
            initially_deferred=initially_deferred,
        )

    def __repr__(self) -> str:
        return f"UseConstraint({self.constraint.constraint_type.name})"


class UseColumnAttributes:
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
        from .ddl.attributes import ColumnAttribute

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


class UseComment:
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


class UseGeneratedColumn:
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