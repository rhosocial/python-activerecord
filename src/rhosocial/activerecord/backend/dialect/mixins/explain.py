# src/rhosocial/activerecord/backend/dialect/mixins/explain.py
from typing import Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.statements import ExplainExpression


class ExplainMixin:
    """Mixin for EXPLAIN statement support."""

    def supports_explain_analyze(self) -> bool:
        """Whether EXPLAIN ANALYZE is supported."""
        return False

    def supports_explain_format(self, format_type: str) -> bool:
        """
        Check if specific EXPLAIN format is supported.

        Args:
            format_type: Format type (e.g., 'JSON', 'XML', 'YAML')

        Returns:
            True if format is supported
        """
        return False

    def format_explain_statement(self, expr: "ExplainExpression") -> Tuple[str, tuple]:
        """Format EXPLAIN statement."""
        statement_sql, statement_params = expr.statement.to_sql()
        options = expr.options
        if options is None:
            return f"EXPLAIN {statement_sql}", statement_params

        parts = ["EXPLAIN"]
        # Import here to avoid circular imports
        from ...expression.statements import ExplainType

        # Determine if ANALYZE should be included based on the type field
        # If type is ANALYZE, or if the boolean analyze field is True
        if (hasattr(options, "type") and options.type == ExplainType.ANALYZE) or options.analyze:
            parts.append("ANALYZE")
        if options.format:
            parts.append(f"FORMAT {options.format.value.upper()}")
        # Only show costs=False if it's explicitly set to False, since True is default
        if not options.costs:
            parts.append("COSTS OFF")
        if options.buffers:
            parts.append("BUFFERS")
        if options.timing and options.analyze:
            parts.append("TIMING ON")
        if options.verbose:
            parts.append("VERBOSE")
        if options.settings:
            parts.append("SETTINGS")  # PostgreSQL-specific option, not SQL standard
        if options.wal:
            parts.append("WAL")  # PostgreSQL-specific option, not SQL standard

        return f"{' '.join(parts)} {statement_sql}", statement_params
