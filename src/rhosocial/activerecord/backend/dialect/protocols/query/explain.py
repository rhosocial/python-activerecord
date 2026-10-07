# src/rhosocial/activerecord/backend/dialect/protocols/query/explain.py
"""ExplainSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression import ExplainExpression


@runtime_checkable
class ExplainSupport(Protocol):
    """Protocol for EXPLAIN statement support."""

    def supports_explain_plan(self) -> bool:
        """Whether the engine accepts the form ``explain_plan``.

        Defaults to ``False``.
        """
        ...  # pragma: no cover

    def supports_explain_analyze(self) -> bool:
        """Whether EXPLAIN ANALYZE is supported."""
        ...  # pragma: no cover

    def supports_explain_format(self, format_type: str) -> bool:
        """
        Check if specific EXPLAIN format is supported.

        Args:
            format_type: Format type (e.g., 'JSON', 'XML', 'YAML')

        Returns:
            True if format is supported
        """
        ...  # pragma: no cover

    def format_explain_statement(self, expr: "ExplainExpression") -> Tuple[str, tuple]:
        """
        Format EXPLAIN statement.

        Args:
            expr: ExplainExpression object

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted statement.
        """
        ...  # pragma: no cover
