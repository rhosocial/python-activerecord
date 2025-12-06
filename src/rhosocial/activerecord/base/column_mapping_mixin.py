# src/rhosocial/activerecord/base/column_mapping_mixin.py
"""
This module provides a mixin for handling field-to-column name mappings.
"""
from typing import ClassVar, Dict, Type, Any

from .fields import UseColumn


class ColumnAnnotationHandler:
    """
    A feature handler for processing `@UseColumn` annotations on model fields.
    """

    @staticmethod
    def handle(new_class: Type[Any]):
        """
        Parses annotations and attaches the `__column_mappings__` dictionary.
        """
        column_mappings: Dict[str, str] = {}
        if hasattr(new_class, '__annotations__'):
            for field_name, field_type in new_class.__annotations__.items():
                if not (hasattr(field_type, '__origin__') and hasattr(field_type, '__args__') and hasattr(field_type, '__metadata__')):
                    continue
                
                # Extract UseColumn instance from __metadata__
                use_columns_found = [arg for arg in field_type.__metadata__ if isinstance(arg, UseColumn)]

                if len(use_columns_found) > 1:
                    raise TypeError(
                        f"Invalid column mapping definition on field '{field_name}'. "
                        f"A field can have at most one UseColumn specified, but {len(use_columns_found)} were found."
                    )

                if use_columns_found:
                    use_column_instance = use_columns_found[0]
                    column_mappings[field_name] = use_column_instance.name

        setattr(new_class, '__column_mappings__', column_mappings)


class ColumnMappingMixin:
    """
    Provides field-to-database column name mapping functionality.

    It registers the ColumnAnnotationHandler to be run by the metaclass system
    and provides the runtime `_get_db_column_name` method.
    """
    _feature_handlers = [ColumnAnnotationHandler]

    __column_mappings__: ClassVar[Dict[str, str]] = {}

    @classmethod
    def _get_db_column_name(cls, field_name: str) -> str:
        """
        Retrieves the actual database column name for a given model field.
        If a custom mapping is defined via `UseColumn`, it returns the mapped name.
        Otherwise, it returns the model field name itself.

        Args:
            field_name: The name of the model field.

        Returns:
            The corresponding database column name.
        """
        return cls.__column_mappings__.get(field_name, field_name)
