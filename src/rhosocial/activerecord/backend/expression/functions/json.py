# src/rhosocial/activerecord/backend/expression/functions/json.py
"""JSON function factories."""

from typing import Optional, TYPE_CHECKING

from ..bases import BaseExpression
from ..core import (
    Column,
    JSONValueExpression,
    FunctionCall,
    Literal,
)
from ..advanced_functions import JSONDocumentExpression, JSONTextExpression

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


def json_extract(dialect: "SQLDialectBase", column: "BaseExpression", path: str) -> "JSONDocumentExpression":
    """
    Creates a JSON extract operation (e.g., column->path).

    Usage rules:
    - To generate column->path, pass a Column object: json_extract(dialect, Column(dialect, "json_col"), "$.field")

    Args:
        dialect: The SQL dialect instance
        column: The JSON column to extract from, as an expression. A bare string is no
                longer part of the contract; it is still coerced to a column at runtime.
        path: The JSON path to extract.

    Returns:
        A JSONDocumentExpression instance representing the JSON extract operation
    """
    target_column = column if isinstance(column, BaseExpression) else Column(dialect, column)
    return JSONDocumentExpression(dialect, target_column, path, operation="->")


def json_extract_text(dialect: "SQLDialectBase", column: "BaseExpression", path: str) -> "JSONTextExpression":
    """
    Creates a JSON extract text operation (e.g., column->>path).

    Usage rules:
    - To generate column->>path, pass a Column object:
      json_extract_text(dialect, Column(dialect, "json_col"), "$.field")

    Args:
        dialect: The SQL dialect instance
        column: The JSON column to extract from, as an expression. A bare string is no
                longer part of the contract; it is still coerced to a column at runtime.
        path: The JSON path to extract as text.

    Returns:
        A JSONTextExpression instance representing the JSON extract text operation
    """
    target_column = column if isinstance(column, BaseExpression) else Column(dialect, column)
    # `->>` yields text, so it arrives as JSONTextExpression and carries the
    # string operations. It used to be built as a JSONDocumentExpression and described
    # as a string by a tag, which meant the JSON accessors it was meant to end
    # the chain with stayed reachable -- the node class served both arrow
    # directions and could not drop them per instance.
    return JSONTextExpression(dialect, target_column, path, operation="->>")


def json_build_object(dialect: "SQLDialectBase", *key_value_pairs: "BaseExpression") -> "JSONValueExpression":
    """
    Creates a JSON_BUILD_OBJECT function call.

    Usage rules:
    - To generate JSON_BUILD_OBJECT(key1, val1, key2, val2, ...), pass expressions:
      json_build_object(dialect, "key1", Column(dialect, "col1"), "key2", Column(dialect, "col2"))

    Args:
        dialect: The SQL dialect instance
        *key_value_pairs: Alternating sequence of key-value expressions.
            Keys and values are expressions. A bare string is no longer part of the
            contract; it is still bound as a literal at runtime.

    Returns:
        A JSONValueExpression wrapping JSON_BUILD_OBJECT
    """
    # Expect alternating sequence of key-value expressions
    processed_args = []
    for arg in key_value_pairs:
        processed_args.append(arg if isinstance(arg, BaseExpression) else Literal(dialect, arg))
    return JSONValueExpression(dialect, FunctionCall(dialect, 'JSON_BUILD_OBJECT', *processed_args))


def json_array_elements(dialect: "SQLDialectBase", expr: "BaseExpression") -> "JSONValueExpression":
    """
    Creates a JSON_ARRAY_ELEMENTS function call.

    Usage rules:
    - To generate JSON_ARRAY_ELEMENTS(column), pass a Column object:
      json_array_elements(dialect, Column(dialect, "json_array"))

    Args:
        dialect: The SQL dialect instance
        expr: The JSON array expression, as an expression. A bare string is no longer part
              of the contract; it is still coerced to a column at runtime.

    Returns:
        A JSONValueExpression wrapping JSON_ARRAY_ELEMENTS
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    return JSONValueExpression(dialect, FunctionCall(dialect, 'JSON_ARRAY_ELEMENTS', target_expr))


def json_objectagg(
    dialect: "SQLDialectBase",
    key_expr: "BaseExpression",
    value_expr: "BaseExpression",
) -> "FunctionCall":
    """Creates a JSON_OBJECTAGG aggregate function call."""
    key_target = key_expr if isinstance(key_expr, BaseExpression) else Column(dialect, key_expr)
    value_target = value_expr if isinstance(value_expr, BaseExpression) else Column(dialect, value_expr)
    return JSONValueExpression(
        dialect,
        FunctionCall(dialect, "JSON_OBJECTAGG", key_target, value_target, is_aggregate=True),
    )


def json_arrayagg(
    dialect: "SQLDialectBase",
    expr: "BaseExpression",
    is_distinct: bool = False,
    alias: Optional[str] = None,
) -> "FunctionCall":
    """Creates a JSON_ARRAYAGG aggregate function call."""
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    return JSONValueExpression(
        dialect,
        FunctionCall(
            dialect,
            "JSON_ARRAYAGG",
            target_expr,
            is_distinct=is_distinct,
            alias=alias,
            is_aggregate=True,
        ),
    )