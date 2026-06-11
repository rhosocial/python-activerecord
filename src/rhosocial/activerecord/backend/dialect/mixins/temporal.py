# src/rhosocial/activerecord/backend/dialect/mixins/temporal.py
from typing import Any, Dict, Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.query_parts import QualifyClause


class TemporalTableMixin:
    """Mixin for temporal table support."""

    def supports_temporal_tables(self) -> bool:
        """Whether temporal tables are supported."""
        return False

    def format_temporal_options(self, options: Dict[str, Any]) -> Tuple[str, tuple]:
        """Format temporal table options."""
        if not options:
            raise ValueError(
                "Temporal options cannot be empty. If no temporal options are needed, "
                "don't call format_temporal_options."
            )
        sql_parts, params = ["FOR SYSTEM_TIME"], []
        # Add temporal options to SQL parts based on the options provided
        for key, value in options.items():
            sql_parts.append(f"{key.upper()} {self.get_parameter_placeholder()}")
            params.append(value)
        return " ".join(sql_parts), tuple(params)


class QualifyClauseMixin:
    """Mixin for QUALIFY clause support."""

    def supports_qualify_clause(self) -> bool:
        """Whether QUALIFY clause is supported."""
        return False

    def format_qualify_clause(self, clause: "QualifyClause") -> Tuple[str, tuple]:
        """Format QUALIFY clause."""
        if not self.supports_qualify_clause():
            raise UnsupportedFeatureError(self.name, "QUALIFY clause")

        condition_sql, condition_params = clause.condition.to_sql()
        return f"QUALIFY {condition_sql}", condition_params
