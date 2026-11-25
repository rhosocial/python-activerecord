# src/rhosocial/activerecord/backend/dialect/mixins/graph.py
"""Property graph mixins (SQL/PGQ).

Provides :class:`GraphMixin` for graph query MATCH formatting and
:class:`GraphTableMixin` for GRAPH_TABLE queries and property-graph DDL.
"""
from typing import Mapping, Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError
from ...expression.objects import EdgeTable as EdgeTableObject
from ...expression.objects import NodeTable, PropertyGraph
from ...textscan import is_simple_name

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
        EdgeTableDefinition,
        CreatePropertyGraphStatement,
        DropPropertyGraphStatement,
        AlterPropertyGraphStatement,
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

    def format_graph_vertex(self, expr: "GraphVertex") -> Tuple[str, tuple]:
        """Format a graph expr expression.

        Args:
            expr: GraphVertex object, optionally carrying a variable, table
                and WHERE condition.

        Returns:
            A ``(sql, params)`` tuple for the formatted expr.

        Raises:
            TypeError: ``GraphVertex.table`` is not a NodeTable. Another object kind
            would have had its own name rendered as the expr's table, and the
            MATCH pattern would read the wrong relation.
            UnsupportedFeatureError: If the dialect does not support MATCH.
            ValueError: If the expr variable name contains invalid
                characters.
        """
        if not isinstance(expr.table, NodeTable):
            raise TypeError(
                f"GraphVertex.table must be a NodeTable, "
                f"got {type(expr.table).__name__}"
            )
        if not self.supports_graph_match():
            raise UnsupportedFeatureError(self.name, "graph MATCH clause")

        from ...expression.graph import GraphVertex

        if not isinstance(expr, GraphVertex):
            raise TypeError("GraphVertex must be a GraphVertex expression")
        if expr.variable is not None and not isinstance(expr.variable, str):
            raise ValueError(
                f"Invalid variable name '{expr.variable}': "
                "must contain only alphanumeric characters and underscores."
            )

        if expr.variable is None:
            vertex_str = ""
        elif is_simple_name(expr.variable):
            vertex_str = f"{expr.variable} IS "
        else:
            raise ValueError(
                f"Invalid variable name '{expr.variable}': "
                "must contain only alphanumeric characters and underscores."
            )

        if expr.where is not None:
            from ...expression.query_parts import WhereClause

            if not isinstance(expr.where, WhereClause):
                raise TypeError("GraphVertex where must be a WhereClause expression")

        if expr.where is not None:
            where_sql, where_params = expr.where.to_sql()
            sql = f"({vertex_str}{expr.table.to_sql()[0]} {where_sql})"
            return sql, where_params

        sql = f"({vertex_str}{expr.table.to_sql()[0]})"
        return sql, ()

    def format_graph_edge(self, expr: "GraphEdge") -> Tuple[str, tuple]:
        """Format a graph expr expression.

        Args:
            expr: GraphEdge object carrying a direction and optional variable
                and table.

        Returns:
            A ``(sql, params)`` tuple for the formatted expr.

        Raises:
            TypeError: ``GraphEdge.table`` is not an EdgeTableObject. Another object
            kind would have had its own name rendered as the expr's.
            UnsupportedFeatureError: If the dialect does not support MATCH.
            ValueError: If the expr variable name contains invalid characters.
        """
        if expr.table is not None and not isinstance(expr.table, EdgeTableObject):
            raise TypeError(
                f"GraphEdge.table must be an EdgeTableObject, "
                f"got {type(expr.table).__name__}"
            )
        if not self.supports_graph_match():
            raise UnsupportedFeatureError(self.name, "graph MATCH clause")

        from ...expression.graph import GraphEdge, GraphEdgeDirection

        if not isinstance(expr, GraphEdge):
            raise TypeError("GraphEdge must be a GraphEdge expression")
        if expr.variable is not None and not isinstance(expr.variable, str):
            raise ValueError(
                f"Invalid variable name '{expr.variable}': "
                "must contain only alphanumeric characters and underscores."
            )
        if expr.table is not None and expr.variable is None:
            raise ValueError("GraphEdge table requires a variable")
        if not isinstance(expr.direction, GraphEdgeDirection):
            raise ValueError(f"Invalid graph expr direction: {expr.direction!r}")
        if expr.direction == GraphEdgeDirection.RIGHT:
            prefix, suffix = "-", "->"
        elif expr.direction == GraphEdgeDirection.LEFT:
            prefix, suffix = "<-", "-"
        elif expr.direction == GraphEdgeDirection.ANY:
            prefix, suffix = "<-", "->"
        elif expr.direction == GraphEdgeDirection.NONE:
            prefix, suffix = "-", "-"
        else:
            raise ValueError(f"Invalid graph expr direction: {expr.direction!r}")

        if expr.variable is not None and expr.table is not None:
            if not is_simple_name(expr.variable):
                raise ValueError(
                    f"Invalid variable name '{expr.variable}': "
                    "must contain only alphanumeric characters and underscores."
                )
            edge_body = f"[{expr.variable} IS {expr.table.to_sql()[0]}]"
        elif expr.variable is not None:
            if not is_simple_name(expr.variable):
                raise ValueError(
                    f"Invalid variable name '{expr.variable}': "
                    "must contain only alphanumeric characters and underscores."
                )
            edge_body = f"[{expr.variable}]"
        else:
            edge_body = "[]"

        sql = f"{prefix}{edge_body}{suffix}"
        return sql, ()

    def format_quantified_path(self, expr: "QuantifiedPath") -> Tuple[str, tuple]:
        """Format a expr (variable-length) path pattern.

        Args:
            expr: QuantifiedPath object exposing the edge and the
                ``min_repeats`` / ``max_repeats`` bounds.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is always empty.

        Raises:
            UnsupportedFeatureError: If the dialect does not support expr
                paths.
        """
        if not self.supports_quantified_path():
            raise UnsupportedFeatureError(self.name, "expr path pattern")

        from ...expression.graph import GraphEdge, QuantifiedPath

        if not isinstance(expr, QuantifiedPath):
            raise TypeError("QuantifiedPath must be a QuantifiedPath expression")
        if not isinstance(expr.edge, GraphEdge):
            raise TypeError("QuantifiedPath edge must be a GraphEdge expression")

        min_repeats = expr.min_repeats
        max_repeats = expr.max_repeats
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

        edge_sql, edge_params = expr.edge.to_sql()
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

    def format_path_pattern(self, expr: "PathPattern") -> Tuple[str, tuple]:
        """Format a single path expr by joining its elements with spaces.

        Args:
            expr: PathPattern object exposing a ``path`` iterable of
                elements.

        Returns:
            A ``(sql, params)`` tuple for the joined expr.

        Raises:
            UnsupportedFeatureError: If the dialect does not support MATCH.
        """
        if not self.supports_graph_match():
            raise UnsupportedFeatureError(self.name, "graph MATCH clause")

        self._validate_graph_path(expr)
        parts_sql, all_params = [], []
        for element in expr.path:
            sql, params = element.to_sql()
            parts_sql.append(sql)
            all_params.extend(params)
        return " ".join(parts_sql), tuple(all_params)

    def format_match_clause(self, expr: "MatchClause") -> Tuple[str, tuple]:
        """Format a MATCH expr with one or more patterns.

        When multiple :class:`PathPattern` instances are present they are
        rendered as comma-separated patterns. If the dialect does not support
        comma-separated patterns and multiple patterns are given, an
        :class:`UnsupportedFeatureError` is raised.

        Args:
            expr: MatchClause object containing the match expression.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expr.

        Raises:
            UnsupportedFeatureError: If the dialect does not support MATCH, or
                does not support multiple comma-separated patterns.
        """
        if not self.supports_graph_match():
            raise UnsupportedFeatureError(self.name, "graph MATCH expr")

        from ...expression.graph import MatchClause, PathPattern

        if not isinstance(expr, MatchClause):
            raise TypeError("MatchClause must be a MatchClause expression")
        if not isinstance(expr.patterns, (list, tuple)):
            raise TypeError("MatchClause.patterns must be a sequence")
        if any(not isinstance(pattern, PathPattern) for pattern in expr.patterns):
            raise TypeError("MatchClause patterns must be PathPattern instances")
        if not expr.patterns or any(not pattern.path for pattern in expr.patterns):
            raise ValueError("MatchClause must contain at least one path element")

        has_multiple = len(expr.patterns) > 1
        if has_multiple and not self.supports_comma_separated_patterns():
            raise UnsupportedFeatureError(
                self.name, "comma-separated patterns in MATCH expr"
            )

        pattern_sqls, all_params = [], []
        for pattern in expr.patterns:
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
            if not is_simple_name(column.variable):
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
            TypeError: ``GraphTableExpression.graph`` is not a PropertyGraph.
            Another object kind would have had its own name rendered as the graph's.
            UnsupportedFeatureError: If the dialect does not support
                GRAPH_TABLE.
        """
        if not isinstance(expr.graph, PropertyGraph):
            raise TypeError(
                f"GraphTableExpression.graph must be a PropertyGraph, "
                f"got {type(expr.graph).__name__}"
            )
        if not self.supports_graph_table():
            raise UnsupportedFeatureError(self.name, "GRAPH_TABLE")

        from ...expression.graph import ColumnsClause, GraphTableExpression, MatchClause

        if not isinstance(expr, GraphTableExpression):
            raise TypeError("GraphTableExpression must be a GraphTableExpression expression")
        if not isinstance(expr.match, MatchClause):
            raise TypeError("GraphTableExpression match must be a MatchClause expression")
        if not isinstance(expr.columns, ColumnsClause):
            raise TypeError("GraphTableExpression columns must be a ColumnsClause expression")
        if expr.alias is not None:
            self._require_graph_string(expr.alias, "GRAPH_TABLE alias")

        graph_name = expr.graph.to_sql()[0]
        match_sql, match_params = self.format_match_clause(expr.match)
        columns_sql, columns_params = self.format_graph_columns_clause(expr.columns)

        sql = f"GRAPH_TABLE ({graph_name} {match_sql} {columns_sql})"
        if expr.alias:
            sql += f" AS {self.format_identifier(expr.alias)}"
        return sql, match_params + columns_params

    def format_graph_columns_clause(self, expr: "ColumnsClause") -> Tuple[str, tuple]:
        """Format a COLUMNS clause for GRAPH_TABLE.

        Args:
            expr: ColumnsClause object exposing a ``expr`` iterable of
                variable/property pairs with optional aliases.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is always empty.
        """
        if not self.supports_graph_table():
            raise UnsupportedFeatureError(self.name, "GRAPH_TABLE COLUMNS clause")
        self._validate_graph_columns(expr)
        parts = []
        for col in expr.columns:
            col_str = f"{self.format_identifier(col.variable)}.{self.format_identifier(col.property_name)}"
            if col.alias:
                col_str += f" AS {self.format_identifier(col.alias)}"
            parts.append(col_str)
        return f"COLUMNS ({', '.join(parts)})", ()

    def format_table_properties_clause(self, expr: "TablePropertiesClause") -> Tuple[str, tuple]:
        """Format a PROPERTIES expr for vertex/edge table definitions.

        Args:
            expr: TablePropertiesClause whose ``columns`` is ``None`` for ALL
                COLUMNS, empty for NONE, or a list of column names.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is always empty.

        Raises:
            UnsupportedFeatureError: If the dialect does not support property
                graph tables.
        """
        if not self.supports_graph_table():
            raise UnsupportedFeatureError(self.name, "PROPERTIES expr")

        if expr.columns is None:
            return "PROPERTIES ALL COLUMNS", ()
        if not expr.columns:
            return "PROPERTIES NONE", ()
        cols = ", ".join(self.format_identifier(c) for c in expr.columns)
        return f"PROPERTIES ({cols})", ()

    def format_vertex_table(self, expr: "VertexTable") -> Tuple[str, tuple]:
        """Format a vertex table definition for CREATE PROPERTY GRAPH.

        Args:
            expr: VertexTable object exposing table, optional alias, labels, key
                columns and properties.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is always empty.

        Raises:
            TypeError: ``VertexTable.table`` is not a NodeTable. Another object kind
            would have had its own name rendered as the vertex table's.
            UnsupportedFeatureError: If the dialect does not support property
                graph tables.
        """
        if not isinstance(expr.table, NodeTable):
            raise TypeError(
                f"VertexTable.table must be a NodeTable, "
                f"got {type(expr.table).__name__}"
            )
        if not self.supports_graph_table():
            raise UnsupportedFeatureError(self.name, "vertex table definition")

        parts = [expr.table.to_sql()[0]]
        if expr.alias:
            parts.append(f"AS {self.format_identifier(expr.alias)}")

        # KEY before LABEL: that is the order the grammar wants, and the
        # other order is a parse error rather than a wrong answer --
        # "missing right parenthesis", with the statement rejected whole.
        if expr.key_columns:
            keys = ", ".join(self.format_identifier(k) for k in expr.key_columns)
            parts.append(f"KEY ({keys})")

        if expr.labels:
            labels = " ".join(
                f"LABEL {self.format_identifier(label)}" for label in expr.labels
            )
            parts.append(labels)

        if expr.properties is not None:
            sql, _ = expr.properties.to_sql()
            parts.append(sql)

        sql = " ".join(parts)
        return sql, ()

    def format_edge_table_definition(self, expr: "EdgeTableDefinition") -> Tuple[str, tuple]:
        """Format an edge table definition for CREATE PROPERTY GRAPH.

        Args:
            expr: EdgeTableDefinition object exposing table, optional alias, key columns,
                source/destination keys (with optional references), labels and
                properties.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is always empty.

        Raises:
            TypeError: ``EdgeTableDefinition.table`` is not an EdgeTableObject. Another object
            kind would have had its own name rendered as the edge table's.
            UnsupportedFeatureError: If the dialect does not support property
                graph tables.
        """
        if not isinstance(expr.table, EdgeTableObject):
            raise TypeError(
                f"EdgeTableDefinition.table must be an EdgeTableObject, "
                f"got {type(expr.table).__name__}"
            )
        if not self.supports_graph_table():
            raise UnsupportedFeatureError(self.name, "edge table definition")

        parts = [expr.table.to_sql()[0]]
        if expr.alias:
            parts.append(f"AS {self.format_identifier(expr.alias)}")

        if expr.key_columns:
            keys = ", ".join(self.format_identifier(k) for k in expr.key_columns)
            parts.append(f"KEY ({keys})")

        src_keys = ", ".join(self.format_identifier(k) for k in expr.source_key)
        if expr.references_source:
            ref_table, ref_cols = expr.references_source
            ref_cols_str = ", ".join(self.format_identifier(c) for c in ref_cols)
            src_part = f"SOURCE KEY ({src_keys}) REFERENCES {self.format_identifier(ref_table)} ({ref_cols_str})"
        else:
            src_part = f"SOURCE KEY ({src_keys})"
        parts.append(src_part)

        dst_keys = ", ".join(self.format_identifier(k) for k in expr.destination_key)
        if expr.references_destination:
            ref_table, ref_cols = expr.references_destination
            ref_cols_str = ", ".join(self.format_identifier(c) for c in ref_cols)
            dst_part = f"DESTINATION KEY ({dst_keys}) REFERENCES {self.format_identifier(ref_table)} ({ref_cols_str})"
        else:
            dst_part = f"DESTINATION KEY ({dst_keys})"
        parts.append(dst_part)

        if expr.labels:
            labels = " ".join(
                f"LABEL {self.format_identifier(label)}" for label in expr.labels
            )
            parts.append(labels)

        if expr.properties is not None:
            sql, _ = expr.properties.to_sql()
            parts.append(sql)

        sql = " ".join(parts)
        return sql, ()

    def format_create_property_graph_statement(self, expr: "CreatePropertyGraphStatement") -> Tuple[str, tuple]:
        """Format a CREATE PROPERTY GRAPH DDL statement.

        Args:
            expr: CreatePropertyGraphStatement exposing graph name,
                ``if_not_exists``, vertex tables and edge tables.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is always empty.

        Raises:
            TypeError: ``CreatePropertyGraphStatement.graph`` is not a
            PropertyGraph. Another object kind would have had its own name rendered
            as the graph's.
            UnsupportedFeatureError: If the dialect does not support property
                graph tables.
        """
        if not isinstance(expr.graph, PropertyGraph):
            raise TypeError(
                f"CreatePropertyGraphStatement.graph must be a PropertyGraph, "
                f"got {type(expr.graph).__name__}"
            )
        if not self.supports_graph_table():
            raise UnsupportedFeatureError(self.name, "CREATE PROPERTY GRAPH")

        parts = ["CREATE PROPERTY GRAPH"]
        if expr.if_not_exists:
            parts.append("IF NOT EXISTS")
        parts.append(expr.graph.to_sql()[0])

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

    def format_drop_property_graph_statement(self, expr: "DropPropertyGraphStatement") -> Tuple[str, tuple]:
        """Format a DROP PROPERTY GRAPH DDL statement.

        Args:
            expr: DropPropertyGraphStatement exposing graph name,
                ``if_exists`` and ``cascade``.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is always empty.

        Raises:
            TypeError: ``DropPropertyGraphStatement.graph`` is not a PropertyGraph.
            Another object kind would have had its own name rendered as the graph's.
            UnsupportedFeatureError: If the dialect does not support property
                graph tables.
        """
        if not isinstance(expr.graph, PropertyGraph):
            raise TypeError(
                f"DropPropertyGraphStatement.graph must be a PropertyGraph, "
                f"got {type(expr.graph).__name__}"
            )
        if not self.supports_graph_table():
            raise UnsupportedFeatureError(self.name, "DROP PROPERTY GRAPH")

        parts = ["DROP PROPERTY GRAPH"]
        if expr.if_exists:
            parts.append("IF EXISTS")
        parts.append(expr.graph.to_sql()[0])
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

    def format_alter_property_graph_statement(self, expr: "AlterPropertyGraphStatement") -> Tuple[str, tuple]:
        """Format an ALTER PROPERTY GRAPH DDL statement.

        Args:
            expr: AlterPropertyGraphStatement exposing graph name, action,
                target, vertex tables and edge tables.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is always empty.

        Raises:
            TypeError: ``AlterPropertyGraphStatement.graph`` is not a
            PropertyGraph. Another object kind would have had its own name rendered
            as the graph's.
            UnsupportedFeatureError: If the dialect does not support property
                graph tables.
        """
        if not isinstance(expr.graph, PropertyGraph):
            raise TypeError(
                f"AlterPropertyGraphStatement.graph must be a PropertyGraph, "
                f"got {type(expr.graph).__name__}"
            )
        if not self.supports_graph_table():
            raise UnsupportedFeatureError(self.name, "ALTER PROPERTY GRAPH")

        from ...expression.graph import AlterPropertyGraphStatement, EdgeTableDefinition, VertexTable

        if not isinstance(expr, AlterPropertyGraphStatement):
            raise TypeError(
                "ALTER PROPERTY GRAPH expression must be an "
                "AlterPropertyGraphStatement"
            )
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
        if any(not isinstance(table, EdgeTableDefinition) for table in edge_tables):
            raise TypeError("ALTER PROPERTY GRAPH edge tables must be EdgeTableDefinition instances")

        parts = [
            "ALTER PROPERTY GRAPH",
            expr.graph.to_sql()[0],
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
