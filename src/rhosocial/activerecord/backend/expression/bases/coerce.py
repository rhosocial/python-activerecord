# src/rhosocial/activerecord/backend/expression/coerce.py
"""Automatic wrapping of raw values at expression API boundaries.

A caller should not have to write ``Parameter(dialect, value)`` to keep a value
out of the SQL text. Constructors and factories accept a raw Python value and
coerce it here: a value becomes the internal :class:`~.core.Parameter` node,
which binds by default. SQL therefore always carries a placeholder and the
value travels in the parameter sequence.

Coercion is applied only at **value positions** (comparison operands, IN lists,
function arguments, INSERT/UPDATE values, DDL defaults). A position that expects
a name -- a table, a column, an ORDER BY item -- must not use it: the string
``"id"`` there means an identifier, not the text ``'id'``.
"""

from typing import Any

from ..bases.bases import BaseExpression


def value_expression(dialect: "Any", value: Any) -> BaseExpression:
    """*value* as an expression: a node is returned as-is, anything else binds."""
    from ..value_types.parameter import Parameter

    if isinstance(value, BaseExpression):
        return value
    return Parameter(dialect, value)


def value_sequence(dialect: "Any", values: Any) -> BaseExpression:
    """A value list for ``IN``: one bind parameter per member.

    A collection becomes a single :class:`~.core.Parameter` holding a tuple,
    which ``format_in_predicate`` renders as ``(?, ?, ...)``. An existing
    expression (a subquery, already-wrapped values) is returned untouched.
    """
    from ..value_types.parameter import Parameter

    if isinstance(values, BaseExpression):
        return values
    if isinstance(values, (list, tuple, set)):
        return Parameter(dialect, tuple(values))
    return Parameter(dialect, values)
