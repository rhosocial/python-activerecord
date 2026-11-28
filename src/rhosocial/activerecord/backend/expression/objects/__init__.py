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

import importlib

# Public name -> defining module. Private names here stay reachable
# through this package but are not part of __all__.
_EXPORTS = {
    'BaseExpression': 'rhosocial.activerecord.backend.expression.objects.base',
    'Database': 'rhosocial.activerecord.backend.expression.objects.namespace',
    'Domain': 'rhosocial.activerecord.backend.expression.objects.type_',
    'EdgeTable': 'rhosocial.activerecord.backend.expression.objects.relation',
    'ForeignTable': 'rhosocial.activerecord.backend.expression.objects.relation',
    'Function': 'rhosocial.activerecord.backend.expression.objects.routine',
    'Index': 'rhosocial.activerecord.backend.expression.objects.index',
    'MaterializedView': 'rhosocial.activerecord.backend.expression.objects.relation',
    'NodeTable': 'rhosocial.activerecord.backend.expression.objects.relation',
    'Optional': 'rhosocial.activerecord.backend.expression.objects.base',
    'Procedure': 'rhosocial.activerecord.backend.expression.objects.routine',
    'PropertyGraph': 'rhosocial.activerecord.backend.expression.objects.graph',
    'QualifiedIdentifier': 'rhosocial.activerecord.backend.expression.objects.qualified_identifier',
    'RelationObject': 'rhosocial.activerecord.backend.expression.objects.relation',
    'RoutineObject': 'rhosocial.activerecord.backend.expression.objects.routine',
    'Schema': 'rhosocial.activerecord.backend.expression.objects.namespace',
    'SchemaObject': 'rhosocial.activerecord.backend.expression.objects.base',
    'Sequence': 'rhosocial.activerecord.backend.expression.objects.sequence',
    'Synonym': 'rhosocial.activerecord.backend.expression.objects.synonym',
    'TYPE_CHECKING': 'rhosocial.activerecord.backend.expression.objects.base',
    'Table': 'rhosocial.activerecord.backend.expression.objects.relation',
    'Trigger': 'rhosocial.activerecord.backend.expression.objects.trigger',
    'Type': 'rhosocial.activerecord.backend.expression.objects.type_',
    'TypeObject': 'rhosocial.activerecord.backend.expression.objects.type_',
    'View': 'rhosocial.activerecord.backend.expression.objects.relation',
}

__all__ = [
    'Database',
    'Domain',
    'EdgeTable',
    'ForeignTable',
    'Function',
    'Index',
    'MaterializedView',
    'NodeTable',
    'Procedure',
    'PropertyGraph',
    'RelationObject',
    'RoutineObject',
    'Schema',
    'SchemaObject',
    'Sequence',
    'Synonym',
    'Table',
    'Trigger',
    'Type',
    'TypeObject',
    'View',
]


def __getattr__(name):
    """Resolve a public name from this namespace lazily (no import cycles)."""
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(module_name)
    value = vars(module)[name]
    globals()[name] = value
    return value
