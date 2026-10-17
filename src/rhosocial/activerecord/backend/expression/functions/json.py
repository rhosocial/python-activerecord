# src/rhosocial/activerecord/backend/expression/functions/json.py
"""JSON function factories."""

from typing import Optional, TYPE_CHECKING

from ..advanced_functions import DeclaredValueType
from ..bases import BaseExpression
from .aggregate import AggregateFunction
from ..core import Column, Literal
from ..advanced_functions import JSONDocumentValue, JSONTextValue

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase

from ..surfaces import JSONSurface

class JSONBuildObjectFunction(
    DeclaredValueType,
    JSONSurface,
):
    """``JSON_BUILD_OBJECT(key, value, ...)`` -- a document built from pairs.

    :attr:`pairs` is a flat list of alternating key and value, which is the
    order the function reads them in, so it is stored flat rather than zipped:
    a backend whose spelling reorders them has to see the order the caller gave.
    """

    kind_name = "json_build_object_function"

    def __init__(self, dialect: "SQLDialectBase", *pairs):

        # BaseExpression directly, not super(): the value class is a *wrapper*
        # whose __init__ takes the call it delegates to, and this node has no
        # call -- it renders itself. DeclaredValueType keeps that from mattering.
        BaseExpression.__init__(self, dialect)
        self.pairs = [p if isinstance(p, BaseExpression) else Literal(dialect, p) for p in pairs]

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_json_build_object_function"


class JSONArrayElementsFunction(
    DeclaredValueType,
    JSONSurface,
):
    """``JSON_ARRAY_ELEMENTS(json)`` -- the array's elements, one per row.

    A table function rather than a scalar: it multiplies rows rather than
    combining them, which is why a FROM source is where it belongs.
    """

    kind_name = "json_array_elements_function"

    def __init__(self, dialect: "SQLDialectBase", target):
        from ..core import Literal

        # BaseExpression directly, not super(): the value class is a *wrapper*
        # whose __init__ takes the call it delegates to, and this node has no
        # call -- it renders itself. DeclaredValueType keeps that from mattering.
        BaseExpression.__init__(self, dialect)
        # A JSON document is not text and not a number, so a bare host value
        # becomes the untyped literal until the JSON value type lands.
        self.target = target if isinstance(target, BaseExpression) else Literal(dialect, target)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_json_array_elements_function"


class JSONObjectAggregateFunction(
    AggregateFunction,
    DeclaredValueType,
    JSONSurface,
):
    """``JSON_OBJECTAGG(key, value)`` -- rows gathered into one document.

    Two operands where :class:`~...expression.functions.aggregate.AggregateFunction`
    declares one, so the **key** is the aggregate's operand -- it is what
    identifies the row -- and the value rides alongside as
    :attr:`entry_value`. ``FILTER`` and the window clause therefore apply to the
    key, which is the only reading that has one.
    """

    kind_name = "json_objectagg_function"

    def __init__(self, dialect: "SQLDialectBase", operand, entry_value):
        from ..core import Literal

        # ``operand`` and not ``key``: that is the name AggregateFunction
        # declares, and the deserializer reads the declared names, so a
        # different spelling here would reconstruct a node missing its key.
        #
        # Both operands are arbitrary JSON, so neither is text or a number and a
        # bare host value becomes the untyped literal.
        operand = operand if isinstance(operand, BaseExpression) else Literal(dialect, operand)
        entry_value = (
            entry_value if isinstance(entry_value, BaseExpression) else Literal(dialect, entry_value)
        )
        AggregateFunction.__init__(self, dialect, operand)
        self.entry_value = entry_value

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_json_objectagg_function"


class JSONArrayAggregateFunction(
    AggregateFunction,
    DeclaredValueType,
    JSONSurface,
):
    """``JSON_ARRAYAGG(value)`` -- rows gathered into one array.

    An array whatever the gathered values were, so the node says so rather than
    reading a type off the operand.
    """

    kind_name = "json_arrayagg_function"

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_json_arrayagg_function"


def json_extract(dialect: "SQLDialectBase", column: "BaseExpression", path: str) -> "JSONDocumentValue":
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
        A JSONDocumentValue instance representing the JSON extract operation
    """
    target_column = column if isinstance(column, BaseExpression) else Column(dialect, column)
    return JSONDocumentValue(dialect, target_column, path, operation="->")


def json_extract_text(dialect: "SQLDialectBase", column: "BaseExpression", path: str) -> "JSONTextValue":
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
        A JSONTextValue instance representing the JSON extract text operation
    """
    target_column = column if isinstance(column, BaseExpression) else Column(dialect, column)
    # `->>` yields text, so it arrives as JSONTextValue and carries the
    # string operations. It used to be built as a JSONDocumentValue and described
    # as a string by a tag, which meant the JSON accessors it was meant to end
    # the chain with stayed reachable -- the node class served both arrow
    # directions and could not drop them per instance.
    return JSONTextValue(dialect, target_column, path, operation="->>")


def json_build_object(dialect: "SQLDialectBase", *key_value_pairs: "BaseExpression") -> "BaseExpression":
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
        A JSONValue wrapping JSON_BUILD_OBJECT
    """
    # Expect alternating sequence of key-value expressions
    return JSONBuildObjectFunction(dialect, *key_value_pairs)


def json_array_elements(dialect: "SQLDialectBase", expr: "BaseExpression") -> "BaseExpression":
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
        A JSONValue wrapping JSON_ARRAY_ELEMENTS
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    return JSONArrayElementsFunction(dialect, target_expr)


def json_objectagg(
    dialect: "SQLDialectBase",
    key_expr: "BaseExpression",
    value_expr: "BaseExpression",
) -> "JSONObjectAggregateFunction":
    """Creates a JSON_OBJECTAGG aggregate function call."""
    key_target = key_expr if isinstance(key_expr, BaseExpression) else Column(dialect, key_expr)
    value_target = value_expr if isinstance(value_expr, BaseExpression) else Column(dialect, value_expr)
    return JSONObjectAggregateFunction(dialect, key_target, value_target)


def json_arrayagg(
    dialect: "SQLDialectBase",
    expr: "BaseExpression",
    is_distinct: bool = False,
    alias: Optional[str] = None,
) -> "JSONArrayAggregateFunction":
    """Creates a JSON_ARRAYAGG aggregate function call."""
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    node = JSONArrayAggregateFunction(dialect, target_expr, distinct=is_distinct)
    return node.as_(alias) if alias else node