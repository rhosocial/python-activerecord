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

    def format_alter_type_statement(
            self,
            expr: "AlterTypeStatement",
        ) -> Tuple[str, tuple]:
            """Format an ALTER TYPE statement carrying one action.

            One expression renders one statement, and that statement carries one
            action; a caller with several changes builds one statement per action
            and orders them itself.

            Raises:
                TypeError: ``AlterTypeStatement.type`` is not a Type. Another object
                kind would have had its own name rendered as the type's.
                TypeError: ``AlterTypeStatement.action`` is not an implementation
                of TypeAlterAction. Another kind has no action clause to dispatch
                on, so nothing would be rendered for it.
            """
            if not isinstance(expr.type, Type):
                raise TypeError(
                    f"AlterTypeStatement.type must be a Type, "
                    f"got {type(expr.type).__name__}"
                )

            # TypeAlterAction is an abstract base and cannot be instantiated, so
            # this reports that the entry is not an implementation of it
            # rather than naming a concrete type.
            if not isinstance(expr.action, TypeAlterAction):
                raise TypeError(
                    f"AlterTypeStatement.action must be a TypeAlterAction implementation, "
                    f"got {type(expr.action).__name__}"
                )
            if not self.supports_type_objects() or not self.supports_alter_type():
                raise UnsupportedFeatureError(self.name, "ALTER TYPE")
            if expr.if_exists and not self.supports_alter_type_if_exists():
                raise UnsupportedFeatureError(self.name, "ALTER TYPE IF EXISTS")
            action_sql, action_params = expr.action.to_sql()
            name_sql = expr.type.to_sql()[0]
            parts = ["ALTER TYPE"]
            if expr.if_exists:
                parts.append("IF EXISTS")
            parts.append(name_sql)
            parts.append(action_sql)
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
