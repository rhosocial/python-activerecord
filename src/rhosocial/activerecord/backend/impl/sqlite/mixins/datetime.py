# src/rhosocial/activerecord/backend/impl/sqlite/mixins/datetime.py
"""
SQLite-specific Datetime implementation.

This module provides the SQLiteDateTimeMixin class.
"""

import re
from typing import Tuple, TYPE_CHECKING
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression import bases
    from rhosocial.activerecord.backend.expression.collation import CollateExpression

_COLLATION_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class SQLiteDateTimeMixin:
    """SQLite-specific date/time expression formatting."""

    _DATETIME_EXTRACT_FORMATS = {
        "year": "%Y",
        "month": "%m",
        "week": "%W",
        "day": "%d",
        "hour": "%H",
        "minute": "%M",
        "second": "%S",
        "dow": "%w",
        "doy": "%j",
    }

    _DATETIME_TRUNC_FORMATS = {
        "hour": "%Y-%m-%d %H:00:00",
        "minute": "%Y-%m-%d %H:%M:00",
        "second": "%Y-%m-%d %H:%M:%S",
    }

    def format_extract_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        """Format datetime field extraction for SQLite."""
        source_sql, source_params = expr.source.to_sql()
        field = expr.field.value
        fmt = self._DATETIME_EXTRACT_FORMATS.get(field)
        if fmt is None:
            raise UnsupportedFeatureError(self.name, f"EXTRACT({field})")
        sql = f"CAST(strftime('{fmt}', {source_sql}) AS INTEGER)"
        return self._apply_value_expression_modifiers(sql, source_params, expr)

    def format_date_part_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        """Format date_part using SQLite strftime."""
        return self.format_extract_expression(expr)

    def format_date_trunc_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        """Format date_trunc using SQLite datetime/strftime functions."""
        source_sql, source_params = expr.source.to_sql()
        field = expr.field.value
        if field in {"year", "month", "day"}:
            sql = f"datetime({source_sql}, 'start of {field}')"
        elif field in self._DATETIME_TRUNC_FORMATS:
            fmt = self._DATETIME_TRUNC_FORMATS[field]
            sql = f"strftime('{fmt}', {source_sql})"
        else:
            raise UnsupportedFeatureError(self.name, f"DATE_TRUNC({field})")
        return self._apply_value_expression_modifiers(sql, source_params, expr)

    def format_interval_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        """SQLite has no standalone interval literal."""
        raise UnsupportedFeatureError(
            self.name,
            "standalone INTERVAL literal",
            "Use date_add/date_sub so SQLite can render the interval as a datetime modifier.",
        )

    @staticmethod
    def format_sqlite_interval_modifier(expr, sign: str) -> str:
        value = expr.value * 7 if expr.unit.value == "week" else expr.value
        unit = "day" if expr.unit.value == "week" else expr.unit.value
        return f"{sign}{value:g} {unit}"

    def format_datetime_add_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        """Format datetime interval addition using SQLite modifiers."""
        source_sql, source_params = expr.source.to_sql()
        modifier = self.format_sqlite_interval_modifier(expr.interval, "+")
        sql = f"datetime({source_sql}, ?)"
        return self._apply_value_expression_modifiers(sql, source_params + (modifier,), expr)

    def format_datetime_subtract_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        """Format datetime interval subtraction using SQLite modifiers."""
        source_sql, source_params = expr.source.to_sql()
        modifier = self.format_sqlite_interval_modifier(expr.interval, "-")
        sql = f"datetime({source_sql}, ?)"
        return self._apply_value_expression_modifiers(sql, source_params + (modifier,), expr)

    def format_datetime_diff_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        """Format datetime difference using SQLite julianday."""
        start_sql, start_params = expr.start.to_sql()
        end_sql, end_params = expr.end.to_sql()
        field = expr.unit.value
        multipliers = {
            "day": "1",
            "hour": "24",
            "minute": "1440",
            "second": "86400",
        }
        multiplier = multipliers.get(field)
        if multiplier is None:
            raise UnsupportedFeatureError(self.name, f"date_diff({field})")
        base_sql = f"(julianday({end_sql}) - julianday({start_sql}))"
        sql = base_sql if multiplier == "1" else f"({base_sql} * {multiplier})"
        return self._apply_value_expression_modifiers(sql, start_params + end_params, expr)

    def supports_collate_expression(self) -> bool:
        """SQLite supports expression-level COLLATE."""
        return True

    def validate_collation_name(self, expr: "CollateExpression") -> str:
        """Validate SQLite collation names and return their SQL representation."""
        if "schema" in expr.collation_options:
            raise UnsupportedFeatureError(self.name, "schema-qualified COLLATE")
        if expr.collation_options:
            unsupported = ", ".join(sorted(expr.collation_options))
            raise UnsupportedFeatureError(self.name, f"COLLATE options: {unsupported}")
        if not _COLLATION_NAME_RE.fullmatch(expr.collation_name):
            raise ValueError(f"Unsupported SQLite collation: {expr.collation_name!r}")
        return expr.collation_name


# =============================================================================
# SQLiteDDLColumnMixin — column constraint and column definition formatting
# =============================================================================

