# src/rhosocial/activerecord/backend/expression/statements/ddl_domain.py
"""Domain DDL expression nodes."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, List, Optional, Sequence, TYPE_CHECKING

from ..bases import BaseExpression, SQLPredicate, SQLValueExpression
from ..mixins import ComparisonMixin, StringMixin, TypeCastingMixin
from ..types import DataType
from .ddl_table import DefaultValueClause

if TYPE_CHECKING:
    from ...dialect import SQLDialectBase


def _validate_name(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _normalize_default(dialect: "SQLDialectBase", value: Any) -> DefaultValueClause:
    if isinstance(value, DefaultValueClause):
        return value
    return DefaultValueClause(dialect, value)


class DomainNullability(Enum):
    """Nullability declaration for a domain."""

    UNSPECIFIED = "UNSPECIFIED"
    NULLABLE = "NULL"
    NOT_NULL = "NOT NULL"


class DomainValueExpression(
    ComparisonMixin,
    StringMixin,
    TypeCastingMixin,
    SQLValueExpression,
):
    """The ``VALUE`` expression available inside a domain check."""

    @property
    def format_method(self) -> str:
        return "format_domain_value_expression"


class DomainCheckConstraint(BaseExpression):
    """A domain ``CHECK`` constraint with an optional constraint name."""

    @property
    def format_method(self) -> str:
        return "format_domain_check_constraint"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        condition: SQLPredicate,
        *,
        name: Optional[str] = None,
    ) -> None:
        super().__init__(dialect)
        if not isinstance(condition, SQLPredicate):
            raise TypeError(
                f"condition must be a SQLPredicate instance, got {type(condition).__name__}"
            )
        if name is not None:
            _validate_name(name, "name")
        self.condition = condition
        self.name = name

    @property
    def check_condition(self) -> SQLPredicate:
        return self.condition


class DomainAlterAction(BaseExpression, ABC):
    """Base class for one ALTER DOMAIN action."""

    @property
    @abstractmethod
    def action_kind(self) -> str:
        """Stable kind name used by dialect capability dispatch."""

    @property
    def format_method(self) -> str:
        return "format_domain_alter_action"


class SetDomainDefaultAction(DomainAlterAction):
    """Set a domain default value."""

    action_kind = "set_default"

    def __init__(self, dialect: "SQLDialectBase", default: Any) -> None:
        super().__init__(dialect)
        self.default = _normalize_default(dialect, default)

    @property
    def value(self) -> BaseExpression:
        return self.default


class DropDomainDefaultAction(DomainAlterAction):
    """Remove a domain default value."""

    action_kind = "drop_default"

    def __init__(self, dialect: "SQLDialectBase") -> None:
        super().__init__(dialect)


class SetDomainNotNullAction(DomainAlterAction):
    """Make a domain non-nullable."""

    action_kind = "set_not_null"

    def __init__(self, dialect: "SQLDialectBase") -> None:
        super().__init__(dialect)
        self.nullability = DomainNullability.NOT_NULL


class DropDomainNotNullAction(DomainAlterAction):
    """Make a domain nullable."""

    action_kind = "drop_not_null"

    def __init__(self, dialect: "SQLDialectBase") -> None:
        super().__init__(dialect)
        self.nullability = DomainNullability.NULLABLE


class AddDomainCheckAction(DomainAlterAction):
    """Add a check constraint to a domain."""

    action_kind = "add_check"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        check: DomainCheckConstraint,
    ) -> None:
        super().__init__(dialect)
        if isinstance(check, SQLPredicate):
            check = DomainCheckConstraint(dialect, check)
        if not isinstance(check, DomainCheckConstraint):
            raise TypeError(
                f"check must be a DomainCheckConstraint instance, got {type(check).__name__}"
            )
        self.check = check


class DropDomainCheckAction(DomainAlterAction):
    """Drop a named or unnamed domain check constraint."""

    action_kind = "drop_check"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        *,
        name: Optional[str] = None,
    ) -> None:
        super().__init__(dialect)
        if name is not None:
            _validate_name(name, "name")
        self.name = name


class RenameDomainAction(DomainAlterAction):
    """Rename a domain."""

    action_kind = "rename"

    def __init__(self, dialect: "SQLDialectBase", new_name: str) -> None:
        super().__init__(dialect)
        _validate_name(new_name, "new_name")
        self.new_name = new_name


class CreateDomainExpression(BaseExpression):
    """Expression for ``CREATE DOMAIN``."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        domain_name: str,
        data_type: DataType,
        *,
        default: Any = None,
        nullability: DomainNullability = DomainNullability.UNSPECIFIED,
        checks: Optional[Sequence[DomainCheckConstraint]] = None,
        collation: Optional[str] = None,
    ) -> None:
        super().__init__(dialect)
        _validate_name(domain_name, "domain_name")
        if not isinstance(data_type, DataType):
            raise TypeError(
                f"data_type must be a DataType instance, got {type(data_type).__name__}"
            )
        if default is not None:
            default = _normalize_default(dialect, default)
        if isinstance(nullability, str):
            try:
                nullability = DomainNullability(nullability)
            except ValueError as exc:
                raise ValueError(f"Invalid domain nullability: {nullability!r}") from exc
        if not isinstance(nullability, DomainNullability):
            raise TypeError(
                f"nullability must be a DomainNullability instance, got "
                f"{type(nullability).__name__}"
            )
        if collation is not None:
            _validate_name(collation, "collation")
            if any(not part.strip() for part in collation.split(".")):
                raise ValueError("collation must contain non-empty identifier segments")
        check_items: List[Any]
        if checks is None:
            check_items = []
        elif isinstance(checks, (DomainCheckConstraint, SQLPredicate)):
            check_items = [checks]
        else:
            check_items = list(checks)
        normalized_checks: List[DomainCheckConstraint] = []
        for check in check_items:
            if isinstance(check, SQLPredicate):
                check = DomainCheckConstraint(dialect, check)
            if not isinstance(check, DomainCheckConstraint):
                raise TypeError(
                    f"checks must contain DomainCheckConstraint instances, got "
                    f"{type(check).__name__}"
                )
            normalized_checks.append(check)
        self.domain_name = domain_name
        self.data_type = data_type
        self.default = default
        self.nullability = nullability
        self.checks = normalized_checks
        self.collation = collation

    @property
    def name(self) -> str:
        return self.domain_name

    @property
    def default_value(self) -> Optional[BaseExpression]:
        return self.default

    @property
    def format_method(self) -> str:
        return "format_create_domain_statement"


class AlterDomainExpression(BaseExpression):
    """Expression for ``ALTER DOMAIN``."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        domain_name: str,
        actions: Sequence[DomainAlterAction],
    ) -> None:
        super().__init__(dialect)
        _validate_name(domain_name, "domain_name")
        action_list = list(actions or [])
        if not action_list:
            raise ValueError("actions must contain at least one DomainAlterAction")
        for action in action_list:
            if not isinstance(action, DomainAlterAction):
                raise TypeError(
                    f"actions must contain DomainAlterAction instances, got {type(action).__name__}"
                )
        self.domain_name = domain_name
        self.actions = action_list

    @property
    def name(self) -> str:
        return self.domain_name

    @property
    def format_method(self) -> str:
        return "format_alter_domain_statement"


class DropDomainExpression(BaseExpression):
    """Expression for ``DROP DOMAIN``."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        domain_name: str,
    ) -> None:
        super().__init__(dialect)
        _validate_name(domain_name, "domain_name")
        self.domain_name = domain_name

    @property
    def name(self) -> str:
        return self.domain_name

    @property
    def format_method(self) -> str:
        return "format_drop_domain_statement"


__all__ = [
    "DomainNullability",
    "DomainValueExpression",
    "DomainCheckConstraint",
    "DomainAlterAction",
    "SetDomainDefaultAction",
    "DropDomainDefaultAction",
    "SetDomainNotNullAction",
    "DropDomainNotNullAction",
    "AddDomainCheckAction",
    "DropDomainCheckAction",
    "RenameDomainAction",
    "CreateDomainExpression",
    "AlterDomainExpression",
    "DropDomainExpression",
]
