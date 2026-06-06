"""
Version-dependent expression — demonstrates ``json_array_insert`` (SQLite 3.53.0+).

Compare behavior across dialect versions:

    $ python -m rhosocial.activerecord.backend.impl.sqlite named-expression \\
        rhosocial.activerecord.backend.impl.sqlite.examples.named_expressions.order_version_compare.demo_json_array_insert \\
        --list --dialect-version 3.53.0

    $ python -m rhosocial.activerecord.backend.impl.sqlite named-expression \\
        rhosocial.activerecord.backend.impl.sqlite.examples.named_expressions.order_version_compare.demo_json_array_insert \\
        --list --dialect-version 3.35.0

The ``json_array_insert()`` function was introduced in SQLite 3.53.0:
https://sqlite.org/json1.html#jarrayins

Calling ``to_sql()`` on a pre-3.53.0 dialect causes the dialect's
``format_function_call()`` to raise ``UnsupportedFeatureError``.
"""  # noqa: E501

from rhosocial.activerecord.backend.expression import (
    QueryExpression,
    FunctionCall,
    Column,
    Literal,
    TableExpression,
)


def demo_json_array_insert(dialect, position: int = 0, value: str = "new_item"):
    """Insert a value into a JSON array using ``json_array_insert()`` (SQLite 3.53.0+).

    Raises ``RuntimeError`` when the dialect version is older than 3.53.0,
    demonstrating how a version-gated function fails on an unsupported
    dialect.  The check uses ``dialect.version`` to compare against the
    required version tuple ``(3, 53, 0)``.

    Reference: https://sqlite.org/json1.html#jarrayins

    Args:
        dialect: SQL dialect instance.
        position: Zero-based index at which to insert.
        value: Value to insert into the array.

    Returns:
        QueryExpression with ``json_array_insert``.

    Raises:
        RuntimeError: If dialect version < 3.53.0.
    """
    if dialect.version < (3, 53, 0):
        ver = f"{dialect.version[0]}.{dialect.version[1]}.{dialect.version[2]}"
        raise RuntimeError(f"json_array_insert() requires SQLite 3.53.0+, current dialect version: {ver}")

    return QueryExpression(
        dialect,
        select=[
            FunctionCall(
                dialect,
                "JSON_ARRAY_INSERT",
                Column(dialect, "tags"),
                Literal(dialect, f"$[{position}]"),
                Literal(dialect, value),
            ).as_("modified_tags"),
        ],
        from_=TableExpression(dialect, "users"),
    )
