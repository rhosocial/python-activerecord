# src/rhosocial/activerecord/backend/dialect/protocols/query/explain.py
"""ExplainSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression import ExplainStatement


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

    def supports_explain_verbose(self) -> bool:
        """Whether the EXPLAIN VERBOSE option is supported."""
        ...  # pragma: no cover

    def supports_explain_costs(self) -> bool:
        """Whether EXPLAIN accepts the COSTS option."""
        ...  # pragma: no cover

    def supports_explain_buffers(self) -> bool:
        """Whether the EXPLAIN BUFFERS option is supported."""
        ...  # pragma: no cover

    def supports_explain_timing(self) -> bool:
        """Whether the EXPLAIN TIMING option is supported."""
        ...  # pragma: no cover

    def supports_explain_settings(self) -> bool:
        """Whether the EXPLAIN SETTINGS option is supported."""
        ...  # pragma: no cover

    def supports_explain_wal(self) -> bool:
        """Whether the EXPLAIN WAL option is supported."""
        ...  # pragma: no cover

    def supports_explain_format_text(self) -> bool:
        """Whether EXPLAIN FORMAT TEXT is supported."""
        ...  # pragma: no cover

    def supports_explain_format_json(self) -> bool:
        """Whether EXPLAIN FORMAT JSON is supported."""
        ...  # pragma: no cover

    def supports_explain_format_xml(self) -> bool:
        """Whether EXPLAIN FORMAT XML is supported."""
        ...  # pragma: no cover

    def supports_explain_format_yaml(self) -> bool:
        """Whether EXPLAIN FORMAT YAML is supported."""
        ...  # pragma: no cover

    def supports_explain_format_tree(self) -> bool:
        """Whether EXPLAIN FORMAT TREE is supported."""
        ...  # pragma: no cover

    def supports_explain_format_traditional(self) -> bool:
        """Whether EXPLAIN FORMAT TRADITIONAL is supported."""
        ...  # pragma: no cover

    def format_explain_statement(self, expr: "ExplainStatement") -> Tuple[str, tuple]:
        """
        Format EXPLAIN statement.

        Args:
            expr: ExplainStatement object

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted statement.
        """
        ...  # pragma: no cover
