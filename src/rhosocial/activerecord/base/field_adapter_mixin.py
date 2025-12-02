# src/rhosocial/activerecord/base/field_adapter_mixin.py
"""
This module provides a mixin for handling field-specific type adapters.
"""
from typing import ClassVar, Dict, Optional, Tuple, Type

from ..backend.type_adapter import SQLTypeAdapter
from .metaclass import ActiveRecordMetaclass


class FieldAdapterMixin(metaclass=ActiveRecordMetaclass):
    """
    A mixin that enables field-specific SQL type adapter definitions via annotations.

    When this mixin is included in a model's inheritance chain, it applies
    the `ActiveRecordMetaclass`, which parses `@UseAdapter` annotations
    and populates the `__field_adapters__` dictionary.
    """
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
