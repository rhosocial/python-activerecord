# src/rhosocial/activerecord/backend/expression_/graph.py
"""
SQL Graph Query (MATCH) expression building blocks.
"""
from enum import Enum
from typing import Any, List, Optional, Tuple, Union, TYPE_CHECKING

from . import bases

if TYPE_CHECKING:
    from ..dialect import SQLDialectBase


class GraphEdgeDirection(Enum):
    """Specifies the direction of an edge in a graph pattern."""
    LEFT = "<-"
    RIGHT = "->"
    ANY = "<->"
    NONE = "-"


class GraphVertex(bases.BaseExpression):
    """Represents a vertex in a graph pattern."""
    def __init__(self, dialect: "SQLDialectBase", variable: str, table: str):
        super().__init__(dialect)
        self.variable = variable
        self.table = table

    def to_sql(self) -> Tuple[str, tuple]:
        return f"({self.variable} IS {self.dialect.format_identifier(self.table)})", ()


class GraphEdge(bases.BaseExpression):
    """Represents an edge in a graph pattern."""
    def __init__(self, dialect: "SQLDialectBase", variable: str, table: str, direction: GraphEdgeDirection):
        super().__init__(dialect)
        self.variable = variable
        self.table = table
        self.direction = direction

    def to_sql(self) -> Tuple[str, tuple]:
        left_arrow, right_arrow = "", ""
        if self.direction in [GraphEdgeDirection.LEFT, GraphEdgeDirection.ANY]:
            left_arrow = "<"
        if self.direction in [GraphEdgeDirection.RIGHT, GraphEdgeDirection.ANY]:
            right_arrow = ">"
        
        return f"{left_arrow}-[{self.variable} IS {self.dialect.format_identifier(self.table)}]-{right_arrow}", ()


class MatchClause(bases.BaseExpression):
    """Represents a MATCH clause with one or more path patterns."""
    def __init__(self, dialect: "SQLDialectBase", *path: Union[GraphVertex, GraphEdge]):
        super().__init__(dialect)
        self.path = list(path)

    def to_sql(self) -> Tuple[str, tuple]:
        path_sql, all_params = [], []
        for part in self.path:
            sql, params = part.to_sql()
            path_sql.append(sql)
            all_params.extend(params)
        
        match_sql, match_params = self.dialect.format_match_clause(path_sql, tuple(all_params))
        return match_sql, match_params
