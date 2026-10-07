# src/rhosocial/activerecord/backend/dialect/mixins/user_defined_type.py
"""Generic user-defined type DDL support."""

from typing import Tuple, Type as TypingType, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError
from ...expression.objects import Type
from ...expression.statements.ddl_type import TypeAlterAction, TypeDefinition

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

    def supported_type_definitions(self) -> Tuple[TypingType["TypeDefinition"], ...]:
        """Return the concrete type-definition classes this dialect renders."""
        return ()

    def supports_type_definition(
        self,
        definition_type: TypingType["TypeDefinition"],
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
        action_type: TypingType["TypeAlterAction"],
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
        """Format a CREATE TYPE statement.

        Raises:
            TypeError: ``CreateTypeExpression.type`` is not a Type. Another object
            kind would have had its own name rendered as the type's.
            TypeError: ``CreateTypeExpression.definition`` is not an implementation
            of TypeDefinition. Without a definition there is no body to render, so
            the statement would name a type and stop.
        """
        if not isinstance(expr.type, Type):
            raise TypeError(
                f"CreateTypeExpression.type must be a Type, "
                f"got {type(expr.type).__name__}"
            )

        # TypeDefinition is an abstract base and cannot be instantiated, so this
        # reports that the slot does not hold an implementation of it
        # rather than naming a concrete type.
        if not isinstance(expr.definition, TypeDefinition):
            raise TypeError(
                f"CreateTypeExpression.definition must be a TypeDefinition, "
                f"got {type(expr.definition).__name__}"
            )
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
        name_sql = expr.type.to_sql()[0]
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
        """Format an ALTER TYPE statement.

        Raises:
            TypeError: ``AlterTypeExpression.type`` is not a Type. Another object
            kind would have had its own name rendered as the type's.
            TypeError: An entry of ``AlterTypeExpression.actions`` is not an
            implementation of TypeAlterAction. An entry of another kind has no
            action clause to dispatch on, so nothing would be rendered for it.
        """
        if not isinstance(expr.type, Type):
            raise TypeError(
                f"AlterTypeExpression.type must be a Type, "
                f"got {type(expr.type).__name__}"
            )

        # TypeAlterAction is an abstract base and cannot be instantiated, so
        # this reports that the entry is not an implementation of it
        # rather than naming a concrete type.
        for position, entry in enumerate(expr.actions):
            if not isinstance(entry, TypeAlterAction):
                raise TypeError(
                    f"AlterTypeExpression.actions must hold TypeAlterAction implementations, "
                    f"got {type(entry).__name__} at position {position}"
                )
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
        name_sql = expr.type.to_sql()[0]
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
        """Format a DROP TYPE statement.

        Raises:
            TypeError: ``DropTypeExpression.type`` is not a Type. Another object
            kind would have had its own name rendered as the type's.
        """
        if not isinstance(expr.type, Type):
            raise TypeError(
                f"DropTypeExpression.type must be a Type, "
                f"got {type(expr.type).__name__}"
            )
        if not self.supports_type_objects() or not self.supports_drop_type():
            raise UnsupportedFeatureError(self.name, "DROP TYPE")
        if expr.if_exists and not self.supports_drop_type_if_exists():
            raise UnsupportedFeatureError(self.name, "DROP TYPE IF EXISTS")
        name_sql = expr.type.to_sql()[0]
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
