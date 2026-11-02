# src/rhosocial/activerecord/backend/expression/collect_columns.py
"""Which columns a condition mentions, walked out of an expression tree.

The question a *policy* asks, not a rendering one: "does this WHERE constrain
the column I care about?" -- whether to warn a reader that a lookup is not a
row address, to refuse a write, or to report anything else about scope. Nothing
here formats SQL or touches a database.

Walked rather than enumerated per predicate class, on purpose. The predicate
families each carry their operands under a different attribute
(``left``/``right``, ``operand``/``low``/``high``, ``operands``, ``expr``,
``column``), and a method that named every one would have to be revisited each
time a family is added; a walk over the tree's own attributes follows whatever
is there and reports what it finds, so a new family is answered without being
wired in. The cost is that the walk cannot say *how* a column is constrained
-- only whether it appears at all, which is what the question above needs.

Where the walk gives up it reports less, never more: an operand shape it does
not recognise contributes no columns, so a query that constrains a column
looks like one that does not only if the constraint hides inside a construct
this module declines to interpret. That direction is deliberate -- an
unrecognised shape should cost a missing warning, not a wrong one.
"""

from __future__ import annotations

from typing import Any, Iterator, Set

from .bases import BaseExpression
from .column_types import ColumnBase


def iter_columns(node: Any) -> Iterator[ColumnBase]:
    """Yield every column reference in an expression tree, depth first.

    Both a :class:`ColumnBase` (a bare or typed column) and the predicates that
    hold them are expressions, and an expression's operands live in instance
    attributes, so one rule covers both: a column is a leaf, anything else is
    walked.

    Sequences are walked too, and not as a special case: a logical predicate
    holds its operands as a tuple, and a walk that stopped at a tuple stopped
    exactly where ``A AND B`` diverges from ``A`` -- the first shape answered,
    the second silently answered nothing. A literal's value is a sequence too,
    so this is not "containers are trees", it is that a node does not get to
    decide how its children are stored.

    Args:
        node: Any expression, predicate, container, or plain value.
    """
    if isinstance(node, ColumnBase):
        yield node
        return
    if isinstance(node, (list, tuple, set, frozenset)):
        for item in node:
            yield from iter_columns(item)
        return
    if not isinstance(node, BaseExpression):
        return
    for value in getattr(node, "__dict__", {}).values():
        yield from iter_columns(value)


def referenced_columns(node: Any) -> Set[str]:
    """Column names ``node``'s tree mentions, as the renderer would spell them.

    Names, not column objects, because the caller is asking about *which
    columns* and a model's declared key is a set of names. Two columns of the
    same name in different tables are the same answer: a lookup that
    constrains either of them addresses the same data column.
    """
    return {column.name for column in iter_columns(node) if getattr(column, "name", None)}


__all__ = ["iter_columns", "referenced_columns"]
