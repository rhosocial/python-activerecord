# src/rhosocial/activerecord/backend/expression/sources/graph.py
"""
Graph traversal sources.

Oracle's ``GRAPH_TABLE`` is a table expression in a ``FROM`` clause: it
produces rows for the duration of the query, so it is a source. The *tables*
holding vertices and edges are ordinary relations -- see
:class:`~..objects.relation.NodeTable` and
:class:`~..objects.relation.EdgeTable` -- and are read through
:class:`~.relation.NamedRelationRef` like any other relation.
"""

from typing import Any, Optional

from .base import TableSource

__all__ = ["GraphTableSource"]


class GraphTableSource(TableSource):
    """A ``GRAPH_TABLE(...)`` row source."""

    __slots__ = ("query", "columns_clause")

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this source."""
        return "format_graph_table"

    def __init__(
        self,
        dialect: "SQLDialectBase",  # noqa: F821
        query: Any,
        columns_clause: Optional[Any] = None,
        alias: Optional[str] = None,
        alias_need_quote: bool = True,
    ) -> None:
        """Evaluate a graph pattern as a row source.

        Args:
            dialect: The dialect that will render this source.
            query: The graph pattern expression.
            columns_clause: Column projection for the matched rows.
            alias: Name this source is known by inside the query.
            alias_need_quote: Whether the alias is quoted when rendered.
        """
        super().__init__(dialect, alias=alias, alias_need_quote=alias_need_quote)
        self.query = query
        self.columns_clause = columns_clause