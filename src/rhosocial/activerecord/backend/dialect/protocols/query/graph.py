# src/rhosocial/activerecord/backend/dialect/protocols/graphsupport.py
"""GraphSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression import (
        GraphEdge,
        GraphVertex,
        MatchClause,
        PathPattern,
        QuantifiedPath,
    )


@runtime_checkable
class GraphSupport(Protocol):
    """Protocol for graph query (MATCH) support."""

    def supports_graph_match(self) -> bool:
        """Whether graph query MATCH clause is supported."""
        ...  # pragma: no cover

    def supports_quantified_path(self) -> bool:
        """Whether variable-length (quantified) path patterns are supported.

        Quantified paths use ``+``, ``*``, or ``{n,m}`` quantifiers on
        edges, e.g. ``-[e IS "knows"]+``.
        """
        ...  # pragma: no cover

    def supports_comma_separated_patterns(self) -> bool:
        """Whether multiple comma-separated patterns in a single MATCH
        clause are supported.

        When ``True`` the dialect accepts ``MATCH (a)->(b), (b)->(c)``.
        """
        ...  # pragma: no cover

    def format_graph_vertex(self, expr: "GraphVertex") -> Tuple[str, tuple]:
        """
        Formats a graph expr expression.

        Args:
            expr: GraphVertex object.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
        ...  # pragma: no cover

    def format_graph_edge(self, expr: "GraphEdge") -> Tuple[str, tuple]:
        """
        Formats a graph expr expression.

        Args:
            expr: GraphEdge object.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
        ...  # pragma: no cover

    def format_quantified_path(self, expr: "QuantifiedPath") -> Tuple[str, tuple]:
        """Formats a expr (variable-length) path pattern."""
        ...  # pragma: no cover

    def format_path_pattern(self, expr: "PathPattern") -> Tuple[str, tuple]:
        """Formats a single path expr (sequence of vertices & edges)."""
        ...  # pragma: no cover

    def format_match_clause(self, expr: "MatchClause") -> Tuple[str, tuple]:
        """
        Formats a MATCH expr with one or more patterns.

        Args:
            expr: MatchClause object.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expr.
        """
        ...  # pragma: no cover
