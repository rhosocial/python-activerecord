# src/rhosocial/activerecord/backend/dialect/mixins/drop_type_mixin.py
"""Per-statement mixin for DropTypeSupport. Members/order/signature mirror the protocol."""

from typing import Tuple, Type as TypingType, TYPE_CHECKING
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.objects import Type
from rhosocial.activerecord.backend.expression.statements import TypeAlterAction, TypeDefinition

class DropTypeMixin:
    def supports_drop_type(self) -> bool:
            """Whether DROP TYPE is supported."""
            return False

    def supports_drop_type_if_exists(self) -> bool:
            """Whether DROP TYPE IF EXISTS is supported."""
            return False

    def format_drop_type_statement(
            self,
            expr: "DropTypeStatement",
        ) -> Tuple[str, tuple]:
            """Format a DROP TYPE statement.

            Raises:
                TypeError: ``DropTypeStatement.type`` is not a Type. Another object
                kind would have had its own name rendered as the type's.
            """
            if not isinstance(expr.type, Type):
                raise TypeError(
                    f"DropTypeStatement.type must be a Type, "
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
