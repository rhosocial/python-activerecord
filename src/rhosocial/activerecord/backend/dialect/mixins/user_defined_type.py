# src/rhosocial/activerecord/backend/dialect/mixins/user_defined_type.py
"""Generic user-defined type DDL support."""

from typing import Tuple, Type, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError

if TYPE_CHECKING:
    from ...expression.statements.ddl_type import (
        AlterTypeExpression,
        CreateTypeExpression,
        DropTypeExpression,
        TypeAlterAction,
        TypeDefinition,
    )


class UserDefinedTypeMixin:
    """Capability checks and generic rendering for user-defined types."""

    if TYPE_CHECKING:
        name: str

        def format_identifier(self, identifier: str, need_quote: bool = True) -> str:
            ...

    def supports_type_objects(self) -> bool:
        """Whether user-defined type objects are supported."""
        return False

    def supports_create_type(self) -> bool:
        """Whether CREATE TYPE is supported."""
        return False

    def supports_alter_type(self) -> bool:
        """Whether ALTER TYPE is supported."""
        return False

    def supports_drop_type(self) -> bool:
        """Whether DROP TYPE is supported."""
        return False

    def supported_type_definitions(self) -> Tuple[Type["TypeDefinition"], ...]:
        """Return the concrete type-definition classes this dialect renders."""
        return ()

    def supports_type_definition(
        self,
        definition_type: Type["TypeDefinition"],
    ) -> bool:
        """Whether a type-definition class is supported."""
        try:
            return any(
                issubclass(definition_type, supported)
                for supported in self.supported_type_definitions()
            )
        except TypeError:
            return False

    def supports_type_alter_action(
        self,
        action_type: Type["TypeAlterAction"],
    ) -> bool:
        """Whether an ALTER TYPE action class is supported."""
        return False

    def supports_create_type_if_not_exists(self) -> bool:
        """Whether CREATE TYPE IF NOT EXISTS is supported."""
        return False

    def supports_create_type_or_replace(self) -> bool:
        """Whether CREATE OR REPLACE TYPE is supported."""
        return False

    def supports_alter_type_if_exists(self) -> bool:
        """Whether ALTER TYPE IF EXISTS is supported."""
        return False

    def supports_drop_type_if_exists(self) -> bool:
        """Whether DROP TYPE IF EXISTS is supported."""
        return False

    def supports_multiple_type_alter_actions(self) -> bool:
        """Whether one ALTER TYPE statement may contain multiple actions."""
        return False

    def format_create_type_statement(
        self,
        expr: "CreateTypeExpression",
    ) -> Tuple[str, tuple]:
        """Format a CREATE TYPE statement."""
        if not self.supports_type_objects() or not self.supports_create_type():
            raise UnsupportedFeatureError(self.name, "CREATE TYPE")
        if expr.if_not_exists and not self.supports_create_type_if_not_exists():
            raise UnsupportedFeatureError(self.name, "CREATE TYPE IF NOT EXISTS")
        if expr.or_replace and not self.supports_create_type_or_replace():
            raise UnsupportedFeatureError(self.name, "CREATE OR REPLACE TYPE")
        if not self.supports_type_definition(type(expr.definition)):
            raise UnsupportedFeatureError(
                self.name,
                f"TYPE definition {expr.definition.definition_kind}",
            )
        definition_sql, definition_params = expr.definition.to_sql()
        if expr.schema_name is None:
            name_sql = self.format_identifier(expr.type_name)
        else:
            name_sql = (
                f"{self.format_identifier(expr.schema_name)}."
                f"{self.format_identifier(expr.type_name)}"
            )
        parts = ["CREATE"]
        if expr.or_replace:
            parts.append("OR REPLACE")
        parts.append("TYPE")
        if expr.if_not_exists:
            parts.append("IF NOT EXISTS")
        parts.extend((name_sql, definition_sql))
        return " ".join(parts), tuple(definition_params)

    def format_alter_type_statement(
        self,
        expr: "AlterTypeExpression",
    ) -> Tuple[str, tuple]:
        """Format an ALTER TYPE statement."""
        if not self.supports_type_objects() or not self.supports_alter_type():
            raise UnsupportedFeatureError(self.name, "ALTER TYPE")
        if expr.if_exists and not self.supports_alter_type_if_exists():
            raise UnsupportedFeatureError(self.name, "ALTER TYPE IF EXISTS")
        if len(expr.actions) > 1 and not self.supports_multiple_type_alter_actions():
            raise UnsupportedFeatureError(self.name, "multiple ALTER TYPE actions")
        action_parts = []
        action_params = []
        for action in expr.actions:
            if not self.supports_type_alter_action(type(action)):
                raise UnsupportedFeatureError(
                    self.name,
                    f"ALTER TYPE action {action.action_kind}",
                )
            action_sql, params = action.to_sql()
            action_parts.append(action_sql)
            action_params.extend(params)
        if expr.schema_name is None:
            name_sql = self.format_identifier(expr.type_name)
        else:
            name_sql = (
                f"{self.format_identifier(expr.schema_name)}."
                f"{self.format_identifier(expr.type_name)}"
            )
        parts = ["ALTER TYPE"]
        if expr.if_exists:
            parts.append("IF EXISTS")
        parts.append(name_sql)
        parts.append(", ".join(action_parts))
        return " ".join(parts), tuple(action_params)

    def format_drop_type_statement(
        self,
        expr: "DropTypeExpression",
    ) -> Tuple[str, tuple]:
        """Format a DROP TYPE statement."""
        if not self.supports_type_objects() or not self.supports_drop_type():
            raise UnsupportedFeatureError(self.name, "DROP TYPE")
        if expr.if_exists and not self.supports_drop_type_if_exists():
            raise UnsupportedFeatureError(self.name, "DROP TYPE IF EXISTS")
        if expr.schema_name is None:
            name_sql = self.format_identifier(expr.type_name)
        else:
            name_sql = (
                f"{self.format_identifier(expr.schema_name)}."
                f"{self.format_identifier(expr.type_name)}"
            )
        parts = ["DROP TYPE"]
        if expr.if_exists:
            parts.append("IF EXISTS")
        parts.append(name_sql)
        return " ".join(parts), ()

    def format_type_definition(
        self,
        expr: "TypeDefinition",
    ) -> Tuple[str, tuple]:
        """Reject TYPE definitions until a backend supplies a grammar."""
        raise UnsupportedFeatureError(
            self.name,
            f"TYPE definition {getattr(expr, 'definition_kind', type(expr).__name__)}",
        )

    def format_type_alter_action(
        self,
        expr: "TypeAlterAction",
    ) -> Tuple[str, tuple]:
        """Reject ALTER TYPE actions until a backend supplies a grammar."""
        raise UnsupportedFeatureError(
            self.name,
            f"ALTER TYPE action {getattr(expr, 'action_kind', type(expr).__name__)}",
        )


__all__ = ["UserDefinedTypeMixin"]
