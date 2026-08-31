# src/rhosocial/activerecord/base/fields.py
"""
This module provides classes and functions related to field definitions and annotations.
"""

from typing import Any, Dict, List, Optional, Type, Union, TYPE_CHECKING

from ..backend.expression.statements.ddl_table import (
    ColumnConstraint,
    ColumnConstraintType,
    IndexDefinition,
)
from ..backend.type_adapter import SQLTypeAdapter

if TYPE_CHECKING:
    from ..backend.expression.bases import BaseExpression, SQLDialectBase, SQLPredicate
    from ..backend.expression.statements.ddl_table import (
        ReferentialAction,
    )
    from ..backend.expression.types import DataType


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
    """Marker for ``Annotated[T, UseSqlType(type_def)]``.

    Instructs the DDL generator to use the supplied SQL ``DataType`` instance
    when building a ``ColumnDefinition`` for this field, overriding the dialect's
    default type suggestion for ``T``.

    Two forms are accepted:

    1. Single type (applies to all backends)::

        status: Annotated[str, UseSqlType(VarCharType(length=50))]

    2. Per-dialect selectable (the ``default`` key is the fallback)::

        metadata: Annotated[dict, UseSqlType({
            "postgres": JsonBType(),
            "mysql": JsonType(),
            "default": TextType(),
        })]

    Attributes:
        data_type: The primary ``DataType`` instance (or the ``default`` entry
            from the per-dialect form).
        dialect_types: ``{dialect_name: DataType}`` mapping for backends whose
            type differs from the primary. Keys are dialect names used by
            ``SQLDialectBase.name`` (e.g. ``"sqlite"``, ``"mysql"``,
            ``"postgres"``).
    """

    def __init__(
        self,
        data_type: Union["DataType", Dict[str, "DataType"]],
    ):
        if isinstance(data_type, dict):
            mapping = dict(data_type)
            self.dialect_types: Dict[str, "DataType"] = mapping
            self.data_type: Optional["DataType"] = mapping.pop("default", None)
            if self.data_type is None:
                raise ValueError(
                    "UseSqlType per-dialect mapping must include a 'default' "
                    "fallback key, e.g. UseSqlType({'default': TextType()})"
                )
        else:
            self.data_type = data_type
            self.dialect_types = {}

    def resolve(self, dialect_name: str) -> Optional["DataType"]:
        """Return the DataType for *dialect_name*, falling back to ``data_type``.

        The lookup is case-insensitive so users may write ``"postgres"`` or
        ``"PostgreSQL"`` and still match the dialect's ``.name`` attribute.
        """
        if not dialect_name:
            return self.data_type
        key = dialect_name.lower()
        for k, v in self.dialect_types.items():
            if k.lower() == key:
                return v
        return self.data_type

    def __repr__(self) -> str:
        if self.dialect_types:
            return f"UseSqlType({self.dialect_types!r}, default={self.data_type!r})"
        return f"UseSqlType({self.data_type!r})"


class UseIndex:
    """Marker for ``Annotated[T, UseIndex(name, ...)]``.

    Declares a single-column index that the DDL generator will emit inline
    with the CREATE TABLE statement (or as a separate CREATE INDEX for backends
    that do not support inline indexes).

    For multi-column (composite) indexes, declare ``__indexes__`` on the model
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
        partial_condition: Optional["SQLPredicate"] = None,
        include_columns: Optional[List[str]] = None,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        if not name:
            raise ValueError("UseIndex requires a non-empty index name.")
        self.name = name
        self.unique = unique
        self.type = type
        self.partial_condition = partial_condition
        self.include_columns = include_columns
        self.dialect_options = dialect_options

    def to_index_definition(self, column_name: str) -> "IndexDefinition":
        """Build an IndexDefinition that references *column_name*."""
        return IndexDefinition(
            name=self.name,
            columns=[column_name],
            unique=self.unique,
            type=self.type,
            partial_condition=self.partial_condition,
            include_columns=self.include_columns,
            dialect_options=self.dialect_options,
        )

    def __repr__(self) -> str:
        return (
            f"UseIndex({self.name!r}, unique={self.unique!r}, type={self.type!r})"
        )


class UseConstraint:
    """Marker for ``Annotated[T, UseConstraint(constraint_type, ...)]``.

    Declares a constraint applied directly to the annotated column in the
    generated CREATE TABLE statement.

    For table-level constraints (CHECK spanning multiple columns, composite
    UNIQUE, composite FOREIGN KEY), declare ``__constraints__`` on the model
    class instead.

    Example::

        # Column-level COLLATE
        name: Annotated[str, UseConstraint(ColumnConstraintType.COLLATE,
                                            collation="utf8mb4_unicode_ci")]

        # Column-level CHARACTER SET (MySQL/MariaDB)
        name: Annotated[str, UseConstraint(ColumnConstraintType.CHARACTER_SET,
                                            character_set="utf8mb4")]
    """

    def __init__(
        self,
        constraint_type: "ColumnConstraintType",
        *,
        name: Optional[str] = None,
        check_condition: Optional["SQLPredicate"] = None,
        foreign_key_reference: Optional[tuple] = None,
        default_value: Any = None,
        is_auto_increment: bool = False,
        on_delete: Optional["ReferentialAction"] = None,
        on_update: Optional["ReferentialAction"] = None,
        deferrable: Optional[bool] = None,
        initially_deferred: Optional[bool] = None,
        dialect_options: Optional[Dict[str, Any]] = None,
        character_set: Optional[str] = None,
        collation: Optional[str] = None,
    ):
        self.constraint = ColumnConstraint(
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
            dialect_options=dialect_options,
            character_set=character_set,
            collation=collation,
        )

    def __repr__(self) -> str:
        return f"UseConstraint({self.constraint.constraint_type.name})"


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