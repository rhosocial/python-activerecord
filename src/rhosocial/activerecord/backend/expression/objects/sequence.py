# src/rhosocial/activerecord/backend/expression/objects/sequence.py
"""
Sequences -- value generators.

A sequence is persistent and named, but it is not a relation. It is reached
through a function call (``nextval('s')`` in PostgreSQL), never by naming it
in a ``FROM`` clause. The engine's own catalogue often files sequences
alongside relations, but the query language does not: keeping this a separate
kind stops a sequence from being used where a table is required.
"""

from .base import SchemaObject

__all__ = ["Sequence"]


class Sequence(SchemaObject):
    """A sequence."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this sequence."""
        return "format_sequence_object"