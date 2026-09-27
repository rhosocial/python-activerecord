# src/rhosocial/activerecord/backend/dialect/mixins/ddl_type.py
"""Deprecated compatibility exports for the renamed data type mixin."""

from .data_type import DataTypeMixin

DDLTypeMixin = DataTypeMixin

__all__ = ["DataTypeMixin", "DDLTypeMixin"]
