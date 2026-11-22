# src/rhosocial/activerecord/backend/dialect/mixins/trigger.py
"""Composition base for TriggerMixin. Feature groups live in per-statement mixins."""

from typing import Tuple, TYPE_CHECKING
from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.expression.objects import Function, Table, Trigger
from .create_trigger_mixin import CreateTriggerMixin
from .drop_trigger_mixin import DropTriggerMixin

class TriggerMixin(CreateTriggerMixin, DropTriggerMixin):
    """Composition of CreateTriggerMixin, DropTriggerMixin. No own members."""
    pass
