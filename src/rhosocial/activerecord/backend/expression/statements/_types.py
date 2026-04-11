# src/rhosocial/activerecord/backend/expression/statements/_types.py
"""Shared type aliases for statement expressions."""

from typing import Union, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ..core import Subquery, TableExpression
    from ..query_sources import SetOperationExpression, ValuesExpression, TableFunctionExpression, LateralExpression
    from ..query_parts import JoinExpression

FromSourceType = Union[
    str,  # Table name as string
    "TableExpression",  # Single table
    "Subquery",  # Subquery
    "SetOperationExpression",  # Set operations (UNION, etc.)
    "JoinExpression",  # Join expression (treated as a single object)
    "ValuesExpression",  # VALUES expression
    "TableFunctionExpression",  # Table function
    "LateralExpression",  # LATERAL expression
]
