"""Rendering of named database objects.

A named object -- table, view, index, sequence, trigger, routine, type, domain,
synonym -- has one job in SQL: state which object it names. These protocols cover
exactly that, one protocol per kind, and nothing else.

They deliberately do not cover the statements that create or drop the object.
``CREATE TABLE`` is a different protocol, because an engine may support naming a
table without supporting ``CREATE TABLE ... LIKE``, and an engine that supports
neither is not thereby unable to say ``"users"``.

The namespace levels every one of them shares are declared once on
:class:`NamespaceSupport`.
"""

from .namespace import NamespaceSupport
from .relation import TableObjectSupport, ViewObjectSupport, MaterializedViewObjectSupport, ForeignTableObjectSupport
from .index import IndexObjectSupport
from .sequence import SequenceObjectSupport
from .trigger import TriggerObjectSupport
from .routine import RoutineObjectSupport
from .type_ import TypeObjectSupport
from .synonym import SynonymObjectSupport

__all__ = [
    "ForeignTableObjectSupport",
    "IndexObjectSupport",
    "MaterializedViewObjectSupport",
    "NamespaceSupport",
    "RoutineObjectSupport",
    "SequenceObjectSupport",
    "SynonymObjectSupport",
    "TableObjectSupport",
    "TriggerObjectSupport",
    "TypeObjectSupport",
    "ViewObjectSupport",
]
