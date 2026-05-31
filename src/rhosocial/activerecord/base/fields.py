# src/rhosocial/activerecord/base/fields.py
"""
This module provides classes and functions related to field definitions and annotations.
"""

from typing import Any, Optional, Type, Union, TYPE_CHECKING

from ..backend.type_adapter import SQLTypeAdapter

if TYPE_CHECKING:
    from ..backend.expression.bases import BaseExpression, SQLDialectBase


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
                default_included=True,
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
        *,
        python_type: type = Any,
        default_included: bool = False,
        adapter: Optional[SQLTypeAdapter] = None,
    ):
        if callable(expression) and not hasattr(expression, "to_sql"):
            self._factory = expression
        else:
            _e = expression
            self._factory = lambda d: _e

        self.python_type = python_type
        self.default_included = default_included
        self.adapter = adapter
        self.field_name: Optional[str] = None
        self._source_id: Optional[int] = None

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance.__dict__.get(self.field_name, None)

    def resolve(self, dialect: "SQLDialectBase") -> "BaseExpression":
        return self._factory(dialect)
