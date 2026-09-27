# src/rhosocial/activerecord/backend/dialect/mixins/graph.py
"""Property graph mixins (SQL/PGQ).

Provides :class:`GraphMixin` for graph query MATCH formatting and
:class:`GraphTableMixin` for GRAPH_TABLE queries and property-graph DDL.
"""
import re
from typing import Mapping, Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.graph import (
        GraphEdge,
        GraphVertex,
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

    @staticmethod
    def _validate_graph_path(pattern: "PathPattern") -> None:
        from ...expression.graph import GraphEdge, GraphVertex, PathPattern, QuantifiedPath

        if not isinstance(pattern, PathPattern):
            raise TypeError("PathPattern must be a PathPattern expression")
        path = pattern.path
        if not isinstance(path, (list, tuple)):
            raise TypeError("PathPattern.path must be a sequence")
        if not path:
            raise ValueError("PathPattern must contain at least one path element")

        for index, element in enumerate(path):
            is_vertex = isinstance(element, GraphVertex)
            is_edge = isinstance(element, (GraphEdge, QuantifiedPath))
            if not is_vertex and not is_edge:
                raise TypeError(
                    "PathPattern elements must be GraphVertex, GraphEdge, "
                    "or QuantifiedPath instances"
                )
            if is_vertex != (index % 2 == 0):
                raise ValueError(
                    "PathPattern must alternate vertices and edges and start "
                    "and end with a vertex"
                )

        if not isinstance(path[0], GraphVertex) or not isinstance(path[-1], GraphVertex):
            raise ValueError(
                "PathPattern must alternate vertices and edges and start "
                "and end with a vertex"
            )

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

        from ...expression.graph import GraphVertex

        if not isinstance(vertex, GraphVertex):
            raise TypeError("GraphVertex must be a GraphVertex expression")
        if not isinstance(vertex.table, str):
            raise TypeError("GraphVertex table must be a string")
        if vertex.variable is not None and not isinstance(vertex.variable, str):
            raise ValueError(
                f"Invalid variable name '{vertex.variable}': "
                "must contain only alphanumeric characters and underscores."
            )

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
            from ...expression.query_parts import WhereClause

            if not isinstance(vertex.where, WhereClause):
                raise TypeError("GraphVertex where must be a WhereClause expression")

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

        from ...expression.graph import GraphEdge, GraphEdgeDirection

        if not isinstance(edge, GraphEdge):
            raise TypeError("GraphEdge must be a GraphEdge expression")
        if edge.table is not None and not isinstance(edge.table, str):
            raise TypeError("GraphEdge table must be a string")
        if edge.variable is not None and not isinstance(edge.variable, str):
            raise ValueError(
                f"Invalid variable name '{edge.variable}': "
                "must contain only alphanumeric characters and underscores."
            )
        if edge.table is not None and edge.variable is None:
            raise ValueError("GraphEdge table requires a variable")
        if not isinstance(edge.direction, GraphEdgeDirection):
            raise ValueError(f"Invalid graph edge direction: {edge.direction!r}")
        if edge.direction == GraphEdgeDirection.RIGHT:
            prefix, suffix = "-", "->"
        elif edge.direction == GraphEdgeDirection.LEFT:
            prefix, suffix = "<-", "-"
        elif edge.direction == GraphEdgeDirection.ANY:
            prefix, suffix = "<-", "->"
        elif edge.direction == GraphEdgeDirection.NONE:
            prefix, suffix = "-", "-"
        else:
            raise ValueError(f"Invalid graph edge direction: {edge.direction!r}")

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

        from ...expression.graph import GraphEdge, QuantifiedPath

        if not isinstance(quantified, QuantifiedPath):
            raise TypeError("QuantifiedPath must be a QuantifiedPath expression")
        if not isinstance(quantified.edge, GraphEdge):
            raise TypeError("QuantifiedPath edge must be a GraphEdge expression")

        min_repeats = quantified.min_repeats
        max_repeats = quantified.max_repeats
        if min_repeats is not None and (
            type(min_repeats) is not int or min_repeats < 0
        ):
            raise ValueError("QuantifiedPath minimum repeats must be a non-negative integer")
        if max_repeats is not None and (
            type(max_repeats) is not int or max_repeats < 0
        ):
            raise ValueError("QuantifiedPath maximum repeats must be a non-negative integer")
        if min_repeats is None and max_repeats is not None:
            raise ValueError("QuantifiedPath maximum repeats require a minimum")
        if min_repeats is not None and max_repeats is not None and min_repeats > max_repeats:
            raise ValueError("QuantifiedPath minimum repeats cannot exceed maximum repeats")

        edge_sql, edge_params = quantified.edge.to_sql()
        if edge_params:
            raise ValueError("QuantifiedPath edges must render without parameters")

        if min_repeats is None and max_repeats is None:
            quantifier = "+"
        elif min_repeats == 0 and max_repeats is None:
            quantifier = "*"
        elif min_repeats is not None and min_repeats == max_repeats:
            quantifier = "{%d}" % min_repeats
        elif max_repeats is None:
            quantifier = "{%d,}" % min_repeats
        else:
            quantifier = "{%d,%d}" % (min_repeats, max_repeats)

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

        self._validate_graph_path(pattern)
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

        from ...expression.graph import MatchClause, PathPattern

        if not isinstance(clause, MatchClause):
            raise TypeError("MatchClause must be a MatchClause expression")
        if not isinstance(clause.patterns, (list, tuple)):
            raise TypeError("MatchClause.patterns must be a sequence")
        if any(not isinstance(pattern, PathPattern) for pattern in clause.patterns):
            raise TypeError("MatchClause patterns must be PathPattern instances")
        if not clause.patterns or any(not pattern.path for pattern in clause.patterns):
            raise ValueError("MatchClause must contain at least one path element")

        has_multiple = len(clause.patterns) > 1
        if has_multiple and not self.supports_comma_separated_patterns():
            raise UnsupportedFeatureError(
                self.name, "comma-separated patterns in MATCH clause"
            )

        pattern_sqls, all_params = [], []
        for pattern in clause.patterns:
            sql, params = self.format_path_pattern(pattern)
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

    @staticmethod
    def _require_graph_string(value: object, label: str) -> str:
        if not isinstance(value, str):
            raise TypeError(f"{label} must be a string")
        if not value:
            raise ValueError(f"{label} must not be empty")
        return value

    @classmethod
    def _validate_graph_columns(cls, columns: "ColumnsClause") -> None:
        from ...expression.graph import ColumnsClause, GraphColumn

        if not isinstance(columns, ColumnsClause):
            raise TypeError("Graph columns must be a ColumnsClause expression")
        if not isinstance(columns.columns, (list, tuple)):
            raise TypeError("ColumnsClause.columns must be a sequence")

        for column in columns.columns:
            if not isinstance(column, GraphColumn):
                raise TypeError("ColumnsClause entries must be GraphColumn instances")
            cls._require_graph_string(column.variable, "Graph column variable")
            if re.fullmatch(r"[A-Za-z0-9_]+", column.variable) is None:
                raise ValueError(
                    f"Invalid graph column variable '{column.variable}': "
                    "must contain only alphanumeric characters and underscores."
                )
            cls._require_graph_string(column.property_name, "Graph column property name")
            if column.alias is not None:
                cls._require_graph_string(column.alias, "Graph column alias")

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

        from ...expression.graph import ColumnsClause, GraphTableExpression, MatchClause

        if not isinstance(expr, GraphTableExpression):
            raise TypeError("GraphTableExpression must be a GraphTableExpression expression")
        if not isinstance(expr.match, MatchClause):
            raise TypeError("GraphTableExpression match must be a MatchClause expression")
        if not isinstance(expr.columns, ColumnsClause):
            raise TypeError("GraphTableExpression columns must be a ColumnsClause expression")
        self._require_graph_string(expr.graph_name, "GRAPH_TABLE graph name")
        if expr.alias is not None:
            self._require_graph_string(expr.alias, "GRAPH_TABLE alias")

        graph_name = self.format_identifier(expr.graph_name)
        match_sql, match_params = self.format_match_clause(expr.match)
        columns_sql, columns_params = self.format_graph_columns_clause(expr.columns)

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
        if not self.supports_graph_table():
            raise UnsupportedFeatureError(self.name, "GRAPH_TABLE COLUMNS clause")
        self._validate_graph_columns(columns)
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
            labels = " ".join(
                f"LABEL {self.format_identifier(label)}" for label in vt.labels
            )
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
            labels = " ".join(
                f"LABEL {self.format_identifier(label)}" for label in et.labels
            )
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

    _ALTER_ACTIONS = {
        "add": "ADD",
        "drop": "DROP",
    }
    _ALTER_TARGETS = {
        "edge tables": "EDGE TABLES",
        "tables": "TABLES",
        "vertex tables": "VERTEX TABLES",
    }

    @staticmethod
    def _normalize_alter_keyword(value: object, allowed: Mapping[str, str], label: str) -> str:
        if isinstance(value, str):
            normalized = allowed.get(value.casefold())
            if normalized is not None:
                return normalized
        raise ValueError(f"Invalid ALTER PROPERTY GRAPH {label}: {value!r}")

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

        from ...expression.graph import AlterPropertyGraphExpression, EdgeTable, VertexTable

        if not isinstance(expr, AlterPropertyGraphExpression):
            raise TypeError(
                "ALTER PROPERTY GRAPH expression must be an "
                "AlterPropertyGraphExpression"
            )
        self._require_graph_string(expr.graph_name, "ALTER PROPERTY GRAPH graph name")
        action = self._normalize_alter_keyword(expr.action, self._ALTER_ACTIONS, "action")
        target = self._normalize_alter_keyword(expr.target, self._ALTER_TARGETS, "target")

        vertex_tables = expr.vertex_tables
        edge_tables = expr.edge_tables
        if not isinstance(vertex_tables, (list, tuple)):
            raise TypeError("ALTER PROPERTY GRAPH vertex_tables must be a sequence")
        if not isinstance(edge_tables, (list, tuple)):
            raise TypeError("ALTER PROPERTY GRAPH edge_tables must be a sequence")
        if target == "VERTEX TABLES" and edge_tables:
            raise ValueError("VERTEX TABLES cannot contain edge tables")
        if target == "EDGE TABLES" and vertex_tables:
            raise ValueError("EDGE TABLES cannot contain vertex tables")
        if any(not isinstance(table, VertexTable) for table in vertex_tables):
            raise TypeError("ALTER PROPERTY GRAPH vertex tables must be VertexTable instances")
        if any(not isinstance(table, EdgeTable) for table in edge_tables):
            raise TypeError("ALTER PROPERTY GRAPH edge tables must be EdgeTable instances")

        parts = [
            "ALTER PROPERTY GRAPH",
            self.format_identifier(expr.graph_name),
            action,
            target,
        ]
        table_parts = []
        for table in (*vertex_tables, *edge_tables):
            sql, _ = table.to_sql()
            table_parts.append(sql)
        if table_parts:
            parts.append(",".join(table_parts))
        return " ".join(parts), ()
