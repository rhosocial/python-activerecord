# src/rhosocial/activerecord/backend/dialect/mixins/datetime.py
from typing import Tuple

from ...expression import bases


class DateTimeMixin:
    """Mixin for date/time expression formatting."""

    def format_extract_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        source_sql, source_params = expr.source.to_sql()
        sql = f"EXTRACT({expr.field.value.upper()} FROM {source_sql})"
        return self._apply_value_expression_modifiers(sql, source_params, expr)

    def format_date_part_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        return self.format_extract_expression(expr)

    def format_date_trunc_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        from ...dialect.base import SQLDialectBase
        source_sql, source_params = expr.source.to_sql()
        field = SQLDialectBase._escape_sql_string(expr.field.value)
        sql = f"DATE_TRUNC('{field}', {source_sql})"
        return self._apply_value_expression_modifiers(sql, source_params, expr)

    def format_interval_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        from ...dialect.base import SQLDialectBase
        value = SQLDialectBase._escape_sql_string(str(expr.value))
        sql = f"INTERVAL '{value}' {expr.unit.value.upper()}"
        return self._apply_value_expression_modifiers(sql, (), expr)

    def format_datetime_add_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        source_sql, source_params = expr.source.to_sql()
        interval_sql, interval_params = expr.interval.to_sql()
        sql = f"{source_sql} + {interval_sql}"
        return self._apply_value_expression_modifiers(sql, source_params + interval_params, expr)

    def format_datetime_subtract_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        source_sql, source_params = expr.source.to_sql()
        interval_sql, interval_params = expr.interval.to_sql()
        sql = f"{source_sql} - {interval_sql}"
        return self._apply_value_expression_modifiers(sql, source_params + interval_params, expr)

    def format_datetime_diff_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        from ..exceptions import UnsupportedFeatureError
        raise UnsupportedFeatureError(
            self.name,
            f"date_diff({expr.unit.value})",
            "Override format_datetime_diff_expression() in the target dialect.",
        )
