# src/rhosocial/activerecord/backend/dialect/mixins/temporal.py
"""Temporal table formatting for the dialect layer.

Provides capability probes and SQL rendering for system-versioned temporal
tables. The QUALIFY clause support has been merged into DQLMixin.
"""
from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.datetime import TemporalOptionsExpression


class TemporalTableMixin:
    """Mixin for SYSTEM_TIME temporal table support."""

    def supports_temporal_tables(self) -> bool:
        """Whether temporal tables are supported.

        Defaults to False; dialects that support them override this.
        """
        return False

    def format_temporal_options(self, expr: "TemporalOptionsExpression") -> Tuple[str, tuple]:
        """Format temporal table options.

        Args:
            expr: Temporal options expression exposing an ``options`` mapping.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            ValueError: If no temporal options were provided.
        """
        if not expr.options:
            raise ValueError(
                "Temporal options cannot be empty. If no temporal options are needed, "
                "don't call format_temporal_options."
            )
        sql_parts, params = ["FOR SYSTEM_TIME"], []
        # Add temporal options to SQL parts based on the options provided
        for key, value in expr.options.items():
            sql_parts.append(f"{key.upper()} {self.get_parameter_placeholder()}")
            params.append(value)
        return " ".join(sql_parts), tuple(params)
