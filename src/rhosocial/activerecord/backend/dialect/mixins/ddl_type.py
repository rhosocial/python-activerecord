# src/rhosocial/activerecord/backend/dialect/mixins/ddl_type.py
"""Compatibility module path for the data type mixin (no class alias).

The canonical definition lives in :mod:`.data_type`. This module simply
re-exports it under the historical module path; there is no second class
name, so naming injectivity is preserved.
"""

from .data_type import DataTypeMixin

__all__ = ["DataTypeMixin"]
