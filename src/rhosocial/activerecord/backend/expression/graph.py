# src/rhosocial/activerecord/backend/expression/graph.py
"""
SQL Graph Query (MATCH) expression building blocks.
"""
from enum import Enum
from typing import Any, List, Optional, Tuple, Union

from .base import BaseExpression
from ..dialect import SQLDialectBase


class GraphEdgeDirection(Enum):
    LEFT = "<-"
    RIGHT = "->"
    ANY = "<->"
    NONE = "-"


class GraphVertex(BaseExpression):
    """Represents a vertex in a graph pattern."""
    def __init__(self, dialect: SQLDialectBase, variable: str, table: str):
        super().__init__(dialect)
        self.variable = variable
        self.table = table

    def to_sql(self) -> Tuple[str, tuple]:
        return f"({self.variable} IS {self.dialect.format_identifier(self.table)})", ()


class GraphEdge(BaseExpression):
    """Represents an edge in a graph pattern."""
    def __init__(self, dialect: SQLDialectBase, variable: str, table: str, direction: GraphEdgeDirection):
        super().__init__(dialect)
        self.variable = variable
        self.table = table
        self.direction = direction

    def to_sql(self) -> Tuple[str, tuple]:
        return f"{self.direction.value}[{self.variable} IS {self.dialect.format_identifier(self.table)}]", ()


class MatchClause(BaseExpression):
    """Represents a MATCH clause with one or more path patterns."""
    def __init__(self, dialect: SQLDialectBase, *path: Union[GraphVertex, GraphEdge]):
        super().__init__(dialect)
        self.path = list(path)

    def to_sql(self) -> Tuple[str, tuple]:
        path_sql = []
        all_params: List[Any] = []
        for part in self.path:
            sql, params = part.to_sql()
            path_sql.append(sql)
            all_params.extend(params)
        
        return f"MATCH {' '.join(path_sql)}", tuple(all_params)
