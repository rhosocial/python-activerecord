# src/rhosocial/activerecord/backend/dialect/mixins/graph.py
import re
from typing import Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.graph import (
        GraphEdge,
        GraphVertex,
        GraphEdgeDirection,
        MatchClause,
        GraphTableExpression,
        ColumnsClause,
        TablePropertiesClause,
        VertexTable,
        EdgeTable,
        CreatePropertyGraphExpression,
        DropPropertyGraphExpression,
        AlterPropertyGraphExpression,
    )


class GraphMixin:
    """Mixin for graph query (MATCH) support."""

    def supports_graph_match(self) -> bool:
        """Whether graph query MATCH clause is supported."""
        return False

    def format_graph_vertex(self, vertex: "GraphVertex") -> Tuple[str, tuple]:
        """
        Formats a graph vertex expression.

        Args:
            vertex: GraphVertex object.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
        if not self.supports_graph_match():
            raise UnsupportedFeatureError(self.name, "graph MATCH clause")

        if vertex.variable is None:
            vertex_str = ""
        elif re.fullmatch(r"[A-Za-z0-9_]+", vertex.variable):
            vertex_str = f"{vertex.variable} IS "
        else:
            raise ValueError(
                f"Invalid variable name '{vertex.variable}': "
                "must contain only alphanumeric characters and underscores."
            )

        if vertex.where is not None:
            where_sql, where_params = vertex.where.to_sql()
            sql = f"({vertex_str}{self.format_identifier(vertex.table)} {where_sql})"
            return sql, where_params

        sql = f"({vertex_str}{self.format_identifier(vertex.table)})"
        return sql, ()

    def format_graph_edge(self, edge: "GraphEdge") -> Tuple[str, tuple]:
        """
        Formats a graph edge expression.

        Args:
            edge: GraphEdge object.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
        if not self.supports_graph_match():
            raise UnsupportedFeatureError(self.name, "graph MATCH clause")

        from ...expression.graph import GraphEdgeDirection

        if edge.direction == GraphEdgeDirection.RIGHT:
            prefix, suffix = "-", "->"
        elif edge.direction == GraphEdgeDirection.LEFT:
            prefix, suffix = "<-", "-"
        elif edge.direction == GraphEdgeDirection.ANY:
            prefix, suffix = "<-", "->"
        else:
            prefix, suffix = "-", "-"

        if edge.variable is not None and edge.table is not None:
            if not re.fullmatch(r"[A-Za-z0-9_]+", edge.variable):
                raise ValueError(
                    f"Invalid variable name '{edge.variable}': "
                    "must contain only alphanumeric characters and underscores."
                )
            edge_body = f"[{edge.variable} IS {self.format_identifier(edge.table)}]"
        elif edge.variable is not None:
            if not re.fullmatch(r"[A-Za-z0-9_]+", edge.variable):
                raise ValueError(
                    f"Invalid variable name '{edge.variable}': "
                    "must contain only alphanumeric characters and underscores."
                )
            edge_body = f"[{edge.variable}]"
        else:
            edge_body = "[]"

        sql = f"{prefix}{edge_body}{suffix}"
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

        path_sql, all_params = [], []
        for part in clause.path:
            sql, params = part.to_sql()
            path_sql.append(sql)
            all_params.extend(params)

        match_sql = f"MATCH {' '.join(path_sql)}"
        return match_sql, tuple(all_params)


class GraphTableMixin:
    """Mixin for GRAPH_TABLE query and PGQ DDL support."""

    def supports_graph_table(self) -> bool:
        """Whether GRAPH_TABLE expression is supported."""
        return False

    def format_graph_table_expression(self, expr: "GraphTableExpression") -> Tuple[str, tuple]:
        """Formats a GRAPH_TABLE expression with MATCH and COLUMNS clauses."""
        if not self.supports_graph_table():
            raise UnsupportedFeatureError(self.name, "GRAPH_TABLE")

        graph_name = self.format_identifier(expr.graph_name)
        match_sql, match_params = expr.match.to_sql()
        columns_sql, columns_params = expr.columns.to_sql()

        sql = f"GRAPH_TABLE ({graph_name} {match_sql} {columns_sql})"
        if expr.alias:
            sql += f" AS {self.format_identifier(expr.alias)}"
        return sql, match_params + columns_params

    def format_graph_columns_clause(self, columns: "ColumnsClause") -> Tuple[str, tuple]:
        """Formats a COLUMNS clause for GRAPH_TABLE."""
        return columns.to_sql()

    def format_table_properties_clause(self, clause: "TablePropertiesClause") -> Tuple[str, tuple]:
        """Formats a PROPERTIES clause for vertex/edge table definitions."""
        if not self.supports_graph_table():
            raise UnsupportedFeatureError(self.name, "PROPERTIES clause")

        if clause.columns is None:
            return "PROPERTIES ALL COLUMNS", ()
        if not clause.columns:
            return "PROPERTIES NONE", ()
        cols = ", ".join(self.format_identifier(c) for c in clause.columns)
        return f"PROPERTIES ({cols})", ()

    def format_vertex_table(self, vt: "VertexTable") -> Tuple[str, tuple]:
        """Formats a vertex table definition for CREATE PROPERTY GRAPH."""
        if not self.supports_graph_table():
            raise UnsupportedFeatureError(self.name, "vertex table definition")

        parts = [self.format_identifier(vt.table)]
        if vt.alias:
            parts.append(f"AS {self.format_identifier(vt.alias)}")

        if vt.labels:
            labels = " ".join(f"LABEL {self.format_identifier(l)}" for l in vt.labels)
            parts.append(labels)

        if vt.key_columns:
            keys = ", ".join(self.format_identifier(k) for k in vt.key_columns)
            parts.append(f"KEY ({keys})")

        if vt.properties is not None:
            sql, _ = vt.properties.to_sql()
            parts.append(sql)

        sql = " ".join(parts)
        return sql, ()

    def format_edge_table(self, et: "EdgeTable") -> Tuple[str, tuple]:
        """Formats an edge table definition for CREATE PROPERTY GRAPH."""
        if not self.supports_graph_table():
            raise UnsupportedFeatureError(self.name, "edge table definition")

        parts = [self.format_identifier(et.table)]
        if et.alias:
            parts.append(f"AS {self.format_identifier(et.alias)}")

        if et.key_columns:
            keys = ", ".join(self.format_identifier(k) for k in et.key_columns)
            parts.append(f"KEY ({keys})")

        src_keys = ", ".join(self.format_identifier(k) for k in et.source_key)
        if et.references_source:
            ref_table, ref_cols = et.references_source
            ref_cols_str = ", ".join(self.format_identifier(c) for c in ref_cols)
            src_part = f"SOURCE KEY ({src_keys}) REFERENCES {self.format_identifier(ref_table)} ({ref_cols_str})"
        else:
            src_part = f"SOURCE KEY ({src_keys})"
        parts.append(src_part)

        dst_keys = ", ".join(self.format_identifier(k) for k in et.destination_key)
        if et.references_destination:
            ref_table, ref_cols = et.references_destination
            ref_cols_str = ", ".join(self.format_identifier(c) for c in ref_cols)
            dst_part = f"DESTINATION KEY ({dst_keys}) REFERENCES {self.format_identifier(ref_table)} ({ref_cols_str})"
        else:
            dst_part = f"DESTINATION KEY ({dst_keys})"
        parts.append(dst_part)

        if et.labels:
            labels = " ".join(f"LABEL {self.format_identifier(l)}" for l in et.labels)
            parts.append(labels)

        if et.properties is not None:
            sql, _ = et.properties.to_sql()
            parts.append(sql)

        sql = " ".join(parts)
        return sql, ()

    def format_create_property_graph_statement(self, expr: "CreatePropertyGraphExpression") -> Tuple[str, tuple]:
        """Formats a CREATE PROPERTY GRAPH DDL statement."""
        if not self.supports_graph_table():
            raise UnsupportedFeatureError(self.name, "CREATE PROPERTY GRAPH")

        parts = ["CREATE PROPERTY GRAPH"]
        if expr.if_not_exists:
            parts.append("IF NOT EXISTS")
        parts.append(self.format_identifier(expr.graph_name))

        if expr.vertex_tables:
            vt_parts = []
            for vt in expr.vertex_tables:
                sql, _ = vt.to_sql()
                vt_parts.append(sql)
            parts.append(f"VERTEX TABLES ({', '.join(vt_parts)})")

        if expr.edge_tables:
            et_parts = []
            for et in expr.edge_tables:
                sql, _ = et.to_sql()
                et_parts.append(sql)
            parts.append(f"EDGE TABLES ({', '.join(et_parts)})")

        return " ".join(parts), ()

    def format_drop_property_graph_statement(self, expr: "DropPropertyGraphExpression") -> Tuple[str, tuple]:
        """Formats a DROP PROPERTY GRAPH DDL statement."""
        if not self.supports_graph_table():
            raise UnsupportedFeatureError(self.name, "DROP PROPERTY GRAPH")

        parts = ["DROP PROPERTY GRAPH"]
        if expr.if_exists:
            parts.append("IF EXISTS")
        parts.append(self.format_identifier(expr.graph_name))
        if expr.cascade:
            parts.append("CASCADE")
        return " ".join(parts), ()

    def format_alter_property_graph_statement(self, expr: "AlterPropertyGraphExpression") -> Tuple[str, tuple]:
        """Formats an ALTER PROPERTY GRAPH DDL statement."""
        if not self.supports_graph_table():
            raise UnsupportedFeatureError(self.name, "ALTER PROPERTY GRAPH")

        parts = ["ALTER PROPERTY GRAPH"]
        parts.append(self.format_identifier(expr.graph_name))
        parts.append(expr.action.upper())
        parts.append(expr.target.upper())
        table_parts = []
        for vt in expr.vertex_tables:
            sql, _ = vt.to_sql()
            table_parts.append(sql)
        for et in expr.edge_tables:
            sql, _ = et.to_sql()
            table_parts.append(sql)
        if table_parts:
            parts.append(",".join(table_parts))
        return " ".join(parts), ()
