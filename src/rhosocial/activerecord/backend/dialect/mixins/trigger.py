# src/rhosocial/activerecord/backend/dialect/mixins/trigger.py
"""Trigger DDL support (SQL:1999 / SQL/PSM).

Provides capability probes for ``CREATE TRIGGER`` / ``DROP TRIGGER`` features
and the generic formatters that render them. Backends override the capability
probes to reflect their real feature set; the formatters raise
``UnsupportedFeatureError`` when a requested feature is not advertised.
"""

from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.statements import (
        CreateTriggerExpression,
        DropTriggerExpression,
    )


class TriggerMixin:
    """Mixin for trigger DDL support (SQL:1999/PSM)."""

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

    def supports_drop_trigger(self) -> bool:
        """Whether ``DROP TRIGGER`` is supported.

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

    def supports_trigger_if_not_exists(self) -> bool:
        """Whether ``CREATE TRIGGER IF NOT EXISTS`` is supported.

        Defaults to ``False``.
        """
        return False

    def format_create_trigger_statement(self, expr: "CreateTriggerExpression") -> Tuple[str, tuple]:
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
            UnsupportedFeatureError: If the dialect does not support triggers.
        """
        from ..exceptions import UnsupportedFeatureError

        if not self.supports_trigger():
            raise UnsupportedFeatureError(self.name, "triggers")

        parts = ["CREATE TRIGGER"]

        if expr.if_not_exists and self.supports_trigger_if_not_exists():
            parts.append("IF NOT EXISTS")

        parts.append(self.format_identifier(expr.trigger_name))

        parts.append(expr.timing.value)

        if expr.update_columns:
            cols = ", ".join(self.format_identifier(c) for c in expr.update_columns)
            events_str = f"UPDATE OF {cols}"
        else:
            events_str = " OR ".join(e.value for e in expr.events)
        parts.append(events_str)

        parts.append("ON")
        parts.append(self.format_identifier(expr.table_name))

        if expr.referencing and self.supports_trigger_referencing():
            parts.append(expr.referencing)

        parts.append(expr.level.value)

        all_params = []
        if expr.condition and self.supports_trigger_when():
            cond_sql, cond_params = expr.condition.to_sql()
            parts.append(f"WHEN ({cond_sql})")
            all_params.extend(cond_params)

        parts.append("EXECUTE")
        parts.append(self.format_identifier(expr.function_name))

        return " ".join(parts), tuple(all_params)

    def format_drop_trigger_statement(self, expr: "DropTriggerExpression") -> Tuple[str, tuple]:
        """Format a ``DROP TRIGGER`` statement per SQL:1999.

        Args:
            expr: The trigger expression carrying the trigger name and an
                optional target table.

        Returns:
            A ``(sql, params)`` tuple.

        Raises:
            UnsupportedFeatureError: If the dialect does not support triggers.
        """
        from ..exceptions import UnsupportedFeatureError

        if not self.supports_trigger():
            raise UnsupportedFeatureError(self.name, "triggers")

        parts = ["DROP TRIGGER"]

        if expr.if_exists:
            parts.append("IF EXISTS")

        parts.append(self.format_identifier(expr.trigger_name))

        if expr.table_name:
            parts.append("ON")
            parts.append(self.format_identifier(expr.table_name))

        return " ".join(parts), ()
