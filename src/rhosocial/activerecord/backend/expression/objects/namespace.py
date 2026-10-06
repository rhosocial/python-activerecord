"""Namespaces -- schemas and the databases that hold them.

A schema and a database are catalogue entries like any other, but they sit
*above* the relations the object model was built around: a schema has no inner
namespace, because it is the inner namespace; a database has no namespace at all,
because it is the thing namespaces live in. So neither carries a ``schema_name``,
and the renderer for each is a dialect's own -- a qualified relation and a
qualified schema are spelled differently even on the same engine.
"""

from .base import SchemaObject

__all__ = ["Database", "Schema"]


class Schema(SchemaObject):
    """A schema.

    The inner namespace of a catalogue. A qualified relation reads
    ``schema.name``, so this class's own name occupies that slot and there is no
    second level to give it -- ``CREATE SCHEMA app`` names one thing.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this schema."""
        return "format_schema_object"


class Database(SchemaObject):
    """A database.

    The outermost container: the thing a connection selects and a catalog sits
    in. Even a catalog is not spelled here -- it is the connection's business,
    not the name of the database.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this database."""
        return "format_database_object"
