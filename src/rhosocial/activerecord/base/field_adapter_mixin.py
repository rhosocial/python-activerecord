# src/rhosocial/activerecord/base/field_adapter_mixin.py
"""
This module provides a mixin for handling field-specific type adapters.
"""
from typing import ClassVar, Dict, Optional, Tuple, Type, Any, get_origin, get_args, Union

from ..backend.type_adapter import SQLTypeAdapter
from .fields import UseAdapter


class AdapterAnnotationHandler:
    """
    A feature handler for processing `@UseAdapter` annotations on model fields.
    """

    @staticmethod
    def handle(new_class: Type[Any]):
        """
        Parses annotations and attaches the `__field_adapters__` dictionary.
        """
        field_adapters: Dict[str, Tuple[SQLTypeAdapter, Type]] = {}
        if hasattr(new_class, '__annotations__'):
            for field_name, field_type in new_class.__annotations__.items():
                adapter_info = AdapterAnnotationHandler._extract_and_validate_adapter(field_name, field_type)
                if adapter_info:
                    field_adapters[field_name] = adapter_info

        setattr(new_class, '__field_adapters__', field_adapters)

    @staticmethod
    def _extract_and_validate_adapter(field_name: str, field_type: Any) -> Optional[Tuple[SQLTypeAdapter, Type]]:
        """
        Extracts an (SQLTypeAdapter, target_db_type) tuple from a field's type annotation
        if `Annotated` and `UseAdapter` are used. It also validates that at most one
        UseAdapter is specified.
        """
        # In Python 3.8, `Annotated` from `typing_extensions` can have identity
        # issues when compared with `is`. A structural check for `__metadata__`
        # is more robust. This is not necessary for Python 3.9+ where `Annotated`
        # is native and behaves consistently.
        if not (hasattr(field_type, '__origin__') and hasattr(field_type, '__args__') and hasattr(field_type, '__metadata__')):
            return None

        # Extract UseAdapter instance from __metadata__
        use_adapters_found = [arg for arg in field_type.__metadata__ if isinstance(arg, UseAdapter)]

        if len(use_adapters_found) > 1:
            raise TypeError(
                f"Invalid adapter definition on field '{field_name}'. "
                f"A field can have at most one UseAdapter specified, but {len(use_adapters_found)} were found."
            )

        if use_adapters_found:
            use_adapter_instance = use_adapters_found[0]
            # The base Python type is the first argument of the Annotated type
            target_py_type = field_type.__args__[0]
            
            # If the base Python type is Optional[T], extract T
            if get_origin(target_py_type) is Union:
                non_none_args = [arg for arg in get_args(target_py_type) if arg is not type(None)]
                if len(non_none_args) == 1:
                    target_py_type = non_none_args[0]

            return use_adapter_instance.adapter, use_adapter_instance.target_db_type

        return None


class FieldAdapterMixin:
    """
    Provides field-specific SQL type adapter functionality.

    It provides runtime methods and registers the AdapterAnnotationHandler
    to be run by the metaclass system at class creation time.
    """
    _feature_handlers = [AdapterAnnotationHandler]

    __field_adapters__: ClassVar[Dict[str, Tuple[SQLTypeAdapter, Type]]] = {}

    @classmethod
    def _get_adapter_for_field(cls, field_name: str) -> Optional[Tuple[SQLTypeAdapter, Type]]:
        """
        Retrieves a field-specific adapter and its target_db_type if one was
        defined in the model's annotations.

        Args:
            field_name: The name of the field to check for a custom adapter.

        Returns:
            A tuple of (SQLTypeAdapter instance, target_db_type) if found,
            otherwise None.
        """
        return cls.__field_adapters__.get(field_name)
