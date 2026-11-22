# src/rhosocial/activerecord/backend/dialect/mixins/ddl_schema.py
"""Composition base for SchemaMixin. Feature groups live in per-statement mixins."""

from typing import Tuple, TYPE_CHECKING
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.objects import Schema
from .create_schema_mixin import CreateSchemaMixin
from .drop_schema_mixin import DropSchemaMixin

class SchemaMixin(CreateSchemaMixin, DropSchemaMixin):
    """Composition of CreateSchemaMixin, DropSchemaMixin. No own members."""
    pass
