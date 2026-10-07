# src/rhosocial/activerecord/backend/expression/objects/synonym.py
"""
Synonyms -- indirection between a name and another object.

A synonym is the lightest persistent object there is: it has a name and a
target, and nothing else. What makes it worth its own kind is that the
target may be *any* object -- table, view, sequence, function, type, even
another synonym. A synonym is not a table under another name, and treating
it as one is how name resolution ends up confused.
"""

from .base import SchemaObject

__all__ = ["Synonym"]


class Synonym(SchemaObject):
    """A synonym: an alternative name resolving to another object.

    The target object is deliberately absent from the identity slots. It is
    a property of the definition, and the same synonym name may be re-pointed
    without the object ceasing to exist.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this synonym."""
        return "format_synonym_object"