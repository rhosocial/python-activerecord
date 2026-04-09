# src/rhosocial/activerecord/backend/impl/sqlite/functions/json.py
"""
SQLite JSON function factories.

SQLite 3.38+ includes the json1 extension for JSON manipulation.
These functions provide a consistent API for working with JSON data in SQLite.

Functions: json, json_array, json_object, json_extract, json_type,
json_valid, json_quote, json_remove, json_set, json_insert, json_replace,
json_patch, json_array_length, json_array_unpack, json_object_pack,
json_object_retrieve, json_object_length, json_object_keys, json_tree,
json_each
"""

from typing import Union, Optional, Any, TYPE_CHECKING

from rhosocial.activerecord.backend.expression import bases, core

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase
    from .dialect import SQLiteDialect


def _convert_to_expression(
    dialect: "SQLDialectBase",
    expr: Union[str, "bases.BaseExpression"],
    handle_numeric_literals: bool = True,
) -> "bases.BaseExpression":
    """
    Helper function to convert an input value to an appropriate BaseExpression.

    Args:
        dialect: The SQL dialect instance
        expr: The expression to convert
        handle_numeric_literals: Whether to treat numeric values as literals

    Returns:
        A BaseExpression instance
    """
    if isinstance(expr, bases.BaseExpression):
        return expr
    elif isinstance(expr, (int, float)):
        # Numeric values: convert to Literal if handle_numeric_literals is True
        if handle_numeric_literals:
            return core.Literal(dialect, expr)
        return core.Column(dialect, str(expr))
    elif isinstance(expr, str):
        # Strings: always convert to Literal for JSON functions
        return core.Literal(dialect, expr)
    else:
        return core.Column(dialect, expr)


def json(
    dialect: "SQLiteDialect",
    value: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """
    Creates a JSON function call.

    Validates and converts a value to a JSON literal.

    Usage:
        - json(dialect, '{"a": 1}') -> JSON('{"a": 1}')
        - json(dialect, Column(dialect, "data"))

    Args:
        dialect: The SQLite dialect instance
        value: Value to convert to JSON

    Returns:
        A FunctionCall instance representing JSON

    Version: SQLite 3.38.0+
    """
    val_expr = _convert_to_expression(dialect, value)
    return core.FunctionCall(dialect, "JSON", val_expr)


def json_array(
    dialect: "SQLiteDialect",
    *values: Any,
) -> "core.FunctionCall":
    """
    Creates a JSON_ARRAY function call.

    Creates a JSON array from the arguments.

    Usage:
        - json_array(dialect) -> JSON_ARRAY()
        - json_array(dialect, 1, 2, 3) -> JSON_ARRAY(1, 2, 3)
        - json_array(dialect, "a", Column(dialect, "b")) -> JSON_ARRAY('a', "b")

    Args:
        dialect: The SQLite dialect instance
        *values: Values to include in the array

    Returns:
        A FunctionCall instance representing JSON_ARRAY

    Version: SQLite 3.38.0+
    """
    if not values:
        return core.FunctionCall(dialect, "JSON_ARRAY")
    args = [core.Literal(dialect, v) if not isinstance(v, bases.BaseExpression) else v
            for v in values]
    return core.FunctionCall(dialect, "JSON_ARRAY", *args)


def json_object(
    dialect: "SQLiteDialect",
    *key_value_pairs: Any,
) -> "core.FunctionCall":
    """
    Creates a JSON_OBJECT function call.

    Creates a JSON object from key-value pairs.

    Usage:
        - json_object(dialect) -> JSON_OBJECT()
        - json_object(dialect, "a", 1, "b", 2) -> JSON_OBJECT('a', 1, 'b', 2)

    Args:
        dialect: The SQLite dialect instance
        *key_value_pairs: Alternating keys and values

    Returns:
        A FunctionCall instance representing JSON_OBJECT

    Version: SQLite 3.38.0+
    """
    if not key_value_pairs:
        return core.FunctionCall(dialect, "JSON_OBJECT")
    args = [core.Literal(dialect, v) if not isinstance(v, bases.BaseExpression) else v
            for v in key_value_pairs]
    return core.FunctionCall(dialect, "JSON_OBJECT", *args)


def json_extract(
    dialect: "SQLiteDialect",
    json_doc: Union[str, "bases.BaseExpression"],
    path: str,
    *paths: str,
) -> "core.FunctionCall":
    """
    Creates a JSON_EXTRACT function call.

    Extracts values from a JSON document at the specified path(s).

    Usage:
        - json_extract(dialect, Column(dialect, "data"), "$.a")
        - json_extract(dialect, '{"a": 1}', "$.a")

    Args:
        dialect: The SQLite dialect instance
        json_doc: JSON document (column or literal)
        path: First JSON path expression
        *paths: Additional JSON path expressions

    Returns:
        A FunctionCall instance representing JSON_EXTRACT

    Version: SQLite 3.38.0+
    """
    doc_expr = _convert_to_expression(dialect, json_doc)
    path_expr = core.Literal(dialect, path)
    args = [doc_expr, path_expr]
    for p in paths:
        args.append(core.Literal(dialect, p))
    return core.FunctionCall(dialect, "JSON_EXTRACT", *args)


def json_type(
    dialect: "SQLiteDialect",
    json_val: Union[str, "bases.BaseExpression"],
    path: Optional[str] = None,
) -> "core.FunctionCall":
    """
    Creates a JSON_TYPE function call.

    Returns the type of a JSON value at the specified path.

    Usage:
        - json_type(dialect, Column(dialect, "data"), "$.a")

    Args:
        dialect: The SQLite dialect instance
        json_val: JSON value or column
        path: Optional path within the JSON

    Returns:
        A FunctionCall instance representing JSON_TYPE

    Version: SQLite 3.38.0+
    """
    val_expr = _convert_to_expression(dialect, json_val)
    if path is not None:
        path_expr = core.Literal(dialect, path)
        return core.FunctionCall(dialect, "JSON_TYPE", val_expr, path_expr)
    return core.FunctionCall(dialect, "JSON_TYPE", val_expr)


def json_valid(
    dialect: "SQLiteDialect",
    json_val: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """
    Creates a JSON_VALID function call.

    Returns 1 if the value is valid JSON, 0 otherwise.

    Usage:
        - json_valid(dialect, Column(dialect, "data"))

    Args:
        dialect: The SQLite dialect instance
        json_val: Value to validate

    Returns:
        A FunctionCall instance representing JSON_VALID

    Version: SQLite 3.38.0+
    """
    val_expr = _convert_to_expression(dialect, json_val)
    return core.FunctionCall(dialect, "JSON_VALID", val_expr)


def json_quote(
    dialect: "SQLiteDialect",
    value: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """
    Creates a JSON_QUOTE function call.

    Converts a value to a JSON literal (quoted string or other JSON literal).

    Usage:
        - json_quote(dialect, "hello") -> JSON_QUOTE('hello')

    Args:
        dialect: The SQLite dialect instance
        value: Value to quote as JSON

    Returns:
        A FunctionCall instance representing JSON_QUOTE

    Version: SQLite 3.38.0+
    """
    val_expr = _convert_to_expression(dialect, value)
    return core.FunctionCall(dialect, "JSON_QUOTE", val_expr)


def json_remove(
    dialect: "SQLiteDialect",
    json_doc: Union[str, "bases.BaseExpression"],
    path: str,
    *paths: str,
) -> "core.FunctionCall":
    """
    Creates a JSON_REMOVE function call.

    Removes values from a JSON document at the specified path(s).

    Usage:
        - json_remove(dialect, Column(dialect, "data"), "$.a")

    Args:
        dialect: The SQLite dialect instance
        json_doc: JSON document or column
        path: First path to remove
        *paths: Additional paths to remove

    Returns:
        A FunctionCall instance representing JSON_REMOVE

    Version: SQLite 3.38.0+
    """
    doc_expr = _convert_to_expression(dialect, json_doc)
    path_expr = core.Literal(dialect, path)
    args = [doc_expr, path_expr]
    for p in paths:
        args.append(core.Literal(dialect, p))
    return core.FunctionCall(dialect, "JSON_REMOVE", *args)


def json_set(
    dialect: "SQLiteDialect",
    json_doc: Union[str, "bases.BaseExpression"],
    path: str,
    value: Any,
    *path_values: Any,
) -> "core.FunctionCall":
    """
    Creates a JSON_SET function call.

    Inserts or replaces values in a JSON document.

    Usage:
        - json_set(dialect, Column(dialect, "data"), "$.a", "new_value")

    Args:
        dialect: The SQLite dialect instance
        json_doc: JSON document or column
        path: JSON path expression
        value: Value to set
        *path_values: Additional path-value pairs

    Returns:
        A FunctionCall instance representing JSON_SET

    Version: SQLite 3.38.0+
    """
    doc_expr = _convert_to_expression(dialect, json_doc)
    path_expr = core.Literal(dialect, path)
    val_expr = core.Literal(dialect, value) if not isinstance(value, bases.BaseExpression) else value
    args = [doc_expr, path_expr, val_expr]
    for i in range(0, len(path_values), 2):
        if i + 1 < len(path_values):
            args.append(core.Literal(dialect, path_values[i]))
            pv = path_values[i + 1]
            args.append(core.Literal(dialect, pv) if not isinstance(pv, bases.BaseExpression) else pv)
    return core.FunctionCall(dialect, "JSON_SET", *args)


def json_insert(
    dialect: "SQLiteDialect",
    json_doc: Union[str, "bases.BaseExpression"],
    path: str,
    value: Any,
    *path_values: Any,
) -> "core.FunctionCall":
    """
    Creates a JSON_INSERT function call.

    Inserts values into a JSON document without replacing existing values.

    Usage:
        - json_insert(dialect, Column(dialect, "data"), "$.b", "new_value")

    Args:
        dialect: The SQLite dialect instance
        json_doc: JSON document or column
        path: JSON path expression
        value: Value to insert
        *path_values: Additional path-value pairs

    Returns:
        A FunctionCall instance representing JSON_INSERT

    Version: SQLite 3.38.0+
    """
    doc_expr = _convert_to_expression(dialect, json_doc)
    path_expr = core.Literal(dialect, path)
    val_expr = core.Literal(dialect, value) if not isinstance(value, bases.BaseExpression) else value
    args = [doc_expr, path_expr, val_expr]
    for i in range(0, len(path_values), 2):
        if i + 1 < len(path_values):
            args.append(core.Literal(dialect, path_values[i]))
            pv = path_values[i + 1]
            args.append(core.Literal(dialect, pv) if not isinstance(pv, bases.BaseExpression) else pv)
    return core.FunctionCall(dialect, "JSON_INSERT", *args)


def json_replace(
    dialect: "SQLiteDialect",
    json_doc: Union[str, "bases.BaseExpression"],
    path: str,
    value: Any,
    *path_values: Any,
) -> "core.FunctionCall":
    """
    Creates a JSON_REPLACE function call.

    Replaces values in a JSON document (only existing paths are replaced).

    Usage:
        - json_replace(dialect, Column(dialect, "data"), "$.a", "new_value")

    Args:
        dialect: The SQLite dialect instance
        json_doc: JSON document or column
        path: JSON path expression
        value: Value to replace
        *path_values: Additional path-value pairs

    Returns:
        A FunctionCall instance representing JSON_REPLACE

    Version: SQLite 3.38.0+
    """
    doc_expr = _convert_to_expression(dialect, json_doc)
    path_expr = core.Literal(dialect, path)
    val_expr = core.Literal(dialect, value) if not isinstance(value, bases.BaseExpression) else value
    args = [doc_expr, path_expr, val_expr]
    for i in range(0, len(path_values), 2):
        if i + 1 < len(path_values):
            args.append(core.Literal(dialect, path_values[i]))
            pv = path_values[i + 1]
            args.append(core.Literal(dialect, pv) if not isinstance(pv, bases.BaseExpression) else pv)
    return core.FunctionCall(dialect, "JSON_REPLACE", *args)


def json_patch(
    dialect: "SQLiteDialect",
    json_doc: Union[str, "bases.BaseExpression"],
    patch: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """
    Creates a JSON_PATCH function call.

    Applies a JSON patch to a JSON document (RFC 7396).

    Usage:
        - json_patch(dialect, Column(dialect, "data"), Column(dialect, "patch"))

    Args:
        dialect: The SQLite dialect instance
        json_doc: Target JSON document or column
        patch: JSON patch to apply

    Returns:
        A FunctionCall instance representing JSON_PATCH

    Version: SQLite 3.38.0+
    """
    doc_expr = _convert_to_expression(dialect, json_doc)
    patch_expr = _convert_to_expression(dialect, patch)
    return core.FunctionCall(dialect, "JSON_PATCH", doc_expr, patch_expr)


def json_array_length(
    dialect: "SQLiteDialect",
    json_val: Union[str, "bases.BaseExpression"],
    path: Optional[str] = None,
) -> "core.FunctionCall":
    """
    Creates a JSON_ARRAY_LENGTH function call.

    Returns the number of elements in a JSON array.

    Usage:
        - json_array_length(dialect, Column(dialect, "data"))
        - json_array_length(dialect, Column(dialect, "data"), "$.items")

    Args:
        dialect: The SQLite dialect instance
        json_val: JSON value or column
        path: Optional path to array within JSON

    Returns:
        A FunctionCall instance representing JSON_ARRAY_LENGTH

    Version: SQLite 3.38.0+
    """
    val_expr = _convert_to_expression(dialect, json_val)
    if path is not None:
        path_expr = core.Literal(dialect, path)
        return core.FunctionCall(dialect, "JSON_ARRAY_LENGTH", val_expr, path_expr)
    return core.FunctionCall(dialect, "JSON_ARRAY_LENGTH", val_expr)


def json_array_unpack(
    dialect: "SQLiteDialect",
    json_val: Union[str, "bases.BaseExpression"],
    path: Optional[str] = None,
) -> "core.FunctionCall":
    """
    Creates a JSON_UNPACK function call (alias for JSON_ARRAY_LENGTH).

    Note: This function is an alias for extracting array elements.

    Usage:
        - json_array_unpack(dialect, Column(dialect, "data"))

    Args:
        dialect: The SQLite dialect instance
        json_val: JSON value or column
        path: Optional path to array within JSON

    Returns:
        A FunctionCall instance representing JSON_UNPACK

    Version: SQLite 3.38.0+
    """
    # SQLite doesn't have JSON_UNPACK, this would typically be used with json_each
    val_expr = _convert_to_expression(dialect, json_val)
    if path is not None:
        path_expr = core.Literal(dialect, path)
        return core.FunctionCall(dialect, "JSON_ARRAY_LENGTH", val_expr, path_expr)
    return core.FunctionCall(dialect, "JSON_ARRAY_LENGTH", val_expr)


def json_object_pack(
    dialect: "SQLiteDialect",
    key: str,
    value: Any,
) -> "core.FunctionCall":
    """
    Creates a JSON_OBJECT function call with a single key-value pair.

    This is a convenience function for creating single-entry JSON objects.

    Usage:
        - json_object_pack(dialect, "key", "value")

    Args:
        dialect: The SQLite dialect instance
        key: Object key
        value: Object value

    Returns:
        A FunctionCall instance representing JSON_OBJECT

    Version: SQLite 3.38.0+
    """
    key_expr = core.Literal(dialect, key)
    val_expr = core.Literal(dialect, value) if not isinstance(value, bases.BaseExpression) else value
    return core.FunctionCall(dialect, "JSON_OBJECT", key_expr, val_expr)


def json_object_retrieve(
    dialect: "SQLiteDialect",
    json_val: Union[str, "bases.BaseExpression"],
    path: str,
) -> "core.FunctionCall":
    """
    Creates a JSON_EXTRACT function call for retrieving a single value.

    This is an alias for json_extract with a single path.

    Usage:
        - json_object_retrieve(dialect, Column(dialect, "data"), "$.name")

    Args:
        dialect: The SQLite dialect instance
        json_val: JSON value or column
        path: JSON path to retrieve

    Returns:
        A FunctionCall instance representing JSON_EXTRACT

    Version: SQLite 3.38.0+
    """
    val_expr = _convert_to_expression(dialect, json_val)
    path_expr = core.Literal(dialect, path)
    return core.FunctionCall(dialect, "JSON_EXTRACT", val_expr, path_expr)


def json_object_length(
    dialect: "SQLiteDialect",
    json_val: Union[str, "bases.BaseExpression"],
    path: Optional[str] = None,
) -> "core.FunctionCall":
    """
    Creates a JSON_OBJECT_LENGTH function call.

    Returns the number of key-value pairs in a JSON object.

    Usage:
        - json_object_length(dialect, Column(dialect, "data"))

    Args:
        dialect: The SQLite dialect instance
        json_val: JSON value or column
        path: Optional path within JSON

    Returns:
        A FunctionCall instance representing JSON_OBJECT_LENGTH

    Version: SQLite 3.38.0+
    """
    val_expr = _convert_to_expression(dialect, json_val)
    if path is not None:
        path_expr = core.Literal(dialect, path)
        return core.FunctionCall(dialect, "JSON_OBJECT_LENGTH", val_expr, path_expr)
    return core.FunctionCall(dialect, "JSON_OBJECT_LENGTH", val_expr)


def json_object_keys(
    dialect: "SQLiteDialect",
    json_val: Union[str, "bases.BaseExpression"],
    path: Optional[str] = None,
) -> "core.FunctionCall":
    """
    Creates a JSON_OBJECT_KEYS function call.

    Returns the keys of a JSON object as a JSON array.

    Usage:
        - json_object_keys(dialect, Column(dialect, "data"))

    Args:
        dialect: The SQLite dialect instance
        json_val: JSON value or column
        path: Optional path within JSON

    Returns:
        A FunctionCall instance representing JSON_OBJECT_KEYS

    Version: SQLite 3.38.0+
    """
    val_expr = _convert_to_expression(dialect, json_val)
    if path is not None:
        path_expr = core.Literal(dialect, path)
        return core.FunctionCall(dialect, "JSON_OBJECT_KEYS", val_expr, path_expr)
    return core.FunctionCall(dialect, "JSON_OBJECT_KEYS", val_expr)


def json_tree(
    dialect: "SQLiteDialect",
    json_val: Union[str, "bases.BaseExpression"],
    path: Optional[str] = None,
) -> "core.FunctionCall":
    """
    Creates a JSON_TREE function call.

    Returns a virtual table with one row for each element in a JSON array or object.

    Usage:
        - json_tree(dialect, Column(dialect, "data"))
        - json_tree(dialect, Column(dialect, "data"), "$.items")

    Args:
        dialect: The SQLite dialect instance
        json_val: JSON value or column
        path: Optional path within JSON

    Returns:
        A FunctionCall instance representing JSON_TREE

    Version: SQLite 3.38.0+
    """
    val_expr = _convert_to_expression(dialect, json_val)
    if path is not None:
        path_expr = core.Literal(dialect, path)
        return core.FunctionCall(dialect, "JSON_TREE", val_expr, path_expr)
    return core.FunctionCall(dialect, "JSON_TREE", val_expr)


def json_each(
    dialect: "SQLiteDialect",
    json_val: Union[str, "bases.BaseExpression"],
    path: Optional[str] = None,
) -> "core.FunctionCall":
    """
    Creates a JSON_EACH function call.

    Returns a virtual table with one row for each element in a JSON array or object.
    Unlike JSON_TREE, JSON_EACH only iterates over the top-level array or object.

    Usage:
        - json_each(dialect, Column(dialect, "data"))
        - json_each(dialect, Column(dialect, "data"), "$.items")

    Args:
        dialect: The SQLite dialect instance
        json_val: JSON value or column
        path: Optional path within JSON

    Returns:
        A FunctionCall instance representing JSON_EACH

    Version: SQLite 3.38.0+
    """
    val_expr = _convert_to_expression(dialect, json_val)
    if path is not None:
        path_expr = core.Literal(dialect, path)
        return core.FunctionCall(dialect, "JSON_EACH", val_expr, path_expr)
    return core.FunctionCall(dialect, "JSON_EACH", val_expr)


__all__ = [
    "json",
    "json_array",
    "json_object",
    "json_extract",
    "json_type",
    "json_valid",
    "json_quote",
    "json_remove",
    "json_set",
    "json_insert",
    "json_replace",
    "json_patch",
    "json_array_length",
    "json_array_unpack",
    "json_object_pack",
    "json_object_retrieve",
    "json_object_length",
    "json_object_keys",
    "json_tree",
    "json_each",
]