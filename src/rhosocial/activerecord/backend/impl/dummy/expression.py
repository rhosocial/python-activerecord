# src/rhosocial/activerecord/backend/impl/dummy/expression.py
"""Expression nodes used to exercise generic DDL protocols in DummyDialect."""

from typing import TYPE_CHECKING

from rhosocial.activerecord.backend.expression.serialization import ExpressionRegistry
from rhosocial.activerecord.backend.expression.statements.ddl_type import (
    TypeAlterAction,
    TypeDefinition,
)
from rhosocial.activerecord.backend.expression.types import DataType

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class _DummyTypeDefinition(TypeDefinition):
    definition_kind = "dummy.alias"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        data_type: DataType,
    ) -> None:
        super().__init__(dialect)
        if not isinstance(data_type, DataType):
            raise TypeError(
                f"data_type must be a DataType instance, got {type(data_type).__name__}"
            )
        self.data_type = data_type


class _DummyTypeAlterAction(TypeAlterAction):
    action_kind = "dummy.rename"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        new_name: str = "renamed",
    ) -> None:
        super().__init__(dialect)
        if not isinstance(new_name, str) or not new_name.strip():
            raise ValueError("new_name must be a non-empty string")
        self.new_name = new_name


ExpressionRegistry.register(_DummyTypeDefinition)
ExpressionRegistry.register(_DummyTypeAlterAction)


__all__ = ["_DummyTypeDefinition", "_DummyTypeAlterAction"]
