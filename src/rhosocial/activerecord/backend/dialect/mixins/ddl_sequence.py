# src/rhosocial/activerecord/backend/dialect/mixins/ddl_sequence.py
"""Composition base for SequenceMixin. Feature groups live in per-statement mixins."""

from typing import Tuple, TYPE_CHECKING
from rhosocial.activerecord.backend.expression.objects import Sequence
from .create_sequence_mixin import CreateSequenceMixin
from .alter_sequence_mixin import AlterSequenceMixin
from .drop_sequence_mixin import DropSequenceMixin

class SequenceMixin(CreateSequenceMixin, AlterSequenceMixin, DropSequenceMixin):
    """Composition of CreateSequenceMixin, AlterSequenceMixin, DropSequenceMixin. No own members."""
    pass
