# src/rhosocial/activerecord/backend/dialect/mixins/graph.py
"""Property graph mixins (SQL/PGQ).

Provides :class:`GraphMixin` for graph query MATCH formatting and
:class:`GraphTableMixin` for GRAPH_TABLE queries and property-graph DDL.
"""
import re
from typing import Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.graph import (
        GraphEdge,
        GraphVertex,
        GraphEdgeDirection,
        QuantifiedPath,
        PathPattern,
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
    """Format property graph query patterns and MATCH clauses.

    Capability probes default to ``False`` and are overridden by dialects that
    support graph queries.
    """

    def supports_graph_match(self) -> bool:
        """Whether the graph query MATCH clause is supported (defaults to False)."""
        return False

    def supports_quantified_path(self) -> bool:
        """Whether variable-length (quantified) path patterns are supported.

        Defaults to False. Quantified paths use ``+``, ``*``, or ``{n,m}``
        quantifiers on edges.
        """
        return False

    def supports_comma_separated_patterns(self) -> bool:
        """Whether multiple comma-separated patterns in one MATCH are supported.

        Defaults to False.
        """
        return False

    def format_graph_vertex(self, vertex: "GraphVertex") -> Tuple[str, tuple]:
        """Format a graph vertex expression.

        Args:
            vertex: GraphVertex object, optionally carrying a variable, table
                and WHERE condition.

        Returns:
            A ``(sql, params)`` tuple for the formatted vertex.

        Raises:
            UnsupportedFeatureError: If the dialect does not support MATCH.
            ValueError: If the vertex variable name contains invalid
                characters.
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
        """Format a graph edge expression.

        Args:
            edge: GraphEdge object carrying a direction and optional variable
                and table.

        Returns:
            A ``(sql, params)`` tuple for the formatted edge.

        Raises:
            UnsupportedFeatureError: If the dialect does not support MATCH.
            ValueError: If the edge variable name contains invalid characters.
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

    def format_quantified_path(self, quantified: "QuantifiedPath") -> Tuple[str, tuple]:
        """Format a quantified (variable-length) path pattern.

        Args:
            quantified: QuantifiedPath object exposing the edge and the
                ``min_repeats`` / ``max_repeats`` bounds.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is always empty.

        Raises:
            UnsupportedFeatureError: If the dialect does not support quantified
                paths.
        """
        if not self.supports_quantified_path():
            raise UnsupportedFeatureError(self.name, "quantified path pattern")

        edge_sql, _ = quantified.edge.to_sql()

        if quantified.min_repeats is None and quantified.max_repeats is None:
            quantifier = "+"
        elif quantified.min_repeats == 0 and quantified.max_repeats is None:
            quantifier = "*"
        elif quantified.min_repeats is not None and quantified.min_repeats == quantified.max_repeats:
            quantifier = "{%d}" % quantified.min_repeats
        elif quantified.max_repeats is None:
            quantifier = "{%d,}" % quantified.min_repeats
        else:
            quantifier = "{%d,%d}" % (quantified.min_repeats, quantified.max_repeats)

        return f"{edge_sql}{quantifier}", ()

    def format_path_pattern(self, pattern: "PathPattern") -> Tuple[str, tuple]:
        """Format a single path pattern by joining its elements with spaces.

        Args:
            pattern: PathPattern object exposing a ``path`` iterable of
                elements.

        Returns:
            A ``(sql, params)`` tuple for the joined pattern.

        Raises:
            UnsupportedFeatureError: If the dialect does not support MATCH.
        """
        if not self.supports_graph_match():
            raise UnsupportedFeatureError(self.name, "graph MATCH clause")

        parts_sql, all_params = [], []
        for element in pattern.path:
            sql, params = element.to_sql()
            parts_sql.append(sql)
            all_params.extend(params)
        return " ".join(parts_sql), tuple(all_params)

    def format_match_clause(self, clause: "MatchClause") -> Tuple[str, tuple]:
        """Format a MATCH clause with one or more patterns.

        When multiple :class:`PathPattern` instances are present they are
        rendered as comma-separated patterns. If the dialect does not support
        comma-separated patterns and multiple patterns are given, an
        :class:`UnsupportedFeatureError` is raised.

        Args:
            clause: MatchClause object containing the match expression.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clause.

        Raises:
            UnsupportedFeatureError: If the dialect does not support MATCH, or
                does not support multiple comma-separated patterns.
        """
        if not self.supports_graph_match():
            raise UnsupportedFeatureError(self.name, "graph MATCH clause")

        has_multiple = len(clause.patterns) > 1
        if has_multiple and not self.supports_comma_separated_patterns():
            raise UnsupportedFeatureError(
                self.name, "comma-separated patterns in MATCH clause"
            )

        pattern_sqls, all_params = [], []
        for pattern in clause.patterns:
            sql, params = pattern.to_sql()
            pattern_sqls.append(sql)
            all_params.extend(params)

        separator = ", " if has_multiple else " "
        match_sql = f"MATCH {separator.join(pattern_sqls)}"
        return match_sql, tuple(all_params)


class GraphTableMixin:
    """Format GRAPH_TABLE queries and property-graph DDL (SQL/PGQ).

    Capability probes default to ``False`` and are overridden by dialects that
    support property graphs.
    """

    def supports_graph_table(self) -> bool:
        """Whether the GRAPH_TABLE expression is supported (defaults to False)."""
        return False

    def format_graph_table_expression(self, expr: "GraphTableExpression") -> Tuple[str, tuple]:
        """Format a GRAPH_TABLE expression with MATCH and COLUMNS clauses.

        Args:
            expr: GraphTableExpression exposing ``graph_name``, ``match``,
                ``columns`` and optional ``alias``.

        Returns:
            A ``(sql, params)`` tuple for the formatted expression.

        Raises:
            UnsupportedFeatureError: If the dialect does not support
                GRAPH_TABLE.
        """
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
        """Format a COLUMNS clause for GRAPH_TABLE.

        Args:
            columns: ColumnsClause object exposing a ``columns`` iterable of
                variable/property pairs with optional aliases.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is always empty.
        """
        parts = []
        for col in columns.columns:
            col_str = f"{self.format_identifier(col.variable)}.{self.format_identifier(col.property_name)}"
            if col.alias:
                col_str += f" AS {self.format_identifier(col.alias)}"
            parts.append(col_str)
        return f"COLUMNS ({', '.join(parts)})", ()

    def format_table_properties_clause(self, clause: "TablePropertiesClause") -> Tuple[str, tuple]:
        """Format a PROPERTIES clause for vertex/edge table definitions.

        Args:
            clause: TablePropertiesClause whose ``columns`` is ``None`` for ALL
                COLUMNS, empty for NONE, or a list of column names.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is always empty.

        Raises:
            UnsupportedFeatureError: If the dialect does not support property
                graph tables.
        """
        if not self.supports_graph_table():
            raise UnsupportedFeatureError(self.name, "PROPERTIES clause")

        if clause.columns is None:
            return "PROPERTIES ALL COLUMNS", ()
        if not clause.columns:
            return "PROPERTIES NONE", ()
        cols = ", ".join(self.format_identifier(c) for c in clause.columns)
        return f"PROPERTIES ({cols})", ()

    def format_vertex_table(self, vt: "VertexTable") -> Tuple[str, tuple]:
        """Format a vertex table definition for CREATE PROPERTY GRAPH.

        Args:
            vt: VertexTable object exposing table, optional alias, labels, key
                columns and properties.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is always empty.

        Raises:
            UnsupportedFeatureError: If the dialect does not support property
                graph tables.
        """
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
        """Format an edge table definition for CREATE PROPERTY GRAPH.

        Args:
            et: EdgeTable object exposing table, optional alias, key columns,
                source/destination keys (with optional references), labels and
                properties.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is always empty.

        Raises:
            UnsupportedFeatureError: If the dialect does not support property
                graph tables.
        """
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
        """Format a CREATE PROPERTY GRAPH DDL statement.

        Args:
            expr: CreatePropertyGraphExpression exposing graph name,
                ``if_not_exists``, vertex tables and edge tables.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is always empty.

        Raises:
            UnsupportedFeatureError: If the dialect does not support property
                graph tables.
        """
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
        """Format a DROP PROPERTY GRAPH DDL statement.

        Args:
            expr: DropPropertyGraphExpression exposing graph name,
                ``if_exists`` and ``cascade``.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is always empty.

        Raises:
            UnsupportedFeatureError: If the dialect does not support property
                graph tables.
        """
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
        """Format an ALTER PROPERTY GRAPH DDL statement.

        Args:
            expr: AlterPropertyGraphExpression exposing graph name, action,
                target, vertex tables and edge tables.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is always empty.

        Raises:
            UnsupportedFeatureError: If the dialect does not support property
                graph tables.
        """
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
