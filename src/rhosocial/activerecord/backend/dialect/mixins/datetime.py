# src/rhosocial/activerecord/backend/dialect/mixins/datetime.py
"""Date/time expression formatting (EXTRACT, DATE_TRUNC, intervals, arithmetic)."""

from typing import Tuple

from ...expression import bases
from ...expression.mixins import AliasableMixin


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
        if isinstance(expr, AliasableMixin) and expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, params

    def format_extract_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        """Format an ``EXTRACT(field FROM source)`` expression.

        Args:
            expr: The expression carrying ``field``, ``source`` and the
                ``spelling`` that was asked for.

        Returns:
            A ``(sql, params)`` tuple.

        The standard's spelling is ``EXTRACT(FIELD FROM source)``; the others
        name the field as a function of the source (``YEAR(source)``), which is
        the same answer and a different grammar. Both are this node, so which one
        is written is the formatter's business and the SQL stays whatever the
        call asked for.
        """
        source_sql, source_params = expr.source.to_sql()
        field = expr.field.value.upper()
        if expr.spelling == "EXTRACT":
            sql = f"EXTRACT({field} FROM {source_sql})"
        else:
            sql = f"{expr.spelling}({source_sql})"
        return self.apply_alias(sql, source_params, expr)

    def _format_temporal_now(self, name: str, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        """Render a current-time/timestamp node, with or without a precision.

        No precision means the bare keyword -- but "bare" is not the same as
        "without parentheses", and which one it is depends on the node:
        :attr:`niladic` says the standard writes this one without them
        (``CURRENT_TIMESTAMP``) or with them (``NOW``, where dropping them is a
        syntax error on MySQL). A precision is an argument either way, so it
        brings the parentheses with it.
        """
        if expr.precision is None:
            sql = name.upper() if expr.niladic else f"{name.upper()}()"
            return self.apply_alias(sql, (), expr)
        precision_sql, precision_params = expr.precision.to_sql()
        sql = f"{name.upper()}({precision_sql})"
        return self.apply_alias(sql, precision_params, expr)

    def format_now_function(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        """Render ``NOW()`` -- a timestamp."""
        return self._format_temporal_now("NOW", expr)

    def format_current_date_function(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        """Render ``CURRENT_DATE`` -- a date, with no precision to give it."""
        return self._format_temporal_now("CURRENT_DATE", expr)

    def format_current_time_function(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        """Render ``CURRENT_TIME`` -- a time of day."""
        return self._format_temporal_now("CURRENT_TIME", expr)

    def format_current_timestamp_function(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        """Render ``CURRENT_TIMESTAMP`` -- a timestamp."""
        return self._format_temporal_now("CURRENT_TIMESTAMP", expr)

    def format_localtimestamp_function(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        """Render ``LOCALTIMESTAMP`` -- a timestamp in the session's zone."""
        return self._format_temporal_now("LOCALTIMESTAMP", expr)

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
