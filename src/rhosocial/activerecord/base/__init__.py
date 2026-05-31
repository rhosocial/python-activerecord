# src/rhosocial/activerecord/base/__init__.py
"""Base ActiveRecord implementation providing core functionality."""

from .base import BaseActiveRecord, AsyncBaseActiveRecord
from .query_mixin import QueryMixin, AsyncQueryMixin
from .field_proxy import FieldProxy
from .column_name_mixin import ColumnNameMixin, ColumnNameAnnotationHandler
from .field_adapter_mixin import FieldAdapterMixin, AdapterAnnotationHandler
from .derived_field_mixin import DerivedFieldMixin
from .derived_field_handler import DerivedFieldHandler
from .fields import UseColumn, UseAdapter, DerivedField
from .metaclass import MetaclassMixin, ActiveRecordMetaclass

__all__ = [
    "BaseActiveRecord",
    "AsyncBaseActiveRecord",
    "QueryMixin",
    "AsyncQueryMixin",
    "FieldProxy",
    "ColumnNameMixin",
    "ColumnNameAnnotationHandler",
    "FieldAdapterMixin",
    "AdapterAnnotationHandler",
    "DerivedFieldMixin",
    "DerivedFieldHandler",
    "UseColumn",
    "UseAdapter",
    "DerivedField",
    "MetaclassMixin",
    "ActiveRecordMetaclass",
]
