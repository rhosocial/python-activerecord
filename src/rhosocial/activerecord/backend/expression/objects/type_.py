# src/rhosocial/activerecord/backend/expression/objects/type_.py
"""
Types and domains -- the ``data_type`` slot.

These names appear where a type is expected, not where a table is expected::

    CREATE TABLE account (balance positive_money);

``positive_money`` is a domain: a type built from another type plus
constraints. It is therefore *not* modelled as a subclass of
:class:`Type`. A domain is a peer that happens to have a base type and extra
checks, and inheriting would drag a whole type definition onto every
subclass of ``Type`` that does not want one.

Both share a namespace with each other and, in most engines, with the
composite type every table implies -- which is exactly the kind of fact a
catalogue enforces and this layer does not try to.
"""

from .base import SchemaObject

__all__ = ["TypeObject", "Type", "Domain"]


class TypeObject(SchemaObject):
    """Base of the objects that occupy a ``data_type`` position.

    Declares no ``format_method``: being usable as a type does not say how a
    type is spelled, so each of the two kinds below declares its own.
    """


class Type(TypeObject):
    """A user-defined type."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this type."""
        return "format_type_object"


class Domain(TypeObject):
    """A domain: a type derived from another type plus constraints.

    A peer of :class:`Type` rather than a subclass: it is a type built from
    another type plus constraints, and inheriting would drag a type definition
    onto every subclass of ``Type`` that does not want one. The base type and the
    constraints belong to the statement that creates the domain, not to the
    domain's identity, so this class adds no slots.
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this domain."""
        return "format_domain_object"