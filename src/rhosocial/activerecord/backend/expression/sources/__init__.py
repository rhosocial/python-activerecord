# src/rhosocial/activerecord/backend/expression/sources/__init__.py
"""Table sources -- the things a ``FROM`` clause can name.

Separate from :mod:`..objects` on purpose. Objects answer *what persists*;
sources answer *what can appear in a query*. The two are connected by
composition, not inheritance:

* :class:`NamedRelationRef` holds a relation object -- a persisted relation
  read by name.
* :class:`DerivedTableSource`, :class:`ValuesTableSource`,
  :class:`TableFunctionSource`, :class:`JsonTableSource`,
  :class:`XmlTableSource` and :class:`GraphTableSource` have no object at
  all -- their rows exist only for one statement.

Nothing here is a schema object, and no schema object is a table source. An
alias lives on the source, because aliasing renames a row for one query and
renames nothing in the catalogue."""

import importlib

# Public name -> defining module. Private names here stay reachable
# through this package but are not part of __all__.
_EXPORTS = {
    'AliasableMixin': 'rhosocial.activerecord.backend.expression.sources.relation',
    'Any': 'rhosocial.activerecord.backend.expression.sources.derived',
    'ArithmeticMixin': 'rhosocial.activerecord.backend.expression.sources.query_sources',
    'BaseExpression': 'rhosocial.activerecord.backend.expression.sources.base',
    'CTEClause': 'rhosocial.activerecord.backend.expression.sources.query_sources',
    'ComparisonMixin': 'rhosocial.activerecord.backend.expression.sources.query_sources',
    'DerivedTableSource': 'rhosocial.activerecord.backend.expression.sources.derived',
    'Dict': 'rhosocial.activerecord.backend.expression.sources.relation',
    'Enum': 'rhosocial.activerecord.backend.expression.sources.query_sources',
    'GraphTableSource': 'rhosocial.activerecord.backend.expression.sources.graph',
    'JSONTableColumn': 'rhosocial.activerecord.backend.expression.sources.query_sources',
    'JSONTableExpression': 'rhosocial.activerecord.backend.expression.sources.query_sources',
    'JsonTableSource': 'rhosocial.activerecord.backend.expression.sources.json',
    'LateralExpression': 'rhosocial.activerecord.backend.expression.sources.query_sources',
    'List': 'rhosocial.activerecord.backend.expression.sources.query_sources',
    'NamedRelationRef': 'rhosocial.activerecord.backend.expression.sources.relation',
    'Optional': 'rhosocial.activerecord.backend.expression.sources.base',
    'QueryWithParams': 'rhosocial.activerecord.backend.expression.sources.subquery',
    'SQLQueryAndParams': 'rhosocial.activerecord.backend.expression.sources.query_sources',
    'SQLValue': 'rhosocial.activerecord.backend.expression.sources.query_sources',
    'SchemaObject': 'rhosocial.activerecord.backend.expression.sources.relation',
    'SetOperation': 'rhosocial.activerecord.backend.expression.sources.query_sources',
    'SetOperationKind': 'rhosocial.activerecord.backend.expression.sources.query_sources',
    'Subquery': 'rhosocial.activerecord.backend.expression.sources.query_sources',
    'TYPE_CHECKING': 'rhosocial.activerecord.backend.expression.sources.query_sources',
    'TableFunctionExpression': 'rhosocial.activerecord.backend.expression.sources.query_sources',
    'TableFunctionSource': 'rhosocial.activerecord.backend.expression.sources.functions',
    'TableSource': 'rhosocial.activerecord.backend.expression.sources.base',
    'Tuple': 'rhosocial.activerecord.backend.expression.sources.query_sources',
    'TypeCastingMixin': 'rhosocial.activerecord.backend.expression.sources.subquery',
    'Union': 'rhosocial.activerecord.backend.expression.sources.query_sources',
    'ValuesExpression': 'rhosocial.activerecord.backend.expression.sources.query_sources',
    'ValuesTableSource': 'rhosocial.activerecord.backend.expression.sources.derived',
    'WithStatement': 'rhosocial.activerecord.backend.expression.sources.query_sources',
    'XmlTableSource': 'rhosocial.activerecord.backend.expression.sources.xml',
    'dataclass': 'rhosocial.activerecord.backend.expression.sources.query_sources',
    'normalize_join_type': 'rhosocial.activerecord.backend.expression.sources.query_sources',
}

__all__ = [
    'DerivedTableSource',
    'GraphTableSource',
    'JsonTableSource',
    'NamedRelationRef',
    'TableFunctionSource',
    'TableSource',
    'ValuesTableSource',
    'XmlTableSource',
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
