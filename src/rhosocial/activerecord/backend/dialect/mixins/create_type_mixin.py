# src/rhosocial/activerecord/backend/dialect/mixins/create_type_mixin.py
"""Per-statement mixin for CreateTypeSupport. Members/order/signature mirror the protocol."""

from typing import Tuple, Type as TypingType, TYPE_CHECKING
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.objects import Type
from rhosocial.activerecord.backend.expression.statements.ddl_type import TypeAlterAction, TypeDefinition

class CreateTypeMixin:
    def supports_type_objects(self) -> bool:
            """Whether user-defined type objects are supported."""
            return False

    def supports_create_type(self) -> bool:
            """Whether CREATE TYPE is supported."""
            return False

    def supports_create_type_if_not_exists(self) -> bool:
            """Whether CREATE TYPE IF NOT EXISTS is supported."""
            return False

    def supports_create_type_or_replace(self) -> bool:
            """Whether CREATE OR REPLACE TYPE is supported."""
            return False

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

    def format_create_type_statement(
            self,
            expr: "CreateTypeStatement",
        ) -> Tuple[str, tuple]:
            """Format a CREATE TYPE statement.

            Raises:
                TypeError: ``CreateTypeStatement.type`` is not a Type. Another object
                kind would have had its own name rendered as the type's.
                TypeError: ``CreateTypeStatement.definition`` is not an implementation
                of TypeDefinition. Without a definition there is no body to render, so
                the statement would name a type and stop.
            """
            if not isinstance(expr.type, Type):
                raise TypeError(
                    f"CreateTypeStatement.type must be a Type, "
                    f"got {type(expr.type).__name__}"
                )

            # TypeDefinition is an abstract base and cannot be instantiated, so this
            # reports that the slot does not hold an implementation of it
            # rather than naming a concrete type.
            if not isinstance(expr.definition, TypeDefinition):
                raise TypeError(
                    f"CreateTypeStatement.definition must be a TypeDefinition, "
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

    def format_type_definition(
            self,
            expr: "TypeDefinition",
        ) -> Tuple[str, tuple]:
            """Reject TYPE definitions until a backend supplies a grammar."""
            raise UnsupportedFeatureError(
                self.name,
                f"TYPE definition {expr.definition_kind}",
            )


    def supported_type_definitions(self) -> Tuple[TypingType["TypeDefinition"], ...]:
        """Return the concrete type-definition classes this dialect renders."""
        return ()
