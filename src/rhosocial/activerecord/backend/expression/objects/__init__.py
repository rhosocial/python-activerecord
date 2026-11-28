# src/rhosocial/activerecord/backend/expression/objects/__init__.py
"""Named database objects and their kinds.

Every object the engine persists is a :class:`SchemaObject`: a name plus up
to two fixed namespace slots. The subclasses name the kind, which lets the
type system reject statements wired to the wrong thing -- creating an index
from a :class:`Table` should not compile, and rendering an index name with a
table expression should not be reachable.

The tree separates the kinds that share an identity from the kinds that
share a role:

* :class:`RelationObject` and its branches -- things a query reads *from*.
* :class:`Index`, :class:`Sequence`, :class:`TypeObject`, :class:`Domain`,
  :class:`RoutineObject`, :class:`Trigger`, :class:`Synonym` -- things DDL
  names but a query never selects from.
* :class:`Schema` and :class:`Database` -- the namespaces the rest sit in.
* :class:`PropertyGraph` -- the named container SQL/PGQ vertices live in.

Query-side row sources live in :mod:`..sources` and are deliberately **not**
part of this tree: ``FROM json_table(...)`` produces rows but has no
catalog identity, so making it a schema object would be a lie."""

__all__ = [
    'SchemaObject',
    'RelationObject',
    'Table',
    'NodeTable',
    'EdgeTable',
    'View',
    'MaterializedView',
    'ForeignTable',
    'Index',
    'Sequence',
    'TypeObject',
    'Type',
    'Domain',
    'RoutineObject',
    'Function',
    'Procedure',
    'Trigger',
    'Synonym',
    'Schema',
    'Database',
    'PropertyGraph',
]

import importlib

_MODULES = ('base', 'graph', 'index', 'namespace', 'qualified_identifier', 'relation', 'routine', 'sequence', 'synonym', 'trigger', 'type_')


def __getattr__(name):
    """Resolve a public name from this namespace lazily (no import cycles)."""
    for module_name in _MODULES:
        module = importlib.import_module(f'.{module_name}', __name__)
        if name in vars(module):
            value = vars(module)[name]
            globals()[name] = value  # cache so vars()/inspect see the name
            return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
