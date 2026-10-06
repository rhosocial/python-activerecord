# src/rhosocial/activerecord/backend/expression/objects/index.py
"""
Indexes -- access paths over a relation.

An index is a persistent, named object, so it is a :class:`SchemaObject`.
It is **not** a relation: ``FROM my_index`` is not legal, and a table
expression must never stand in for an index name. That distinction is the
whole reason the object kinds are separate types.
"""

from .base import SchemaObject

__all__ = ["Index"]


class Index(SchemaObject):
    """An index.

    The relation an index is built over is *not* part of the index's
    identity -- ``CREATE INDEX ix ON users`` names two objects in two
    namespaces, and each carries its own. That is why this class adds no
    slot for the target table.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this index."""
        return "format_index_object"