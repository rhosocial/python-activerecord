# src/rhosocial/activerecord/base/field_proxy.py
"""
Defines the FieldProxy, a descriptor that enables static, type-safe
access to model fields for building query expressions (e.g., `Model.c.field`).
"""
from typing import Any, Type, Optional, get_type_hints, Union

from .expression import Column
from ..backend.field import SQLField
from ..interface import IActiveRecord


class FieldProxy:
    """
    A descriptor that provides a way to reference model fields statically
    to build type-safe query expressions.

    It should be attached to a model as a `ClassVar`.

    Usage:
        class MyModel(IActiveRecord):
            c: ClassVar[FieldProxy] = FieldProxy()
            
            id: int
            name: str

        # This allows building expressions like:
        MyModel.query.where(MyModel.c.name == 'test')
    """
    _owner: Type[IActiveRecord]

    def __set_name__(self, owner: Type[IActiveRecord], name: str):
        # This is part of the descriptor protocol. It gets called when the
        # proxy is assigned to a class variable, giving us access to the model class.
        self._owner = owner

    def __getattribute__(self, name: str) -> Any:
        # Avoid recursion on our own attributes.
        if name in ('_owner', '__class__', '__set_name__'):
            return object.__getattribute__(self, name)

        # Here, `name` is the field being accessed (e.g., 'age' in `User.c.age`).
        model_class = self._owner
        
        # --- Field Type Resolution ---
        sql_field_class: Optional[Type[SQLField]] = None
        
        # TODO: Implement full 3-layer type resolution:
        # 1. Check for `Annotated[..., UseFieldType(...)]`
        # 2. Check backend's field type registry (this is what we implement now)
        # 3. Fallback to a global default.

        try:
            all_hints = get_type_hints(model_class)
            field_py_type = all_hints.get(name)

            if field_py_type:
                backend = model_class.get_backend()
                if backend:
                    registry = backend.get_field_type_registry()
                    if registry:
                        sql_field_class = registry.get_field_type(field_py_type)
        except Exception:
            # Fails gracefully if hints or backend are not available.
            sql_field_class = None

        # --- Column and Table Name Resolution ---
        # The column name used should respect any `UseColumn` annotations.
        if hasattr(model_class, 'get_column_name_for_field'):
            field_name = model_class.get_column_name_for_field(name)
        else:
            field_name = name 
        
        # The table name should come from the model's metadata.
        if hasattr(model_class, 'table_name'):
            table_name = model_class.table_name()
        else:
            table_name = getattr(self._owner, '__tablename__', self._owner.__name__.lower() + 's')

        # --- Instantiate and Return Expression ---
        if sql_field_class:
            # Found a specific SQLField type (e.g., IntegerField). Instantiate it.
            return sql_field_class(name=field_name, table=table_name)
        
        # Fallback to the generic Column expression if no specific type was found.
        return Column(name=field_name, table=table_name)
