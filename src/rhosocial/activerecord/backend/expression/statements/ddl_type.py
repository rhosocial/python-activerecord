# src/rhosocial/activerecord/backend/expression/statements/ddl_type.py
"""User-defined type DDL expression nodes."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from ..bases import BaseExpression
from ..objects import Type

if TYPE_CHECKING:
    from ...dialect import SQLDialectBase


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


class CreateTypeStatement(BaseExpression):
    """Expression for ``CREATE TYPE``."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        type: "Type",
        definition: TypeDefinition,
        *,
        if_not_exists: bool = False,
        or_replace: bool = False,
    ) -> None:
        super().__init__(dialect)
        if if_not_exists and or_replace:
            raise ValueError("CREATE TYPE IF NOT EXISTS and OR REPLACE are mutually exclusive")
        self.type = type
        self.definition = definition
        self.if_not_exists = if_not_exists
        self.or_replace = or_replace

    @property
    def format_method(self) -> str:
        return "format_create_type_statement"


class AlterTypeStatement(BaseExpression):
    """One ``ALTER TYPE`` statement carrying exactly one action.

    One expression renders one statement, and that statement carries one action;
    a caller with several changes builds one statement per action and orders
    them itself.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        type: "Type",
        action: TypeAlterAction,
        *,
        if_exists: bool = False,
    ) -> None:
        super().__init__(dialect)
        self.type = type
        self.action = action
        self.if_exists = if_exists

    @property
    def format_method(self) -> str:
        return "format_alter_type_statement"


class DropTypeStatement(BaseExpression):
    """Expression for ``DROP TYPE``."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        type: "Type",
        *,
        if_exists: bool = False,
    ) -> None:
        super().__init__(dialect)
        self.type = type
        self.if_exists = if_exists

    @property
    def format_method(self) -> str:
        return "format_drop_type_statement"


__all__ = [
    "TypeDefinition",
    "TypeAlterAction",
    "CreateTypeStatement",
    "AlterTypeStatement",
    "DropTypeStatement",
]
