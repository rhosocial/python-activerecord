# src/rhosocial/activerecord/backend/dialect/mixins/ddl_index.py
"""Composition base for IndexMixin. Feature groups live in per-statement mixins."""

from typing import List, Tuple, TYPE_CHECKING
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.bases import ToSQLProtocol
from rhosocial.activerecord.backend.expression.objects import Index, Table
from .create_index_mixin import CreateIndexMixin
from .drop_index_mixin import DropIndexMixin
from .fulltext_index_mixin import FulltextIndexMixin

class IndexMixin(CreateIndexMixin, DropIndexMixin, FulltextIndexMixin):
    """Composition of CreateIndexMixin, DropIndexMixin, FulltextIndexMixin. No own members."""
    pass
