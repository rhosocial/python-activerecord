# src/rhosocial/activerecord/backend/dialect/mixins/drop_domain_mixin.py
"""Per-statement mixin for DropDomainSupport. Members/order/signature mirror the protocol."""

from typing import Tuple, Type, TYPE_CHECKING
from rhosocial.activerecord.backend.expression.objects import Domain
from rhosocial.activerecord.backend.expression.statements.ddl_domain import DomainAlterAction, DomainCheckConstraint, DomainNullability
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

class DropDomainMixin:
    def supports_drop_domain(self) -> bool:
            """Whether DROP DOMAIN is supported."""
            return self.supports_domains()

    def supports_drop_domain_if_exists(self) -> bool:
            """Whether DROP DOMAIN IF EXISTS is supported."""
            return False

    def supports_drop_domain_cascade(self) -> bool:
            """Whether DROP DOMAIN CASCADE is supported."""
            return False

    def supports_drop_domain_restrict(self) -> bool:
            """Whether DROP DOMAIN RESTRICT is supported."""
            return False

    def format_drop_domain_statement(
            self,
            expr: "DropDomainStatement",
        ) -> Tuple[str, tuple]:
            """Format a standard DROP DOMAIN statement.

            Raises:
                TypeError: ``DropDomainStatement.domain`` is not a Domain. Another
                object kind would have had its own name rendered as the domain's.
            """
            if not isinstance(expr.domain, Domain):
                raise TypeError(
                    f"DropDomainStatement.domain must be a Domain, "
                    f"got {type(expr.domain).__name__}"
                )
            if not self.supports_domains() or not self.supports_drop_domain():
                raise UnsupportedFeatureError(self.name, "DROP DOMAIN")
            return f"DROP DOMAIN {expr.domain.to_sql()[0]}", ()
