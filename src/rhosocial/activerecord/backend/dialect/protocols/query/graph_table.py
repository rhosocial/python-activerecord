# src/rhosocial/activerecord/backend/dialect/protocols/graphtablesupport.py
"""GraphTableSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression import (
        AlterPropertyGraphExpression,
        ColumnsClause,
        CreatePropertyGraphExpression,
        DropPropertyGraphExpression,
        EdgeTable,
        GraphTableExpression,
        TablePropertiesClause,
        VertexTable,
    )


@runtime_checkable
class GraphTableSupport(Protocol):
    """Protocol for GRAPH_TABLE query expression support (SQL/PGQ)."""

    def supports_graph_table(self) -> bool:
        """Whether GRAPH_TABLE expression is supported."""
        ...  # pragma: no cover

    def format_graph_table_expression(self, expr: "GraphTableExpression") -> Tuple[str, tuple]:
        """
        Formats a GRAPH_TABLE expression.

        Args:
            expr: GraphTableExpression object.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
        ...  # pragma: no cover

    def format_graph_columns_clause(self, columns: "ColumnsClause") -> Tuple[str, tuple]:
        """
        Formats a GRAPH_TABLE COLUMNS clause.

        Args:
            columns: ColumnsClause object.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clause.
        """
        ...  # pragma: no cover

    def format_table_properties_clause(self, clause: "TablePropertiesClause") -> Tuple[str, tuple]:
        """
        Formats a PROPERTIES clause for vertex/edge table definitions.

        Args:
            clause: TablePropertiesClause object.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_vertex_table(self, vt: "VertexTable") -> Tuple[str, tuple]:
        """
        Formats a vertex table definition for CREATE PROPERTY GRAPH.

        Args:
            vt: VertexTable object.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_edge_table(self, et: "EdgeTable") -> Tuple[str, tuple]:
        """
        Formats an edge table definition for CREATE PROPERTY GRAPH.

        Args:
            et: EdgeTable object.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_create_property_graph_statement(self, expr: "CreatePropertyGraphExpression") -> Tuple[str, tuple]:
        """
        Formats a CREATE PROPERTY GRAPH statement.

        Args:
            expr: CreatePropertyGraphExpression object.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_drop_property_graph_statement(self, expr: "DropPropertyGraphExpression") -> Tuple[str, tuple]:
        """
        Formats a DROP PROPERTY GRAPH statement.

        Args:
            expr: DropPropertyGraphExpression object.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_alter_property_graph_statement(self, expr: "AlterPropertyGraphExpression") -> Tuple[str, tuple]:
        """
        Formats an ALTER PROPERTY GRAPH statement.

        Args:
            expr: AlterPropertyGraphExpression object.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover
