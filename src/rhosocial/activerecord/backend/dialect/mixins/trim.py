# src/rhosocial/activerecord/backend/dialect/mixins/trim.py
"""Dialect mixin for the TRIM family of string expressions.

One node, one formatter: :class:`~...expression.advanced_functions.TrimExpression`
renders through :meth:`format_trim_expression`, and the default is the standard
``TRIM([BOTH|LEADING|TRAILING] [chars] FROM expr)`` form. A dialect that spells
it differently overrides the formatter rather than assembling SQL by hand --
SQLite does exactly that, because it parses no ``trim(... from ...)`` syntax
at all.
"""
from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.advanced_functions import TrimExpression


class TrimMixin:
    """Mixin rendering the standard TRIM expression."""

    def format_trim_expression(self, expr: "TrimExpression") -> Tuple[str, Tuple]:
        """Format a ``TRIM`` node in the standard SQL form.

        Args:
            expr: Trim expression exposing ``expr``, ``chars``, ``direction``
                and an optional ``alias``.

        Returns:
            Tuple of (SQL string, parameters tuple), carrying the operands'
            parameters in order.
        """
        target_sql, target_params = expr.expr.to_sql()
        if expr.chars is not None:
            chars_sql, chars_params = expr.chars.to_sql()
            sql = f"TRIM({expr.direction} {chars_sql} FROM {target_sql})"
            params = tuple(target_params) + tuple(chars_params)
        else:
            sql = f"TRIM({expr.direction} FROM {target_sql})"
            params = tuple(target_params)
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, params
