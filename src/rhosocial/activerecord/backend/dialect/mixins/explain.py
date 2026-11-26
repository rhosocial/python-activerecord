# src/rhosocial/activerecord/backend/dialect/mixins/explain.py
"""EXPLAIN statement mixin.

Provides capability probes and a generic formatter for EXPLAIN expressions,
with hooks for dialect-specific options such as ANALYZE and FORMAT.
"""
from typing import Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.statements import ExplainStatement


class ExplainMixin:
    """Format EXPLAIN statements and advertise EXPLAIN capabilities.

    The generic formatter appends only the options a backend recognizes;
    dialects may override the probes to enable ANALYZE or specific formats.
    """

    def supports_explain_plan(self) -> bool:
        """Whether EXPLAIN of any form is supported (defaults to False)."""
        return False

    def supports_explain_analyze(self) -> bool:
        """Whether EXPLAIN ANALYZE is supported (defaults to False)."""
        return False

    def supports_explain_verbose(self) -> bool:
        """Whether the EXPLAIN VERBOSE option is supported (defaults to False)."""
        return False

    def supports_explain_costs(self) -> bool:
        """Whether EXPLAIN accepts the COSTS option (defaults to False)."""
        return False

    def supports_explain_buffers(self) -> bool:
        """Whether the EXPLAIN BUFFERS option is supported (defaults to False)."""
        return False

    def supports_explain_timing(self) -> bool:
        """Whether the EXPLAIN TIMING option is supported (defaults to False)."""
        return False

    def supports_explain_settings(self) -> bool:
        """Whether the EXPLAIN SETTINGS option is supported (defaults to False)."""
        return False

    def supports_explain_wal(self) -> bool:
        """Whether the EXPLAIN WAL option is supported (defaults to False)."""
        return False

    def supports_explain_format_text(self) -> bool:
        """Whether EXPLAIN FORMAT TEXT is supported (defaults to False)."""
        return False

    def supports_explain_format_json(self) -> bool:
        """Whether EXPLAIN FORMAT JSON is supported (defaults to False)."""
        return False

    def supports_explain_format_xml(self) -> bool:
        """Whether EXPLAIN FORMAT XML is supported (defaults to False)."""
        return False

    def supports_explain_format_yaml(self) -> bool:
        """Whether EXPLAIN FORMAT YAML is supported (defaults to False)."""
        return False

    def supports_explain_format_tree(self) -> bool:
        """Whether EXPLAIN FORMAT TREE is supported (defaults to False)."""
        return False

    def supports_explain_format_traditional(self) -> bool:
        """Whether EXPLAIN FORMAT TRADITIONAL is supported (defaults to False)."""
        return False

    def format_explain_statement(self, expr: "ExplainStatement") -> Tuple[str, tuple]:
        """Format an EXPLAIN statement.

        Args:
            expr: The ExplainStatement to render, including the wrapped
                statement and optional options.

        Returns:
            A ``(sql, params)`` tuple where ``params`` are the parameters of
            the explained statement.
        """
        statement_sql, statement_params = expr.statement.to_sql()
        options = expr.options
        if options is None:
            return f"EXPLAIN {statement_sql}", statement_params

        parts = ["EXPLAIN"]
        # Import here to avoid circular imports
        from ...expression.statements import ExplainType

        # Determine if ANALYZE should be included based on the type field
        # If type is ANALYZE, or if the boolean analyze field is True
        if options.type == ExplainType.ANALYZE or options.analyze:
            if not self.supports_explain_analyze():
                raise UnsupportedFeatureError(self.name, "EXPLAIN ANALYZE")
            parts.append("ANALYZE")
        if options.format:
            from ...expression.statements import ExplainFormat

            probe = {
                ExplainFormat.TEXT: "supports_explain_format_text",
                ExplainFormat.JSON: "supports_explain_format_json",
                ExplainFormat.XML: "supports_explain_format_xml",
                ExplainFormat.YAML: "supports_explain_format_yaml",
                ExplainFormat.TREE: "supports_explain_format_tree",
                ExplainFormat.TRADITIONAL: "supports_explain_format_traditional",
            }[options.format]
            if not getattr(self, probe)():
                raise UnsupportedFeatureError(
                    self.name, f"EXPLAIN FORMAT {options.format.value}"
                )
            parts.append(f"FORMAT {options.format.value}")
        # Only show costs=False if it's explicitly set to False, since True is default
        if not options.costs:
            if not self.supports_explain_costs():
                raise UnsupportedFeatureError(self.name, "EXPLAIN COSTS")
            parts.append("COSTS OFF")
        if options.buffers:
            if not self.supports_explain_buffers():
                raise UnsupportedFeatureError(self.name, "EXPLAIN BUFFERS")
            parts.append("BUFFERS")
        if options.timing and options.analyze:
            if not self.supports_explain_timing():
                raise UnsupportedFeatureError(self.name, "EXPLAIN TIMING")
            parts.append("TIMING ON")
        if options.verbose:
            if not self.supports_explain_verbose():
                raise UnsupportedFeatureError(self.name, "EXPLAIN VERBOSE")
            parts.append("VERBOSE")
        if options.settings:
            if not self.supports_explain_settings():
                raise UnsupportedFeatureError(self.name, "EXPLAIN SETTINGS")
            parts.append("SETTINGS")
        if options.wal:
            if not self.supports_explain_wal():
                raise UnsupportedFeatureError(self.name, "EXPLAIN WAL")
            parts.append("WAL")
        return f"{' '.join(parts)} {statement_sql}", statement_params
