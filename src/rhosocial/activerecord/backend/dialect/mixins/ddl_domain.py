# src/rhosocial/activerecord/backend/dialect/mixins/ddl_domain.py
"""Composition base for DomainMixin. Feature groups live in per-statement mixins."""

from typing import Tuple, Type, TYPE_CHECKING
from rhosocial.activerecord.backend.expression.objects import Domain
from rhosocial.activerecord.backend.expression.statements.ddl_domain import DomainAlterAction, DomainCheckConstraint, DomainNullability
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from .create_domain_mixin import CreateDomainMixin
from .alter_domain_mixin import AlterDomainMixin
from .drop_domain_mixin import DropDomainMixin

class DomainMixin(CreateDomainMixin, AlterDomainMixin, DropDomainMixin):
    """Composition of CreateDomainMixin, AlterDomainMixin, DropDomainMixin. No own members."""
    pass
