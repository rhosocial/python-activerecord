# src/rhosocial/activerecord/base/metaclass.py
"""
This module defines the metaclass for the ActiveRecord base model.
"""
from typing import get_origin, get_args, Dict, Any, Tuple, Type

from pydantic._internal._model_construction import ModelMetaclass

from ..backend.type_adapter import SQLTypeAdapter
from .fields import UseAdapter


class ActiveRecordMetaclass(ModelMetaclass):
    """
    A custom metaclass for ActiveRecord models.

    This metaclass extends Pydantic's model construction to parse and
    validate `UseAdapter` annotations on model fields during class creation.
    It attaches a `__field_adapters__` mapping to the class, which is used
    later by the backend to select type adapters.
    """
    def __new__(cls, name, bases, namespace, **kwargs):
        """
        Constructs the new class, processing field annotations after the
        Pydantic metaclass has finished its work.
        """
        # First, let the Pydantic metaclass create the class object.
        new_class = super().__new__(cls, name, bases, namespace, **kwargs)

        # Now, inspect the fully-formed annotations on the new class.
        field_adapters: Dict[str, Tuple[SQLTypeAdapter, Type]] = {}
        if hasattr(new_class, '__annotations__'):
            for field_name, field_type in new_class.__annotations__.items():
                adapter_info = cls._extract_and_validate_adapter(field_name, field_type)
                if adapter_info:
                    field_adapters[field_name] = adapter_info
        
        # Use setattr to attach the processed adapters to the created class.
        setattr(new_class, '__field_adapters__', field_adapters)
        
        return new_class

    @classmethod
    def _extract_and_validate_adapter(cls, field_name: str, field_type: Any) -> Optional[Tuple[SQLTypeAdapter, Type]]:
        """
        Extracts an (SQLTypeAdapter, target_db_type) tuple from a field's type annotation
        if `Annotated` and `UseAdapter` are used. It also validates that at most one
        UseAdapter is specified.
        """
        # In Python 3.8, get_origin(Annotated[...]) is just Annotated.
        # In Python 3.9+, it's typing.Annotated.
        try:
            from typing import Annotated
        except ImportError:
            # For Python 3.8, Annotated is not in typing, handle accordingly if needed
            Annotated = None

        if get_origin(field_type) is not Annotated:
            return None

        # Arguments of Annotated are (OriginalType, Metadata1, Metadata2, ...)
        type_args = get_args(field_type)
        use_adapters_found = [
            arg for arg in type_args[1:] if isinstance(arg, UseAdapter)
        ]

        # Validation: Ensure at most one UseAdapter is defined per field.
        if len(use_adapters_found) > 1:
            raise TypeError(
                f"Invalid adapter definition on field '{field_name}'. "
                f"A field can have at most one UseAdapter specified, but {len(use_adapters_found)} were found."
            )

        if use_adapters_found:
            use_adapter_instance = use_adapters_found[0]
            return (use_adapter_instance.adapter, use_adapter_instance.target_db_type)
        
        return None
