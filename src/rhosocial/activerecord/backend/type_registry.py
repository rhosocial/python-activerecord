# src/rhosocial/activerecord/backend/type_registry.py
"""
Registry for type adapters.

This module defines the TypeRegistry class, which is responsible for
managing and providing access to SQLTypeAdapter instances based on
Python type and database type pairs.
"""
from typing import Any, Dict, List, Optional, Sequence, Tuple, Type, Union
from .type_adapter import SQLTypeAdapter

class TypeRegistry:
    """Registry for type adapters with exact type pair matching."""
    def __init__(self):
        self._adapters: Dict[Tuple[Type, Type], SQLTypeAdapter] = {}

    def register(
        self,
        adapter: SQLTypeAdapter,
        py_type: Type,
        db_type: Type,
        allow_override: bool = False
    ) -> None:
        type_pair = (py_type, db_type)
        if not allow_override and type_pair in self._adapters:
            raise ValueError(f"Type pair already registered.")
        self._adapters[type_pair] = adapter

    def get_adapter(self, py_type: Type, db_type: Type) -> Optional[SQLTypeAdapter]:
        return self._adapters.get((py_type, db_type))

    def get_all_adapters(self) -> Dict[Tuple[Type, Type], SQLTypeAdapter]:
        """Returns a copy of all registered adapters."""
        return self._adapters.copy()