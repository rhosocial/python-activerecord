# src/rhosocial/activerecord/backend/expression/functions/grouping.py
"""Grouping function factories."""

from typing import Union, List, TYPE_CHECKING

from ..bases import BaseExpression
from ..core import Column
from ..query_parts import GroupingExpression

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


def grouping_sets(
    dialect: "SQLDialectBase", *grouping_lists: List[Union[str, "BaseExpression"]]
) -> "GroupingExpression":
    """
    Creates a GROUPING SETS expression for use in GROUP BY clauses.

    Usage rules:
    - To generate GROUPING SETS((col1, col2), (col3)), pass column lists:
      grouping_sets(dialect, ["col1", "col2"], ["col3"])

    Args:
        dialect: The SQL dialect instance
        *grouping_lists: Variable number of lists, each containing expressions to group by

    Returns:
        A GroupingExpression instance representing the GROUPING SETS operation
    """
    processed_lists = []
    for grouping_list in grouping_lists:
        processed_exprs = [
            expr if isinstance(expr, BaseExpression) else Column(dialect, expr) for expr in grouping_list
        ]
        processed_lists.append(processed_exprs)
    return GroupingExpression(dialect, "GROUPING SETS", processed_lists)


def rollup(dialect: "SQLDialectBase", *exprs: Union[str, "BaseExpression"]) -> "GroupingExpression":
    """
    Creates a ROLLUP expression for use in GROUP BY clauses.

    Usage rules:
    - To generate ROLLUP(col1, col2), pass expressions:
      rollup(dialect, "col1", "col2") or rollup(dialect, Column(dialect, "col1"), Column(dialect, "col2"))

    Args:
        dialect: The SQL dialect instance
        *exprs: Variable number of expressions to include in the ROLLUP

    Returns:
        A GroupingExpression instance representing the ROLLUP operation
    """
    processed_exprs = [expr if isinstance(expr, BaseExpression) else Column(dialect, expr) for expr in exprs]
    return GroupingExpression(dialect, "ROLLUP", processed_exprs)


def cube(dialect: "SQLDialectBase", *exprs: Union[str, "BaseExpression"]) -> "GroupingExpression":
    """
    Creates a CUBE expression for use in GROUP BY clauses.

    Usage rules:
    - To generate CUBE(col1, col2), pass expressions:
      cube(dialect, "col1", "col2") or cube(dialect, Column(dialect, "col1"), Column(dialect, "col2"))

    Args:
        dialect: The SQL dialect instance
        *exprs: Variable number of expressions to include in the CUBE

    Returns:
        A GroupingExpression instance representing the CUBE operation
    """
    processed_exprs = [expr if isinstance(expr, BaseExpression) else Column(dialect, expr) for expr in exprs]
    return GroupingExpression(dialect, "CUBE", processed_exprs)
