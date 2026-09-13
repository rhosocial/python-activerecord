# src/rhosocial/activerecord/backend/dialect/mixins/datetime.py
"""Date/time expression formatting (EXTRACT, DATE_TRUNC, intervals, arithmetic)."""

from typing import Tuple

from ...expression import bases


class DateTimeMixin:
    """Mixin for date/time expression formatting."""

    def apply_alias(self, sql: str, params: tuple, expr) -> Tuple[str, tuple]:
        """Append ``AS alias`` when the expression carries an alias.

        Args:
            sql: The rendered SQL fragment.
            params: The bind parameters for the fragment.
            expr: The expression whose optional ``alias`` is applied.

        Returns:
            A ``(sql, params)`` tuple, with the alias appended when present.
        """
        if getattr(expr, "alias", None):
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, params

    def format_extract_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        """Format an ``EXTRACT(field FROM source)`` expression.

        Args:
            expr: The expression carrying ``field`` and ``source``.

        Returns:
            A ``(sql, params)`` tuple.
        """
        source_sql, source_params = expr.source.to_sql()
        sql = f"EXTRACT({expr.field.value.upper()} FROM {source_sql})"
        return self.apply_alias(sql, source_params, expr)

    def format_date_part_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        """Format a ``DATE_PART`` expression as ``EXTRACT``.

        Args:
            expr: The expression carrying ``field`` and ``source``.

        Returns:
            A ``(sql, params)`` tuple.
        """
        return self.format_extract_expression(expr)

    def format_date_trunc_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        """Format a ``DATE_TRUNC(field, source)`` expression.

        Args:
            expr: The expression carrying ``field`` and ``source``.

        Returns:
            A ``(sql, params)`` tuple.
        """
        from ...dialect.base import SQLDialectBase
        source_sql, source_params = expr.source.to_sql()
        field = SQLDialectBase._escape_sql_string(expr.field.value)
        sql = f"DATE_TRUNC('{field}', {source_sql})"
        return self.apply_alias(sql, source_params, expr)

    def format_interval_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        """Format an ``INTERVAL 'value' unit`` expression.

        Args:
            expr: The expression carrying ``value`` and ``unit``.

        Returns:
            A ``(sql, params)`` tuple.
        """
        from ...dialect.base import SQLDialectBase
        value = SQLDialectBase._escape_sql_string(str(expr.value))
        sql = f"INTERVAL '{value}' {expr.unit.value.upper()}"
        return self.apply_alias(sql, (), expr)

    def format_datetime_add_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        """Format date/time addition (``source + interval``).

        Args:
            expr: The expression carrying ``source`` and ``interval``.

        Returns:
            A ``(sql, params)`` tuple.
        """
        source_sql, source_params = expr.source.to_sql()
        interval_sql, interval_params = expr.interval.to_sql()
        sql = f"{source_sql} + {interval_sql}"
        return self.apply_alias(sql, source_params + interval_params, expr)

    def format_datetime_subtract_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        """Format date/time subtraction (``source - interval``).

        Args:
            expr: The expression carrying ``source`` and ``interval``.

        Returns:
            A ``(sql, params)`` tuple.
        """
        source_sql, source_params = expr.source.to_sql()
        interval_sql, interval_params = expr.interval.to_sql()
        sql = f"{source_sql} - {interval_sql}"
        return self.apply_alias(sql, source_params + interval_params, expr)

    def format_datetime_diff_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        """Format a date/time difference.

        The core provides no generic syntax; dialects with native support
        (e.g. ``DATEDIFF``) override this method.

        Args:
            expr: The expression carrying the operand and ``unit``.

        Raises:
            UnsupportedFeatureError: Always, at the core layer.
        """
        from ..exceptions import UnsupportedFeatureError
        raise UnsupportedFeatureError(
            self.name,
            f"date_diff({expr.unit.value})",
            "Override format_datetime_diff_expression() in the target dialect.",
        )
