# src/rhosocial/activerecord/backend/expression/graph.py
"""
SQL Graph Query (MATCH) expression building blocks.

Implements SQL/PGQ (Property Graph Query) standard as defined in
SQL 2023 (ISO/IEC 9075-16:2023) for querying property graphs.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union, TYPE_CHECKING

from .bases import BaseExpression, SQLQueryAndParams

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase
    from .query_parts import WhereClause


class GraphEdgeDirection(Enum):
    """Specifies the direction of an edge in a graph pattern according to SQL 2023 standard."""

    LEFT = "<-"  # Left-directed: <-[edge]-
    RIGHT = "->"  # Right-directed: -[edge]->
    ANY = "<->"  # Bidirectional: <-[edge]->
    NONE = "-"  # Undirected: -[edge]-


class GraphVertex(BaseExpression):
    """Represents a vertex in a graph pattern according to SQL 2023 standard."""

    def __init__(self, dialect: "SQLDialectBase", variable: Optional[str], table: str,
                 where: Optional["WhereClause"] = None):
        super().__init__(dialect)
        self.variable = variable
        self.table = table
        self.where = where

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_graph_vertex(self)


class GraphEdge(BaseExpression):
    """Represents an edge in a graph pattern."""

    def __init__(self, dialect: "SQLDialectBase",
                 variable: Optional[str] = None,
                 table: Optional[str] = None,
                 direction: GraphEdgeDirection = GraphEdgeDirection.RIGHT):
        super().__init__(dialect)
        self.variable = variable
        self.table = table
        self.direction = direction

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_graph_edge(self)


class MatchClause(BaseExpression):
    """Represents a MATCH clause with one or more path patterns according to SQL 2023 standard."""

    def __init__(self, dialect: "SQLDialectBase", *path: Union[GraphVertex, GraphEdge]):
        super().__init__(dialect)
        self.path = list(path)

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_match_clause(self)


class GraphColumn:
    """A single column definition in a GRAPH_TABLE COLUMNS clause."""

    def __init__(self, variable: str, property_name: str, alias: Optional[str] = None):
        self.variable = variable
        self.property_name = property_name
        self.alias = alias


class ColumnsClause(BaseExpression):
    """Represents the COLUMNS clause in a GRAPH_TABLE expression."""

    def __init__(self, dialect: "SQLDialectBase", *columns: GraphColumn):
        super().__init__(dialect)
        self.columns = list(columns)

    def to_sql(self) -> "SQLQueryAndParams":
        parts = []
        for col in self.columns:
            col_str = f"{self.dialect.format_identifier(col.variable)}.{self.dialect.format_identifier(col.property_name)}"
            if col.alias:
                col_str += f" AS {self.dialect.format_identifier(col.alias)}"
            parts.append(col_str)
        return f"COLUMNS ({', '.join(parts)})", ()


class GraphTableExpression(BaseExpression):
    """Represents a GRAPH_TABLE (graph MATCH ... COLUMNS (...)) expression.

    Acts as a FROM clause item, producing a tabular result set from graph pattern matching."""

    def __init__(self, dialect: "SQLDialectBase", graph_name: str,
                 match: MatchClause, columns: ColumnsClause,
                 alias: Optional[str] = None):
        super().__init__(dialect)
        self.graph_name = graph_name
        self.match = match
        self.columns = columns
        self.alias = alias

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_graph_table_expression(self)


class TablePropertiesClause(BaseExpression):
    """Represents the PROPERTIES clause in a vertex/edge table definition.

    Renders: PROPERTIES (columns) | PROPERTIES ALL COLUMNS | PROPERTIONS NONE

    When columns is None, renders PROPERTIES ALL COLUMNS.
    When columns is an empty list, renders PROPERTIES NONE.
    When columns is a non-empty list, renders PROPERTIES (col1, col2, ...)."""

    def __init__(self, dialect: "SQLDialectBase",
                 columns: Optional[List[str]] = None):
        super().__init__(dialect)
        self.columns = columns  # None = ALL COLUMNS, [] = NONE, [...] = specific

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_table_properties_clause(self)


class VertexTable(BaseExpression):
    """Represents a vertex table definition in CREATE PROPERTY GRAPH.

    Renders: table [AS alias] [LABEL l1 [LABEL l2 ...]] [KEY (cols)] [PROPERTIES ...]"""

    def __init__(self, dialect: "SQLDialectBase", table: str,
                 labels: Optional[List[str]] = None,
                 key_columns: Optional[List[str]] = None,
                 properties: Optional["TablePropertiesClause"] = None,
                 alias: Optional[str] = None):
        super().__init__(dialect)
        self.table = table
        self.labels = labels
        self.key_columns = key_columns
        self.properties = properties
        self.alias = alias

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_vertex_table(self)


class EdgeTable(BaseExpression):
    """Represents an edge table definition in CREATE PROPERTY GRAPH.

    Renders: table [AS alias] [KEY (cols)] SOURCE KEY (cols) [REFERENCES t (c)]
            DESTINATION KEY (cols) [REFERENCES t (c)] [LABEL ...] [PROPERTIES ...]"""

    def __init__(self, dialect: "SQLDialectBase", table: str,
                 source_key: List[str], destination_key: List[str],
                 key_columns: Optional[List[str]] = None,
                 references_source: Optional[Tuple[str, List[str]]] = None,
                 references_destination: Optional[Tuple[str, List[str]]] = None,
                 labels: Optional[List[str]] = None,
                 properties: Optional["TablePropertiesClause"] = None,
                 alias: Optional[str] = None):
        super().__init__(dialect)
        self.table = table
        self.source_key = source_key
        self.destination_key = destination_key
        self.key_columns = key_columns
        self.references_source = references_source
        self.references_destination = references_destination
        self.labels = labels
        self.properties = properties
        self.alias = alias

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_edge_table(self)


class CreatePropertyGraphExpression(BaseExpression):
    """Represents a CREATE PROPERTY GRAPH DDL statement."""

    def __init__(self, dialect: "SQLDialectBase", graph_name: str,
                 vertex_tables: List[VertexTable],
                 edge_tables: Optional[List[EdgeTable]] = None,
                 if_not_exists: bool = False,
                 *,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect)
        self.graph_name = graph_name
        self.vertex_tables = vertex_tables
        self.edge_tables = edge_tables or []
        self.if_not_exists = if_not_exists
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_create_property_graph_statement(self)


class DropPropertyGraphExpression(BaseExpression):
    """Represents a DROP PROPERTY GRAPH DDL statement."""

    def __init__(self, dialect: "SQLDialectBase", graph_name: str,
                 if_exists: bool = False, cascade: bool = False,
                 *,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect)
        self.graph_name = graph_name
        self.if_exists = if_exists
        self.cascade = cascade
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_drop_property_graph_statement(self)


class AlterPropertyGraphExpression(BaseExpression):
    """Represents an ALTER PROPERTY GRAPH DDL statement."""

    def __init__(self, dialect: "SQLDialectBase", graph_name: str,
                 action: str, target: str,
                 vertex_tables: Optional[List[VertexTable]] = None,
                 edge_tables: Optional[List[EdgeTable]] = None,
                 *,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect)
        self.graph_name = graph_name
        self.action = action
        self.target = target
        self.vertex_tables = vertex_tables or []
        self.edge_tables = edge_tables or []
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_alter_property_graph_statement(self)
