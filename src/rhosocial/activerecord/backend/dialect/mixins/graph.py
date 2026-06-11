# src/rhosocial/activerecord/backend/dialect/mixins/graph.py
import re
from typing import Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.graph import GraphEdgeDirection, MatchClause


class GraphMixin:
    """Mixin for graph query (MATCH) support."""

    def supports_graph_match(self) -> bool:
        """Whether graph query MATCH clause is supported."""
        return False

    def format_graph_vertex(self, variable: str, table: str) -> Tuple[str, tuple]:
        """
        Formats a graph vertex expression.

        Args:
            variable: The vertex variable name.
            table: The vertex table name.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
        if not self.supports_graph_match():
            raise UnsupportedFeatureError(self.name, "graph MATCH clause")

        # Validate variable name: only alphanumeric and underscore allowed.
        if not re.fullmatch(r"[A-Za-z0-9_]+", variable):
            raise ValueError(
                f"Invalid variable name '{variable}': must contain only alphanumeric characters and underscores."
            )

        sql = f"({variable} IS {self.format_identifier(table)})"
        return sql, ()

    def format_graph_edge(self, variable: str, table: str, direction: "GraphEdgeDirection") -> Tuple[str, tuple]:
        """
        Formats a graph edge expression.

        Args:
            variable: The edge variable name.
            table: The edge table name.
            direction: The edge direction.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
        if not self.supports_graph_match():
            raise UnsupportedFeatureError(self.name, "graph MATCH clause")

        # Validate variable name: only alphanumeric and underscore allowed.
        if not re.fullmatch(r"[A-Za-z0-9_]+", variable):
            raise ValueError(
                f"Invalid variable name '{variable}': must contain only alphanumeric characters and underscores."
            )

        from ...expression.graph import GraphEdgeDirection  # Import here to avoid circular import

        # For different directions, construct the correct syntax
        if direction == GraphEdgeDirection.RIGHT:
            # Right-directed: -[var IS table]->
            sql = f"-[{variable} IS {self.format_identifier(table)}]->"
        elif direction == GraphEdgeDirection.LEFT:
            # Left-directed: <-[var IS table]-
            sql = f"<-[{variable} IS {self.format_identifier(table)}]-"
        elif direction == GraphEdgeDirection.ANY:
            # Bidirectional: <-[var IS table]->
            sql = f"<-[{variable} IS {self.format_identifier(table)}]->"
        else:  # GraphEdgeDirection.NONE (undirected)
            # Undirected: -[var IS table]-
            sql = f"-[{variable} IS {self.format_identifier(table)}]-"

        return sql, ()

    def format_match_clause(self, clause: "MatchClause") -> Tuple[str, tuple]:
        """
        Formats a MATCH clause.

        Args:
            clause: MatchClause object containing the match expression

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clause.
        """
        if not self.supports_graph_match():
            raise UnsupportedFeatureError(self.name, "graph MATCH clause")

        # This method is called from MatchClause.to_sql(), so we need to format the MATCH clause
        # with the path components from the clause
        path_sql, all_params = [], []
        for part in clause.path:
            sql, params = part.to_sql()
            path_sql.append(sql)
            all_params.extend(params)

        match_sql = f"MATCH {' '.join(path_sql)}"
        return match_sql, tuple(all_params)
