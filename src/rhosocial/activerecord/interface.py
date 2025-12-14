# src/rhosocial/activerecord/interface.py
"""
This module defines interfaces (Protocols) for core ActiveRecord components,
allowing for clear contracts and dependency inversion.
"""
from typing import Protocol, Type, Any, Optional, Dict, Tuple, List

from .backend.field_registry import FieldTypeRegistry
from .backend.type_adapter import SQLTypeAdapter
from .backend.base import StorageBackendBase # Assuming StorageBackendBase is the interface for backend


class IActiveRecord(Protocol):
    """
    Interface for an ActiveRecord model class.

    This protocol defines the minimal set of attributes and methods
    that a class must implement to be considered an ActiveRecord model
    by components like `FieldProxy`.
    """
    __tablename__: str

    @classmethod
    def table_name(cls) -> str:
        """Returns the database table name for the model."""
        ...

    @classmethod
    def get_backend(cls) -> StorageBackendBase: # Using StorageBackendBase as the interface for backend
        """Returns the active StorageBackend instance for this model."""
        ...

    @classmethod
    def get_column_name_for_field(cls, field_name: str) -> str:
        """
        Returns the database column name corresponding to a model field name,
        respecting any `UseColumn` annotations.
        """
        ...
