# src/rhosocial/activerecord/backend/field_registry.py
"""
Manages the registration and retrieval of `SQLField` types based on Python types,
enabling dynamic resolution of typed column expressions.
"""
from __future__ import annotations
from typing import Type, Dict, Optional, Any

from .field import SQLField


class FieldTypeRegistry:
    """
    Manages the mapping between Python types and SQLField types for a backend.

    This allows backends to provide optimized or specific SQLField implementations
    for common Python types (e.g., mapping `dict` to a `JSONField`).
    """

    def __init__(self):
        self._mapping: Dict[Type[Any], Type[SQLField]] = {}

    def register(self, python_type: Type[Any], field_type: Type[SQLField]):
        """
        Registers a mapping from a Python type to a SQLField type.
        """
        self._mapping[python_type] = field_type

    def get_field_type(self, python_type: Type[Any]) -> Optional[Type[SQLField]]:
        """
        Retrieves the mapped SQLField type for a given Python type.
        """
        return self._mapping.get(python_type)

    def __repr__(self) -> str:
        return f"<FieldTypeRegistry mappings={len(self._mapping)}>"


