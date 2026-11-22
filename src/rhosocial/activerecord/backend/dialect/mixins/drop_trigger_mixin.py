# src/rhosocial/activerecord/backend/dialect/mixins/drop_trigger_mixin.py
"""Per-statement mixin for DropTriggerSupport. Members/order/signature mirror the protocol."""

from typing import Tuple, TYPE_CHECKING
from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.expression.objects import Function, Table, Trigger

class DropTriggerMixin:
    def supports_drop_trigger(self) -> bool:
            """Whether ``DROP TRIGGER`` is supported.

            Defaults to ``False``.
            """
            return False

    def supports_trigger_if_exists(self) -> bool:
            """Whether ``DROP TRIGGER IF EXISTS`` is supported.

            Defaults to ``False``.
            """
            return False

    def format_drop_trigger_statement(self, expr: "DropTriggerStatement") -> Tuple[str, tuple]:
            """Format a ``DROP TRIGGER`` statement per SQL:1999.

            Args:
                expr: The trigger expression carrying the trigger name and an
                    optional target table.

            Returns:
                A ``(sql, params)`` tuple.

            Raises:
                TypeError: ``DropTriggerStatement.trigger`` is not a Trigger. Another
                object kind would have had its own name rendered as the trigger's.
                TypeError: ``DropTriggerStatement.table`` is not a Table. Another
                object kind would have had its own name rendered as the table's.
                UnsupportedFeatureError: If the dialect does not support triggers.
            """
            if not isinstance(expr.trigger, Trigger):
                raise TypeError(
                    f"DropTriggerStatement.trigger must be a Trigger, "
                    f"got {type(expr.trigger).__name__}"
                )

            if expr.table is not None and not isinstance(expr.table, Table):
                raise TypeError(
                    f"DropTriggerStatement.table must be a Table, " f"got {type(expr.table).__name__}"
                )
            from ..exceptions import UnsupportedFeatureError

            if not self.supports_trigger():
                raise UnsupportedFeatureError(self.name, "triggers")

            parts = ["DROP TRIGGER"]

            if expr.if_exists:
                if not self.supports_trigger_if_exists():
                    raise UnsupportedFeatureError(
                        self.name,
                        "DROP TRIGGER IF EXISTS",
                        f"{self.name} does not support DROP TRIGGER IF EXISTS.",
                    )
                parts.append("IF EXISTS")

            parts.append(expr.trigger.to_sql()[0])

            if expr.table:
                parts.append("ON")
                parts.append(expr.table.to_sql()[0])

            return " ".join(parts), ()
