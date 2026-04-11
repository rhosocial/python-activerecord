# src/rhosocial/activerecord/backend/expression/functions/json.py
"""JSON function factories."""

from typing import Union, Optional, TYPE_CHECKING

from ..bases import BaseExpression
from ..aggregates import AggregateFunctionCall
from ..core import Column, FunctionCall, Literal
from ..advanced_functions import JSONExpression

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


def json_extract(
    dialect: "SQLDialectBase", column: Union[str, "BaseExpression"], path: str
) -> "JSONExpression":
    """
    Creates a JSON extract operation (e.g., column->path).

    Usage rules:
    - To generate column->path, pass a Column object: json_extract(dialect, Column(dialect, "json_col"), "$.field")

    Args:
        dialect: The SQL dialect instance
        column: The JSON column to extract from. If a string is passed, it's treated as a column name.
                If a BaseExpression is passed, it's used as-is.
        path: The JSON path to extract.

    Returns:
        A JSONExpression instance representing the JSON extract operation
    """
    target_column = column if isinstance(column, BaseExpression) else Column(dialect, column)
    return JSONExpression(dialect, target_column, path, operation="->")


def json_extract_text(
    dialect: "SQLDialectBase", column: Union[str, "BaseExpression"], path: str
) -> "JSONExpression":
    """
    Creates a JSON extract text operation (e.g., column->>path).

    Usage rules:
    - To generate column->>path, pass a Column object:
      json_extract_text(dialect, Column(dialect, "json_col"), "$.field")

    Args:
        dialect: The SQL dialect instance
        column: The JSON column to extract from. If a string is passed, it's treated as a column name.
                If a BaseExpression is passed, it's used as-is.
        path: The JSON path to extract as text.

    Returns:
        A JSONExpression instance representing the JSON extract text operation
    """
    target_column = column if isinstance(column, BaseExpression) else Column(dialect, column)
    return JSONExpression(dialect, target_column, path, operation="->>")


def json_build_object(
    dialect: "SQLDialectBase", *key_value_pairs: Union[str, "BaseExpression"]
) -> "FunctionCall":
    """
    Creates a JSON_BUILD_OBJECT function call.

    Usage rules:
    - To generate JSON_BUILD_OBJECT(key1, val1, key2, val2, ...), pass expressions:
      json_build_object(dialect, "key1", Column(dialect, "col1"), "key2", Column(dialect, "col2"))

    Args:
        dialect: The SQL dialect instance
        *key_value_pairs: Alternating sequence of key-value expressions.
            Keys and values can be strings (literal) or BaseExpression.

    Returns:
        A FunctionCall instance representing the JSON_BUILD_OBJECT function
    """
    # Expect alternating sequence of key-value expressions
    processed_args = []
    for arg in key_value_pairs:
        processed_args.append(arg if isinstance(arg, BaseExpression) else Literal(dialect, arg))
    return FunctionCall(dialect, "JSON_BUILD_OBJECT", *processed_args)


def json_array_elements(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "FunctionCall":
    """
    Creates a JSON_ARRAY_ELEMENTS function call.

    Usage rules:
    - To generate JSON_ARRAY_ELEMENTS(column), pass a Column object:
      json_array_elements(dialect, Column(dialect, "json_array"))

    Args:
        dialect: The SQL dialect instance
        expr: The JSON array expression. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the JSON_ARRAY_ELEMENTS function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    return FunctionCall(dialect, "JSON_ARRAY_ELEMENTS", target_expr)


def json_objectagg(
    dialect: "SQLDialectBase",
    key_expr: Union[str, "BaseExpression"],
    value_expr: Union[str, "BaseExpression"],
) -> "AggregateFunctionCall":
    """Creates a JSON_OBJECTAGG aggregate function call."""
    key_target = key_expr if isinstance(key_expr, BaseExpression) else Column(dialect, key_expr)
    value_target = value_expr if isinstance(value_expr, BaseExpression) else Column(dialect, value_expr)
    return AggregateFunctionCall(dialect, "JSON_OBJECTAGG", key_target, value_target)


def json_arrayagg(
    dialect: "SQLDialectBase",
    expr: Union[str, "BaseExpression"],
    is_distinct: bool = False,
    alias: Optional[str] = None,
) -> "AggregateFunctionCall":
    """Creates a JSON_ARRAYAGG aggregate function call."""
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    return AggregateFunctionCall(dialect, "JSON_ARRAYAGG", target_expr, is_distinct=is_distinct, alias=alias)
