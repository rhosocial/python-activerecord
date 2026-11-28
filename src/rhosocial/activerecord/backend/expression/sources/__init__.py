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

__all__ = [
    'TableSource',
    'NamedRelationRef',
    'DerivedTableSource',
    'ValuesTableSource',
    'TableFunctionSource',
    'JsonTableSource',
    'XmlTableSource',
    'GraphTableSource',
]

import importlib

_MODULES = ('base', 'derived', 'functions', 'graph', 'json', 'query_sources', 'relation', 'subquery', 'xml')


def __getattr__(name):
    """Resolve a public name from this namespace lazily (no import cycles)."""
    for module_name in _MODULES:
        module = importlib.import_module(f'.{module_name}', __name__)
        if name in vars(module):
            value = vars(module)[name]
            globals()[name] = value  # cache so vars()/inspect see the name
            return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
