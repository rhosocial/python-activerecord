# src/rhosocial/activerecord/backend/dialect/mixins/string_ops.py
"""Dialect mixins for the string operations that are nodes rather than calls.

One node, one formatter, and the default is the spelling the majority of
backends share natively (measured 2026-10-09): ``REPEAT`` on PostgreSQL, MySQL,
MariaDB, ClickHouse and BigQuery, ``LPAD``/``RPAD`` on all of those plus
Oracle, Firebird and Snowflake. A dialect that lacks the function overrides the
formatter with an emulation **composed from ordinary nodes** -- SQLite does
exactly that -- rather than the factory assembling a SQL string no hook could
ever reach.
"""
from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.advanced_functions import (
        LpadExpression,
        RepeatExpression,
        RpadExpression,
    )


class RepeatMixin:
    """Mixin rendering ``REPEAT(expr, count)`` in the common spelling."""

    def format_repeat_expression(self, expr: "RepeatExpression") -> Tuple[str, tuple]:
        """Format a repeat node as ``REPEAT(expr, count)``.

        Args:
            expr: Repeat expression exposing ``expr``, ``count`` and ``alias``.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        expr_sql, expr_params = expr.expr.to_sql()
        count_sql, count_params = expr.count.to_sql()
        sql = f"REPEAT({expr_sql}, {count_sql})"
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, tuple(expr_params) + tuple(count_params)


class LpadMixin:
    """Mixin rendering ``LPAD(expr, length, pad)`` in the common spelling."""

    def format_lpad_expression(self, expr: "LpadExpression") -> Tuple[str, tuple]:
        """Format a left-pad node as ``LPAD(expr, length, pad)``.

        Args:
            expr: Pad expression exposing ``expr``, ``length``, ``pad`` and
                ``alias``.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        expr_sql, expr_params = expr.expr.to_sql()
        length_sql, length_params = expr.length.to_sql()
        pad_sql, pad_params = expr.pad.to_sql()
        sql = f"LPAD({expr_sql}, {length_sql}, {pad_sql})"
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, tuple(expr_params) + tuple(length_params) + tuple(pad_params)


class RpadMixin:
    """Mixin rendering ``RPAD(expr, length, pad)`` in the common spelling."""

    def format_rpad_expression(self, expr: "RpadExpression") -> Tuple[str, tuple]:
        """Format a right-pad node as ``RPAD(expr, length, pad)``.

        Args:
            expr: Pad expression exposing ``expr``, ``length``, ``pad`` and
                ``alias``.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        expr_sql, expr_params = expr.expr.to_sql()
        length_sql, length_params = expr.length.to_sql()
        pad_sql, pad_params = expr.pad.to_sql()
        sql = f"RPAD({expr_sql}, {length_sql}, {pad_sql})"
        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, tuple(expr_params) + tuple(length_params) + tuple(pad_params)
