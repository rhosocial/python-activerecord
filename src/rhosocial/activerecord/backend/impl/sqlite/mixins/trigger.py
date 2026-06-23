# src/rhosocial/activerecord/backend/impl/sqlite/mixins/trigger.py
"""
SQLite-specific Trigger implementation.

This module provides the SQLiteTriggerMixin class.
"""


class SQLiteTriggerMixin:
    """SQLite trigger DDL formatting."""

    def supports_trigger(self) -> bool:
        """SQLite supports triggers."""
        return True

    def supports_create_trigger(self) -> bool:
        """SQLite supports CREATE TRIGGER."""
        return True

    def supports_drop_trigger(self) -> bool:
        """SQLite supports DROP TRIGGER."""
        return True

    def supports_instead_of_trigger(self) -> bool:
        """SQLite supports INSTEAD OF triggers (for views)."""
        return True

    def supports_statement_trigger(self) -> bool:
        """SQLite does NOT support FOR EACH STATEMENT triggers."""
        return False

    def supports_trigger_referencing(self) -> bool:
        """SQLite supports referencing OLD and NEW rows."""
        return True

    def supports_trigger_when(self) -> bool:
        """SQLite supports WHEN condition in triggers."""
        return True

    def supports_trigger_if_not_exists(self) -> bool:
        """SQLite supports CREATE TRIGGER IF NOT EXISTS."""
        return True

    def format_create_trigger_statement(self, expr):
        """Format CREATE TRIGGER statement for SQLite."""
        from rhosocial.activerecord.backend.expression.statements import TriggerLevel

        parts = ["CREATE TRIGGER"]

        if expr.if_not_exists:
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

        if expr.level == TriggerLevel.ROW:
            parts.append("FOR EACH ROW")

        all_params = []
        if expr.condition:
            cond_sql, cond_params = expr.condition.to_sql()
            parts.append(f"WHEN ({cond_sql})")
            all_params.extend(cond_params)

        parts.append("BEGIN")
        parts.append(f"SELECT {self.format_identifier(expr.function_name)}();")
        parts.append("END")

        return " ".join(parts), tuple(all_params)

    def format_drop_trigger_statement(self, expr):
        """Format DROP TRIGGER statement for SQLite."""
        parts = ["DROP TRIGGER"]

        if expr.if_exists:
            parts.append("IF EXISTS")

        parts.append(self.format_identifier(expr.trigger_name))

        return " ".join(parts), ()


# =============================================================================
# SQLiteTransactionMixin — transaction control
# =============================================================================

