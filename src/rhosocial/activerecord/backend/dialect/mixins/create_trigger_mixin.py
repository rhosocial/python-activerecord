# src/rhosocial/activerecord/backend/dialect/mixins/create_trigger_mixin.py
"""Per-statement mixin for CreateTriggerSupport. Members/order/signature mirror the protocol."""

from typing import Tuple, TYPE_CHECKING
from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.expression.objects import Function, Table, Trigger

class CreateTriggerMixin:
    def supports_trigger(self) -> bool:
            """Whether triggers are supported.

            Defaults to ``False``; backends with trigger support override this.
            """
            return False

    def supports_create_trigger(self) -> bool:
            """Whether ``CREATE TRIGGER`` is supported.

            Defaults to ``False``.
            """
            return False

    def supports_trigger_if_not_exists(self) -> bool:
            """Whether ``CREATE TRIGGER IF NOT EXISTS`` is supported.

            Defaults to ``False``.
            """
            return False

    def supports_instead_of_trigger(self) -> bool:
            """Whether ``INSTEAD OF`` triggers are supported.

            Defaults to ``False``.
            """
            return False

    def supports_statement_trigger(self) -> bool:
            """Whether statement-level (``FOR EACH STATEMENT``) triggers are supported.

            Defaults to ``False``.
            """
            return False

    def supports_trigger_referencing(self) -> bool:
            """Whether the ``REFERENCING`` clause is supported.

            Defaults to ``False``.
            """
            return False

    def supports_trigger_when(self) -> bool:
            """Whether the ``WHEN (condition)`` clause is supported.

            Defaults to ``False``.
            """
            return False

    def format_create_trigger_statement(self, expr: "CreateTriggerStatement") -> Tuple[str, tuple]:
            """Format a ``CREATE TRIGGER`` statement per SQL:1999.

            Renders the optional ``IF NOT EXISTS`` qualifier, timing, events
            (or ``UPDATE OF`` columns), target table, optional ``REFERENCING``
            and ``WHEN`` clauses, and the executed function.

            Args:
                expr: The trigger expression carrying timing, events, table,
                    and the function to execute.

            Returns:
                A ``(sql, params)`` tuple.

            Raises:
                TypeError: ``CreateTriggerStatement.trigger`` is not a Trigger. Another
                object kind would have had its own name rendered as the trigger's.
                TypeError: ``CreateTriggerStatement.table`` is not a Table. Another
                object kind would have had its own name rendered as the watched table's.
                TypeError: ``CreateTriggerStatement.function`` is not a Function.
                Another object kind would have had its own name rendered as the trigger
                body's.
                UnsupportedFeatureError: If the dialect does not support triggers.
            """
            if not isinstance(expr.trigger, Trigger):
                raise TypeError(
                    f"CreateTriggerStatement.trigger must be a Trigger, "
                    f"got {type(expr.trigger).__name__}"
                )

            if not isinstance(expr.table, Table):
                raise TypeError(
                    f"CreateTriggerStatement.table must be a Table, " f"got {type(expr.table).__name__}"
                )

            if expr.body is not None:
                for statement in expr.body:
                    if not isinstance(statement, BaseExpression):
                        raise TypeError(
                            f"CreateTriggerStatement.body items must be expressions, "
                            f"got {type(statement).__name__}"
                        )
            elif not isinstance(expr.function, Function):
                raise TypeError(
                    f"CreateTriggerStatement.function must be a Function, "
                    f"got {type(expr.function).__name__}"
                )
            from ..exceptions import UnsupportedFeatureError

            if not self.supports_trigger():
                raise UnsupportedFeatureError(self.name, "triggers")

            parts = ["CREATE TRIGGER"]

            if expr.if_not_exists:
                if not self.supports_trigger_if_not_exists():
                    raise UnsupportedFeatureError(
                        self.name,
                        "CREATE TRIGGER IF NOT EXISTS",
                        f"{self.name} does not support CREATE TRIGGER IF NOT EXISTS.",
                    )
                parts.append("IF NOT EXISTS")

            parts.append(expr.trigger.to_sql()[0])

            parts.append(expr.timing.value)

            if expr.update_columns:
                cols = ", ".join(self.format_identifier(c) for c in expr.update_columns)
                events_str = f"UPDATE OF {cols}"
            else:
                events_str = " OR ".join(e.value for e in expr.events)
            parts.append(events_str)

            parts.append("ON")
            parts.append(expr.table.to_sql()[0])

            if expr.referencing:
                if not self.supports_trigger_referencing():
                    raise UnsupportedFeatureError(
                        self.name,
                        "CREATE TRIGGER REFERENCING",
                        f"{self.name} does not support CREATE TRIGGER REFERENCING.",
                    )
                parts.append(expr.referencing)

            parts.append(expr.level.value)

            all_params = []
            if expr.condition:
                if not self.supports_trigger_when():
                    raise UnsupportedFeatureError(
                        self.name,
                        "CREATE TRIGGER WHEN",
                        f"{self.name} does not support CREATE TRIGGER WHEN.",
                    )
                cond_sql, cond_params = expr.condition.to_sql()
                parts.append(f"WHEN ({cond_sql})")
                all_params.extend(cond_params)

            if expr.body is not None:
                parts.append("BEGIN")
                for statement in expr.body:
                    statement_sql, statement_params = statement.to_sql()
                    parts.append(f"{statement_sql};")
                    all_params.extend(statement_params)
                parts.append("END")
            else:
                parts.append("EXECUTE")
                parts.append(expr.function.to_sql()[0])

            return " ".join(parts), tuple(all_params)
