# src/rhosocial/activerecord/backend/expression/pivot.py
"""PIVOT / UNPIVOT clause expressions.

PIVOT rotates rows into columns (a cross-tabulation); UNPIVOT rotates
columns back into rows. Both are supported natively by SQL Server, Oracle
(11g+), Snowflake and others with a shared core syntax:

    PIVOT (agg(value_column) FOR pivot_column IN (v1, v2, ...)) [alias]
    UNPIVOT [INCLUDE|EXCLUDE NULLS] (value_column FOR pivot_column IN (c1, c2)) [alias]

Dialects override ``format_pivot_value`` / ``format_pivot_expression`` /
``format_unpivot_expression`` for their own extensions.
"""
from typing import List, Optional, Union, TYPE_CHECKING

from .bases import BaseExpression

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase


class PivotExpression(BaseExpression):
    """A PIVOT clause expression (row-to-column transformation).

    Example:
        >>> PivotExpression(
        ...     dialect, "SUM", "amount", "month", ["Jan", "Feb"], alias="p"
        ... )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        aggregate_function: str,
        value_column: str,
        pivot_column: str,
        values: Optional[List[Union[str, int, float, "BaseExpression"]]] = None,
        alias: Optional[str] = None,
        default: Optional[object] = None,
    ):
        super().__init__(dialect)
        self.aggregate_function = aggregate_function
        self.value_column = value_column
        self.pivot_column = pivot_column
        self.values = list(values) if values else []
        self.alias = alias
        self.default = default

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_pivot_expression"


class UnpivotExpression(BaseExpression):
    """An UNPIVOT clause expression (column-to-row transformation)."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        value_column: str,
        pivot_column: str,
        columns: Optional[List[str]] = None,
        include_nulls: bool = False,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.value_column = value_column
        self.pivot_column = pivot_column
        self.columns = list(columns) if columns else []
        self.include_nulls = include_nulls
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_unpivot_expression"
