# src/rhosocial/activerecord/backend/dialect/mixins/ddl_database.py
"""Composition base for DatabaseMixin. Feature groups live in per-statement mixins."""

from typing import Tuple, TYPE_CHECKING
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.objects import Database
from .create_database_mixin import CreateDatabaseMixin
from .alter_database_mixin import AlterDatabaseMixin
from .drop_database_mixin import DropDatabaseMixin

class DatabaseMixin(CreateDatabaseMixin, AlterDatabaseMixin, DropDatabaseMixin):
    """Composition of CreateDatabaseMixin, AlterDatabaseMixin, DropDatabaseMixin. No own members."""
    pass
