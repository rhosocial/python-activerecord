# src/rhosocial/activerecord/backend/expression/statements/ddl_type.py
"""User-defined type DDL expression nodes."""

from abc import ABC, abstractmethod
from typing import Optional, Sequence, TYPE_CHECKING

from ..bases import BaseExpression

if TYPE_CHECKING:
    from ...dialect import SQLDialectBase


def _validate_name(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


class TypeDefinition(BaseExpression, ABC):
    """Base class for a user-defined type definition."""

    @property
    @abstractmethod
    def definition_kind(self) -> str:
        """Stable kind name used by dialect capability dispatch."""

    @property
    def format_method(self) -> str:
        return "format_type_definition"


class TypeAlterAction(BaseExpression, ABC):
    """Base class for one ALTER TYPE action."""

    @property
    @abstractmethod
    def action_kind(self) -> str:
        """Stable kind name used by dialect capability dispatch."""

    @property
    def format_method(self) -> str:
        return "format_type_alter_action"


class CreateTypeExpression(BaseExpression):
    """Expression for ``CREATE TYPE``."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        type_name: str,
        definition: TypeDefinition,
        *,
        schema_name: Optional[str] = None,
        if_not_exists: bool = False,
        or_replace: bool = False,
    ) -> None:
        super().__init__(dialect)
        _validate_name(type_name, "type_name")
        if schema_name is not None:
            _validate_name(schema_name, "schema_name")
        if not isinstance(definition, TypeDefinition):
            raise TypeError(
                f"definition must be a TypeDefinition instance, got {type(definition).__name__}"
            )
        if if_not_exists and or_replace:
            raise ValueError("CREATE TYPE IF NOT EXISTS and OR REPLACE are mutually exclusive")
        self.type_name = type_name
        self.schema_name = schema_name
        self.definition = definition
        self.if_not_exists = if_not_exists
        self.or_replace = or_replace

    @property
    def format_method(self) -> str:
        return "format_create_type_statement"


class AlterTypeExpression(BaseExpression):
    """Expression for ``ALTER TYPE``."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        type_name: str,
        actions: Sequence[TypeAlterAction],
        *,
        schema_name: Optional[str] = None,
        if_exists: bool = False,
    ) -> None:
        super().__init__(dialect)
        _validate_name(type_name, "type_name")
        if schema_name is not None:
            _validate_name(schema_name, "schema_name")
        action_list = list(actions or [])
        if not action_list:
            raise ValueError("actions must contain at least one TypeAlterAction")
        for action in action_list:
            if not isinstance(action, TypeAlterAction):
                raise TypeError(
                    f"actions must contain TypeAlterAction instances, got {type(action).__name__}"
                )
        self.type_name = type_name
        self.schema_name = schema_name
        self.actions = action_list
        self.if_exists = if_exists

    @property
    def format_method(self) -> str:
        return "format_alter_type_statement"


class DropTypeExpression(BaseExpression):
    """Expression for ``DROP TYPE``."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        type_name: str,
        *,
        schema_name: Optional[str] = None,
        if_exists: bool = False,
    ) -> None:
        super().__init__(dialect)
        _validate_name(type_name, "type_name")
        if schema_name is not None:
            _validate_name(schema_name, "schema_name")
        self.type_name = type_name
        self.schema_name = schema_name
        self.if_exists = if_exists

    @property
    def format_method(self) -> str:
        return "format_drop_type_statement"


__all__ = [
    "TypeDefinition",
    "TypeAlterAction",
    "CreateTypeExpression",
    "AlterTypeExpression",
    "DropTypeExpression",
]
