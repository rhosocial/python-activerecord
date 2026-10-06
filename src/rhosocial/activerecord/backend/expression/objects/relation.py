# src/rhosocial/activerecord/backend/expression/objects/relation.py
"""
Relations: the objects that produce rows.

A relation is what a query can read *from*. Table, view, materialized view
and foreign table all qualify, which is why they share this branch of the
object tree. None of them inherits from another: a view is not a table that
happens to be computed, and code that accepts a table must not silently
accept a view. What they share is the *kind* of thing they are, not a
parent-child relationship.

Graph tables are the one place inheritance is genuine. SQL Server spells
them ``CREATE TABLE ... AS NODE`` / ``AS EDGE``: they are ordinary tables
that carry an additional graph role. Modelling that as ``Table`` plus a
subclass keeps them usable everywhere a table is, which is exactly what the
engine does.
"""

from .base import SchemaObject

__all__ = [
    "RelationObject",
    "Table",
    "NodeTable",
    "EdgeTable",
    "View",
    "MaterializedView",
    "ForeignTable",
]


class RelationObject(SchemaObject):
    """Base of every object a query can select from.

    Adds no slots: a relation's identity is still catalog, schema and name.
    The class exists so that statements needing "something readable" can ask
    for a relation without accepting arbitrary objects. It declares no
    ``format_method`` either -- being readable does not say how a kind of
    relation is spelled, so each concrete relation declares its own.
    """


class Table(RelationObject):
    """A base table."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this table."""
        return "format_table_object"


class NodeTable(Table):
    """A graph vertex table -- a table carrying the node role.

    Inherits ``Table``'s formatter: a node table is created and dropped
    exactly as a table is, and the graph role belongs to the statement that
    declares it, not to the name.
    """


class EdgeTable(Table):
    """A graph edge table -- a table carrying the edge role.

    Inherits ``Table``'s formatter, for the same reason as :class:`NodeTable`.
    """


class View(RelationObject):
    """A view: a relation defined by a query, recomputed on read."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this view."""
        return "format_view_object"


class MaterializedView(RelationObject):
    """A materialized view: a relation defined by a query, stored."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this materialized view."""
        return "format_materialized_view_object"


class ForeignTable(RelationObject):
    """A foreign table: a relation whose rows live in another engine."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this foreign table."""
        return "format_foreign_table_object"