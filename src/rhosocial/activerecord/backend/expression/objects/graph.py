# src/rhosocial/activerecord/backend/expression/objects/graph.py
"""Property graphs -- the named containers SQL/PGQ vertices and edges live in.

A property graph is a catalogue entry like a table or a sequence: it has a name,
it can be created and dropped, and it is qualified by a catalog and a schema on
the engines that have either. It is not a relation -- a graph is queried *through*
``GRAPH_TABLE``, which produces rows, so the row source is a separate expression
and this class is only what that source names.

Note that the tables declared inside a graph (:class:`NodeTable` and
:class:`EdgeTable`) are ordinary tables with a graph role. The role belongs to the
statement that declares it, not to the table's name, so those two inherit
:class:`~.relation.Table` rather than this.
"""

from .base import SchemaObject

__all__ = ["PropertyGraph"]


class PropertyGraph(SchemaObject):
    """A property graph."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this property graph."""
        return "format_property_graph_object"