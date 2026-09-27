# src/rhosocial/activerecord/backend/dialect/mixins/ddl_domain.py
"""Generic domain DDL capability checks and formatters."""

from typing import Tuple, Type, TYPE_CHECKING

from ...expression.statements.ddl_domain import DomainNullability
from ..exceptions import UnsupportedFeatureError

if TYPE_CHECKING:
    from ...expression.statements.ddl_domain import (
        AlterDomainExpression,
        CreateDomainExpression,
        DomainAlterAction,
        DomainCheckConstraint,
        DomainValueExpression,
        DropDomainExpression,
    )


class DomainMixin:
    """Capability checks and standard rendering for domain DDL."""

    if TYPE_CHECKING:
        name: str

        def format_identifier(self, identifier: str, need_quote: bool = True) -> str:
            ...

    def supports_domains(self) -> bool:
        """Whether domain objects are supported."""
        return False

    def supports_create_domain(self) -> bool:
        """Whether CREATE DOMAIN is supported."""
        return self.supports_domains()

    def supports_alter_domain(self) -> bool:
        """Whether ALTER DOMAIN is supported."""
        return self.supports_domains()

    def supports_drop_domain(self) -> bool:
        """Whether DROP DOMAIN is supported."""
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

    def supports_alter_domain_action(
        self,
        action_type: Type["DomainAlterAction"],
    ) -> bool:
        """Whether an ALTER DOMAIN action class is supported."""
        return False

    def supports_multiple_domain_alter_actions(self) -> bool:
        """Whether one ALTER DOMAIN statement may contain multiple actions."""
        return False

    def supports_drop_domain_if_exists(self) -> bool:
        """Whether DROP DOMAIN IF EXISTS is supported."""
        return False

    def supports_drop_domain_cascade(self) -> bool:
        """Whether DROP DOMAIN CASCADE is supported."""
        return False

    def supports_drop_domain_restrict(self) -> bool:
        """Whether DROP DOMAIN RESTRICT is supported."""
        return False

    def supports_unnamed_domain_check_drop(self) -> bool:
        """Whether an unnamed domain CHECK can be dropped."""
        return False

    def format_create_domain_statement(
        self,
        expr: "CreateDomainExpression",
    ) -> Tuple[str, tuple]:
        """Format a standard CREATE DOMAIN statement."""
        if not self.supports_domains() or not self.supports_create_domain():
            raise UnsupportedFeatureError(self.name, "CREATE DOMAIN")
        type_sql, type_params = expr.data_type.to_sql()
        parts = [
            "CREATE DOMAIN",
            self.format_identifier(expr.domain_name),
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

    def format_alter_domain_statement(
        self,
        expr: "AlterDomainExpression",
    ) -> Tuple[str, tuple]:
        """Format a standard ALTER DOMAIN statement."""
        if not self.supports_domains() or not self.supports_alter_domain():
            raise UnsupportedFeatureError(self.name, "ALTER DOMAIN")
        if len(expr.actions) > 1 and not self.supports_multiple_domain_alter_actions():
            raise UnsupportedFeatureError(self.name, "multiple ALTER DOMAIN actions")
        action_parts = []
        action_params = []
        for action in expr.actions:
            if not self.supports_alter_domain_action(type(action)):
                raise UnsupportedFeatureError(
                    self.name,
                    f"ALTER DOMAIN action {action.action_kind}",
                )
            action_sql, params = action.to_sql()
            action_parts.append(action_sql)
            action_params.extend(params)
        return (
            f"ALTER DOMAIN {self.format_identifier(expr.domain_name)} "
            f"{', '.join(action_parts)}",
            tuple(action_params),
        )

    def format_drop_domain_statement(
        self,
        expr: "DropDomainExpression",
    ) -> Tuple[str, tuple]:
        """Format a standard DROP DOMAIN statement."""
        if not self.supports_domains() or not self.supports_drop_domain():
            raise UnsupportedFeatureError(self.name, "DROP DOMAIN")
        return f"DROP DOMAIN {self.format_identifier(expr.domain_name)}", ()

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
        if condition_params:
            raise ValueError("DOMAIN CHECK must render without bind parameters")
        if expr.name is None:
            sql = f"CHECK ({condition_sql})"
        else:
            sql = (
                f"CONSTRAINT {self.format_identifier(expr.name)} "
                f"CHECK ({condition_sql})"
            )
        return sql, tuple(condition_params)

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
        if not self.supports_alter_domain_action(type(expr)):
            raise UnsupportedFeatureError(
                self.name,
                f"ALTER DOMAIN action {expr.action_kind}",
            )
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
            if not self.supports_domain_nullability(expr.nullability):
                raise UnsupportedFeatureError(self.name, "ALTER DOMAIN SET NOT NULL")
            return "SET NOT NULL", ()
        if isinstance(expr, DropDomainNotNullAction):
            if not self.supports_domain_nullability(expr.nullability):
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
            f"ALTER DOMAIN action {getattr(expr, 'action_kind', type(expr).__name__)}",
        )


__all__ = ["DomainMixin"]
