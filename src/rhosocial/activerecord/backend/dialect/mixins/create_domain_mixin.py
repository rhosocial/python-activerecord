# src/rhosocial/activerecord/backend/dialect/mixins/create_domain_mixin.py
"""Per-statement mixin for CreateDomainSupport. Members/order/signature mirror the protocol."""

from typing import Tuple, Type, TYPE_CHECKING
from rhosocial.activerecord.backend.expression.objects import Domain
from rhosocial.activerecord.backend.expression.statements.ddl_domain import DomainAlterAction, DomainCheckConstraint, DomainNullability
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

class CreateDomainMixin:
    def supports_domains(self) -> bool:
            """Whether domain objects are supported."""
            return False

    def supports_create_domain(self) -> bool:
            """Whether CREATE DOMAIN is supported."""
            return self.supports_domains()

    def supports_domain_default(self) -> bool:
            """Whether domain DEFAULT values are supported."""
            return self.supports_domains()

    def supports_domain_nullability(
            self,
            nullability: "DomainNullability",
        ) -> bool:
            """Whether a domain nullability declaration is supported."""
            if not self.supports_domains():
                return False
            return nullability in set(DomainNullability)

    def supports_domain_checks(self) -> bool:
            """Whether domain CHECK constraints are supported."""
            return self.supports_domains()

    def supports_named_domain_checks(self) -> bool:
            """Whether named domain CHECK constraints are supported."""
            return False

    def supports_multiple_domain_checks(self) -> bool:
            """Whether a domain may declare multiple CHECK constraints."""
            return False

    def supports_domain_collation(self) -> bool:
            """Whether domain COLLATE clauses are supported."""
            return self.supports_domains()

    def format_create_domain_statement(
            self,
            expr: "CreateDomainStatement",
        ) -> Tuple[str, tuple]:
            """Format a standard CREATE DOMAIN statement.

            Raises:
                TypeError: ``CreateDomainStatement.domain`` is not a Domain. Another
                object kind would have had its own name rendered as the domain's.
                TypeError: An entry of ``CreateDomainStatement.checks`` is not a
                DomainCheckConstraint. An entry of another kind has no check clause to
                render, so its CHECK would silently disappear.
            """
            if not isinstance(expr.domain, Domain):
                raise TypeError(
                    f"CreateDomainStatement.domain must be a Domain, "
                    f"got {type(expr.domain).__name__}"
                )

            for position, entry in enumerate(expr.checks):
                if not isinstance(entry, DomainCheckConstraint):
                    raise TypeError(
                        f"CreateDomainStatement.checks must hold DomainCheckConstraint instances, "
                        f"got {type(entry).__name__} at position {position}"
                    )
            if not self.supports_domains() or not self.supports_create_domain():
                raise UnsupportedFeatureError(self.name, "CREATE DOMAIN")
            type_sql, type_params = expr.data_type.to_sql()
            parts = [
                "CREATE DOMAIN",
                expr.domain.to_sql()[0],
                "AS",
                type_sql,
            ]
            params = list(type_params)
            if expr.collation is not None:
                if not self.supports_domain_collation():
                    raise UnsupportedFeatureError(self.name, "DOMAIN COLLATE")
                collation_parts = expr.collation.split(".")
                if any(not part.strip() for part in collation_parts):
                    raise ValueError("collation must contain non-empty identifier segments")
                collation_sql = ".".join(
                    self.format_identifier(part) for part in collation_parts
                )
                parts.append(f"COLLATE {collation_sql}")
            if expr.default is not None:
                if not self.supports_domain_default():
                    raise UnsupportedFeatureError(self.name, "DOMAIN DEFAULT")
                default_sql, default_params = expr.default.to_sql()
                if default_params:
                    raise ValueError("DOMAIN DEFAULT must render without bind parameters")
                parts.append(f"DEFAULT {default_sql}")
            checks = list(expr.checks)
            if checks and not self.supports_domain_checks():
                raise UnsupportedFeatureError(self.name, "DOMAIN CHECK")
            if any(check.name is not None for check in checks):
                if not self.supports_named_domain_checks():
                    raise UnsupportedFeatureError(self.name, "named DOMAIN CHECK")
            if len(checks) > 1 and not self.supports_multiple_domain_checks():
                raise UnsupportedFeatureError(
                    self.name,
                    "multiple domain CHECK constraints",
                )
            for check in checks:
                check_sql, check_params = check.to_sql()
                parts.append(check_sql)
                params.extend(check_params)
            if expr.nullability is not DomainNullability.UNSPECIFIED:
                if not self.supports_domain_nullability(expr.nullability):
                    raise UnsupportedFeatureError(
                        self.name,
                        f"DOMAIN {expr.nullability.value}",
                    )
                parts.append(expr.nullability.value)
            return " ".join(parts), tuple(params)

    def format_domain_value_expression(
            self,
            expr: "DomainValueExpression",
        ) -> Tuple[str, tuple]:
            """Format the domain VALUE reference."""
            if not self.supports_domains():
                raise UnsupportedFeatureError(self.name, "DOMAIN VALUE")
            return "VALUE", ()

    def format_domain_check_constraint(
            self,
            expr: "DomainCheckConstraint",
        ) -> Tuple[str, tuple]:
            """Format a domain CHECK constraint."""
            if not self.supports_domains() or not self.supports_domain_checks():
                raise UnsupportedFeatureError(self.name, "DOMAIN CHECK")
            if expr.name is not None and not self.supports_named_domain_checks():
                raise UnsupportedFeatureError(self.name, "named DOMAIN CHECK")
            condition_sql, condition_params = expr.condition.to_sql()
            if expr.name is None:
                sql = f"CHECK ({condition_sql})"
            else:
                sql = (
                    f"CONSTRAINT {self.format_identifier(expr.name)} "
                    f"CHECK ({condition_sql})"
                )
            return sql, tuple(condition_params)
