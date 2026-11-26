# src/rhosocial/activerecord/backend/dialect/mixins/alter_type_mixin.py
"""Per-statement mixin for AlterTypeSupport. Members/order/signature mirror the protocol."""

from typing import Tuple
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.objects import Type
from rhosocial.activerecord.backend.expression.statements.ddl_type import TypeAlterAction

class AlterTypeMixin:
    def supports_alter_type(self) -> bool:
            """Whether ALTER TYPE is supported."""
            return False

    def supports_alter_type_if_exists(self) -> bool:
            """Whether ALTER TYPE IF EXISTS is supported."""
            return False

    def supports_multiple_type_alter_actions(self) -> bool:
            """Whether one ALTER TYPE statement may contain multiple actions."""
            return False

    def format_alter_type_statement(
            self,
            expr: "AlterTypeStatement",
        ) -> Tuple[str, tuple]:
            """Format an ALTER TYPE statement.

            Raises:
                TypeError: ``AlterTypeStatement.type`` is not a Type. Another object
                kind would have had its own name rendered as the type's.
                TypeError: An entry of ``AlterTypeStatement.actions`` is not an
                implementation of TypeAlterAction. An entry of another kind has no
                action clause to dispatch on, so nothing would be rendered for it.
            """
            if not isinstance(expr.type, Type):
                raise TypeError(
                    f"AlterTypeStatement.type must be a Type, "
                    f"got {type(expr.type).__name__}"
                )

            # TypeAlterAction is an abstract base and cannot be instantiated, so
            # this reports that the entry is not an implementation of it
            # rather than naming a concrete type.
            for position, entry in enumerate(expr.actions):
                if not isinstance(entry, TypeAlterAction):
                    raise TypeError(
                        f"AlterTypeStatement.actions must hold TypeAlterAction implementations, "
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

    def format_type_alter_action(
            self,
            expr: "TypeAlterAction",
        ) -> Tuple[str, tuple]:
            """Reject ALTER TYPE actions until a backend supplies a grammar."""
            raise UnsupportedFeatureError(
                self.name,
                f"ALTER TYPE action {expr.action_kind}",
            )
