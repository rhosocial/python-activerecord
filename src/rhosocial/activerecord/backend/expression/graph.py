# src/rhosocial/activerecord/backend/expression/graph.py
"""
SQL Graph Query (MATCH) expression building blocks.

Implements SQL/PGQ (Property Graph Query) standard as defined in
SQL 2023 (ISO/IEC 9075-16:2023) for querying property graphs.
"""
from enum import Enum
from typing import Any, List, Optional, Tuple, Union, TYPE_CHECKING

from . import bases

# if TYPE_CHECKING:
#     from ..dialect import SQLDialectBase


class GraphEdgeDirection(Enum):
    """Specifies the direction of an edge in a graph pattern according to SQL 2023 standard."""
    LEFT = "<-"  # Left-directed: <-[edge]-
    RIGHT = "->"  # Right-directed: -[edge]->
    ANY = "<->"  # Bidirectional: <-[edge]->
    NONE = "-"   # Undirected: -[edge]-


class GraphVertex(bases.BaseExpression):
    """Represents a vertex in a graph pattern according to SQL 2023 standard."""
    def __init__(self, dialect: "SQLDialectBase", variable: str, table: str):
        super().__init__(dialect)
        self.variable = variable
        self.table = table

    def to_sql(self) -> Tuple[str, tuple]:
        # According to SQL 2023 (ISO/IEC 9075-16), vertex syntax is (variable IS table)
        return f"({self.variable} IS {self.dialect.format_identifier(self.table)})", ()


class GraphEdge(bases.BaseExpression):
    """Represents an edge in a graph pattern."""
    def __init__(self, dialect: "SQLDialectBase", variable: str, table: str, direction: GraphEdgeDirection):
        super().__init__(dialect)
        self.variable = variable
        self.table = table
        self.direction = direction

    def to_sql(self) -> Tuple[str, tuple]:
        # According to SQL 2023 (ISO/IEC 9075-16), the edge syntax is:
        # -[variable IS table]-> for right-directed edges
        # <-[variable IS table]- for left-directed edges
        # -[variable IS table]- for undirected edges (NONE)
        # <-[variable IS table]-> for bidirectional edges (ANY)
        left_arrow, right_arrow = "", ""
        if self.direction in [GraphEdgeDirection.LEFT, GraphEdgeDirection.ANY]:
            left_arrow = "<"
        if self.direction in [GraphEdgeDirection.RIGHT, GraphEdgeDirection.ANY]:
            right_arrow = ">"

        # For different directions, construct the correct syntax
        if self.direction == GraphEdgeDirection.RIGHT:
            # Right-directed: -[var IS table]->
            return f"-[{self.variable} IS {self.dialect.format_identifier(self.table)}]->", ()
        elif self.direction == GraphEdgeDirection.LEFT:
            # Left-directed: <-[var IS table]-
            return f"<-[{self.variable} IS {self.dialect.format_identifier(self.table)}]-", ()
        elif self.direction == GraphEdgeDirection.ANY:
            # Bidirectional: <-[var IS table]->
            return f"<-[{self.variable} IS {self.dialect.format_identifier(self.table)}]->", ()
        else:  # GraphEdgeDirection.NONE (undirected)
            # Undirected: -[var IS table]-
            return f"-[{self.variable} IS {self.dialect.format_identifier(self.table)}]-", ()


class MatchClause(bases.BaseExpression):
    """Represents a MATCH clause with one or more path patterns according to SQL 2023 standard."""
    def __init__(self, dialect: "SQLDialectBase", *path: Union[GraphVertex, GraphEdge]):
        super().__init__(dialect)
        self.path = list(path)

    def to_sql(self) -> Tuple[str, tuple]:
        """
        Generates SQL for the MATCH clause according to SQL 2023 standard.
        The actual formatting depends on the dialect's implementation of format_match_clause.
        """
        path_sql, all_params = [], []
        for part in self.path:
            sql, params = part.to_sql()
            path_sql.append(sql)
            all_params.extend(params)

        match_sql, match_params = self.dialect.format_match_clause(path_sql, tuple(all_params))
        return match_sql, match_params
