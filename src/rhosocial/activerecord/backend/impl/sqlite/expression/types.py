# src/rhosocial/activerecord/backend/impl/sqlite/expression/types.py
"""SQLite-specific DataType subclasses.

Naming convention
-----------------
SQLite-specific types use the ``Sqlite`` prefix to distinguish them from
the core types (which have no prefix).  This avoids ambiguity when both
core and backend types are used together.

Usage scope
-----------
These types are used **only** for SQLite backend DDL column definitions,
introspection result parsing, and schema comparison.  They should **not**
be used by application code directly — always use the core types for
DDL definition expressions (``ColumnDefinition.data_type``).

Details
-------
SQLite uses type affinity rather than strict types. These classes extend the
core types to handle SQLite's relaxed type system and its special behaviour
(e.g. INTEGER PRIMARY KEY → rowid alias, AUTOINCREMENT).

Most core types (IntegerType, TextType, etc.) work as-is for SQLite.
SQLite-specific subclasses are defined here only where the behaviour
differs from the generic type.
"""

from __future__ import annotations

from typing import Set

from rhosocial.activerecord.backend.expression.types import (
    IntegerType,
    TextType,
)


class SQLiteIntegerType(IntegerType):
    """SQLite INTEGER — rowid alias when used as PRIMARY KEY.

    In SQLite ``INTEGER PRIMARY KEY`` makes the column an alias for the
    internal rowid.  ``INTEGER PRIMARY KEY AUTOINCREMENT`` prevents rowid
    reuse.

    The class is functionally identical to ``IntegerType`` for now; the
    distinction matters mainly for introspection and schema comparison.
    """

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'IntegerType'}


class SQLiteTextType(TextType):
    """SQLite TEXT — the only string affinity.

    SQLite does not distinguish CHAR/VARCHAR/TEXT at the storage level;
    all string-like types have TEXT affinity.  This class exists so the
    dialect can map ``VARCHAR`` / ``CHAR`` etc. to a canonical type during
    introspection round-trips.
    """

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'TextType', 'VarCharType', 'CharType'}
