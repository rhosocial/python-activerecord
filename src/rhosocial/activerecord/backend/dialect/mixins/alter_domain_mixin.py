# src/rhosocial/activerecord/backend/dialect/mixins/alter_domain_mixin.py
"""Per-statement mixin for AlterDomainSupport. Members/order/signature mirror the protocol."""

from typing import Tuple
from rhosocial.activerecord.backend.expression.objects import Domain
from rhosocial.activerecord.backend.expression.statements.ddl_domain import DomainAlterAction
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

class AlterDomainMixin:
    def supports_alter_domain(self) -> bool:
            """Whether ALTER DOMAIN is supported."""
            return self.supports_domains()

    def supports_unnamed_domain_check_drop(self) -> bool:
            """Whether an unnamed domain CHECK can be dropped."""
            return False

    def format_alter_domain_statement(
            self,
            expr: "AlterDomainStatement",
        ) -> Tuple[str, tuple]:
            """Format a standard ALTER DOMAIN statement carrying one action.

            One expression renders one statement, and that statement carries one
            action; a caller with several changes builds one statement per action
            and orders them itself.

            Raises:
                TypeError: ``AlterDomainStatement.domain`` is not a Domain. Another
                object kind would have had its own name rendered as the domain's.
                TypeError: ``AlterDomainStatement.action`` is not an implementation
                of DomainAlterAction. Another kind has no action clause to dispatch
                on, so nothing would be rendered for it.
            """
            if not isinstance(expr.domain, Domain):
                raise TypeError(
                    f"AlterDomainStatement.domain must be a Domain, "
                    f"got {type(expr.domain).__name__}"
                )

            # DomainAlterAction is an abstract base and cannot be instantiated, so
            # this reports that the entry is not an implementation of it
            # rather than naming a concrete type.
            if not isinstance(expr.action, DomainAlterAction):
                raise TypeError(
                    f"AlterDomainStatement.action must be a DomainAlterAction implementation, "
                    f"got {type(expr.action).__name__}"
                )
            if not self.supports_domains() or not self.supports_alter_domain():
                raise UnsupportedFeatureError(self.name, "ALTER DOMAIN")
            action_sql, action_params = expr.action.to_sql()
            return (
                f"ALTER DOMAIN {expr.domain.to_sql()[0]} {action_sql}",
                tuple(action_params),
            )

    def format_domain_alter_action(
            self,
            expr: "DomainAlterAction",
        ) -> Tuple[str, tuple]:
            """Format one standard ALTER DOMAIN action."""
            from ...expression.statements.ddl_domain import (
                AddDomainCheckAction,
                DropDomainCheckAction,
                DropDomainDefaultAction,
                DropDomainNotNullAction,
                RenameDomainAction,
                SetDomainDefaultAction,
                SetDomainNotNullAction,
            )

            if not self.supports_domains() or not self.supports_alter_domain():
                raise UnsupportedFeatureError(self.name, "ALTER DOMAIN action")
            if isinstance(expr, SetDomainDefaultAction):
                if not self.supports_domain_default():
                    raise UnsupportedFeatureError(self.name, "ALTER DOMAIN SET DEFAULT")
                value_sql, params = expr.default.to_sql()
                if params:
                    raise ValueError("ALTER DOMAIN DEFAULT must render without bind parameters")
                return f"SET DEFAULT {value_sql}", ()
            if isinstance(expr, DropDomainDefaultAction):
                if not self.supports_domain_default():
                    raise UnsupportedFeatureError(self.name, "ALTER DOMAIN DROP DEFAULT")
                return "DROP DEFAULT", ()
            if isinstance(expr, SetDomainNotNullAction):
                if not self.supports_domain_not_null():
                    raise UnsupportedFeatureError(self.name, "ALTER DOMAIN SET NOT NULL")
                return "SET NOT NULL", ()
            if isinstance(expr, DropDomainNotNullAction):
                if not self.supports_domain_not_null():
                    raise UnsupportedFeatureError(self.name, "ALTER DOMAIN DROP NOT NULL")
                return "DROP NOT NULL", ()
            if isinstance(expr, AddDomainCheckAction):
                check_sql, params = expr.check.to_sql()
                return f"ADD {check_sql}", tuple(params)
            if isinstance(expr, DropDomainCheckAction):
                if not self.supports_domain_checks():
                    raise UnsupportedFeatureError(self.name, "ALTER DOMAIN DROP CHECK")
                if expr.name is None:
                    if not self.supports_unnamed_domain_check_drop():
                        raise UnsupportedFeatureError(
                            self.name,
                            "unnamed DOMAIN CHECK drop",
                        )
                    return "DROP CONSTRAINT", ()
                if not self.supports_named_domain_checks():
                    raise UnsupportedFeatureError(
                        self.name,
                        "named DOMAIN CHECK drop",
                    )
                return f"DROP CONSTRAINT {self.format_identifier(expr.name)}", ()
            if isinstance(expr, RenameDomainAction):
                return f"RENAME TO {self.format_identifier(expr.new_name)}", ()
            raise UnsupportedFeatureError(
                self.name,
                f"ALTER DOMAIN action {expr.action_kind}",
            )
