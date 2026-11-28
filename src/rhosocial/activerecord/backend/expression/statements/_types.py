# src/rhosocial/activerecord/backend/expression/statements/_types.py
"""Shared type aliases for statement expressions."""

from typing import Union, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.sources.relation import NamedRelationRef

if TYPE_CHECKING:  # pragma: no cover
    from ..sources.subquery import Subquery
    from ..sources.query_sources import SetOperation, ValuesExpression, TableFunctionExpression, LateralExpression
    from ..query_parts.query_parts import JoinClause
    from ..statements.graph import GraphTableExpression

FromSourceType = Union[
    str,  # Table name as string
    "NamedRelationRef",  # Single table
    "Subquery",  # Subquery
    "SetOperation",  # Set operations (UNION, etc.)
    "JoinClause",  # Join expression (treated as a single object)
    "ValuesExpression",  # VALUES expression
    "TableFunctionExpression",  # Table function
    "LateralExpression",  # LATERAL expression
    "GraphTableExpression",  # GRAPH_TABLE expression (SQL/PGQ)
]
