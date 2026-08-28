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


class QuantifiedPath(BaseExpression):
    """A variable-length (quantified) graph edge path pattern.

    Represents SQL/PGQ quantified path patterns such as:
    - ``-[e IS "label"]+``  (one or more)
    - ``-[e IS "label"]*``  (zero or more)
    - ``-[e IS "label"]{2,5}``  (between 2 and 5)

    Not all SQL dialects support quantified paths; they are a SQL/PGQ
    standard feature.  Dialects that implement this capability must
    override :meth:`format_quantified_path`.
    """

    def __init__(self, dialect: "SQLDialectBase",
                 edge: "GraphEdge",
                 min_repeats: Optional[int] = None,
                 max_repeats: Optional[int] = None):
        super().__init__(dialect)
        self.edge = edge
        self.min_repeats = min_repeats
        self.max_repeats = max_repeats

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_quantified_path(self)


class PathPattern(BaseExpression):
    """A single graph path pattern within a MATCH clause.

    Wraps a sequence of vertices, edges, and quantified paths into one
    logical pattern.  When a :class:`MatchClause` holds multiple
    ``PathPattern`` instances they are rendered as comma-separated
    patterns (``MATCH p1, p2``).

    .. code-block:: python

        p1 = PathPattern(dialect, a, e1, b)
        p2 = PathPattern(dialect, b, e2, c)
        match = MatchClause(dialect, p1, p2)
        # -> MATCH (a)-[e1]->(b), (b)-[e2]->(c)
    """

    def __init__(self, dialect: "SQLDialectBase",
                 *path: Union["GraphVertex", "GraphEdge", "QuantifiedPath"]):
        super().__init__(dialect)
        self.path = list(path)

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_path_pattern(self)


class MatchClause(BaseExpression):
    """Represents a MATCH clause with one or more path patterns.

    Accepts either a flat sequence of vertices/edges (legacy single-path
    API) or one or more explicit :class:`PathPattern` instances for
    comma-separated multi-pattern support.

    .. code-block:: python

        # Single path (legacy API)
        MatchClause(dialect, a, e, b)
        # -> MATCH (a)-[e]->(b)

        # Multiple comma-separated patterns
        MatchClause(dialect, PathPattern(dialect, a, e, b),
                           PathPattern(dialect, b, f, c))
        # -> MATCH (a)-[e]->(b), (b)-[f]->(c)
    """

    def __init__(self, dialect: "SQLDialectBase",
                 *args: Union["PathPattern", "GraphVertex", "GraphEdge", "QuantifiedPath"]):
        super().__init__(dialect)
        # Keep the raw constructor arguments so that the introspection-based
        # get_params() (and therefore serialization round-trip) can rebuild
        # an equivalent instance.
        self.args = list(args)
        if len(args) > 0 and isinstance(args[0], PathPattern):
            self.patterns = list(args)
        else:
            self.patterns = [PathPattern(dialect, *args)]

    @property
    def path(self) -> List[Union["GraphVertex", "GraphEdge", "QuantifiedPath"]]:
        """Backward-compatible access to the first (or only) pattern's elements.

        For single-pattern ``MatchClause`` instances this returns the flat
        element list as the previous ``.path`` attribute did.  Raises
        ``ValueError`` when multiple patterns are present.
        """
        if len(self.patterns) != 1:
            raise ValueError(
                "MatchClause.path is ambiguous when multiple patterns exist; "
                "use MatchClause.patterns instead."
            )
        return self.patterns[0].path

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
