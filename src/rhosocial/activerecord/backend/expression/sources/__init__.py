# src/rhosocial/activerecord/backend/expression/sources/__init__.py
"""
Table sources -- the things a ``FROM`` clause can name.

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
renames nothing in the catalogue.
"""

from .base import TableSource
from .derived import DerivedTableSource, ValuesTableSource
from .functions import TableFunctionSource
from .graph import GraphTableSource
from .json import JsonTableSource
from .relation import NamedRelationRef
from .xml import XmlTableSource

__all__ = [
    "TableSource",
    "NamedRelationRef",
    "DerivedTableSource",
    "ValuesTableSource",
    "TableFunctionSource",
    "JsonTableSource",
    "XmlTableSource",
    "GraphTableSource",
]