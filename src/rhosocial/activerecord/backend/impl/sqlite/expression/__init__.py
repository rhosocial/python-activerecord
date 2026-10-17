# src/rhosocial/activerecord/backend/impl/sqlite/expression/__init__.py
"""
SQLite-specific expression classes.

This module provides expression classes that are specific to SQLite,
such as column info expressions, table list expressions, and REINDEX statement.

Directory structure:
- introspection.py  - Column info expression
- table_list.py     - Table list expression
- reindex.py        - REINDEX expression
- predicates.py     - FTS MATCH predicate expression
- fts5.py           - FTS5 expression classes
- rtree.py          - R-Tree expression classes
- geopoly.py        - Geopoly expression classes
"""

from .introspection import SQLiteColumnInfoExpression
from .table_list import SQLiteTableListExpression
from .reindex import SQLiteReindexStatement
from .vacuum import SQLiteVacuumStatement, SQLiteAnalyzeStatement
from .attach import SQLiteAttachExpression, SQLiteDetachExpression
from .predicates import SQLiteMatchPredicate
from .dml import SQLiteInsertStatement
from .fts5 import (
    SQLiteFTS5MatchPredicate,
    SQLiteFTS5CreateVirtualTable,
    SQLiteFTS5RankExpression,
    SQLiteFTS5HighlightExpression,
    SQLiteFTS5SnippetExpression,
)
from .virtual_table import (
    CreateVirtualTableStatement,
    DropVirtualTableStatement,
)
from .rtree import (
    SQLiteRTreeCreateVirtualTable,
    SQLiteRTreeRangeQuery,
)
from .geopoly import (
    SQLiteGeopolyCreateVirtualTable,
    SQLiteGeopolyContainsExpression,
    SQLiteGeopolyAreaExpression,
)
from .json import SQLiteJsonExtractFunction

# ``SQLite`` is the backend identifier spelled as §4.9.4 requires, and it is a
# compound word: the general capital-run rule would derive ``sq_lite_json_extract_function``
# instead of ``sqlite_json_extract_function``. Since a kind is part of the wire
# contract, the identifier is kept whole — and this is the SQLite package's own
# declaration, made where it assembles its own expressions. The core holds no
# backend names, so another backend declaring its own tokens needs no change here
# or in the core (§5.1: rhosocial's own packages get no privilege).
for _sqlite_expression in (
    SQLiteColumnInfoExpression,
    SQLiteTableListExpression,
    SQLiteReindexStatement,
    SQLiteVacuumStatement,
    SQLiteAnalyzeStatement,
    SQLiteAttachExpression,
    SQLiteDetachExpression,
    SQLiteMatchPredicate,
    SQLiteInsertStatement,
    SQLiteFTS5MatchPredicate,
    SQLiteFTS5CreateVirtualTable,
    SQLiteFTS5RankExpression,
    SQLiteFTS5HighlightExpression,
    SQLiteFTS5SnippetExpression,
    SQLiteRTreeCreateVirtualTable,
    SQLiteRTreeRangeQuery,
    SQLiteGeopolyCreateVirtualTable,
    SQLiteGeopolyContainsExpression,
    SQLiteGeopolyAreaExpression,
    SQLiteJsonExtractFunction,
):
    _sqlite_expression.KIND_RESERVED = ("SQLite",)
del _sqlite_expression

__all__ = [
    "SQLiteColumnInfoExpression",
    "SQLiteTableListExpression",
    "SQLiteReindexStatement",
    "SQLiteVacuumStatement",
    "SQLiteAnalyzeStatement",
    "SQLiteAttachExpression",
    "SQLiteDetachExpression",
    "SQLiteMatchPredicate",
    "SQLiteInsertStatement",
    "SQLiteFTS5MatchPredicate",
    "SQLiteFTS5CreateVirtualTable",
    "SQLiteFTS5RankExpression",
    "SQLiteFTS5HighlightExpression",
    "SQLiteFTS5SnippetExpression",
    "CreateVirtualTableStatement",
    "DropVirtualTableStatement",
    "SQLiteRTreeCreateVirtualTable",
    "SQLiteRTreeRangeQuery",
    "SQLiteGeopolyCreateVirtualTable",
    "SQLiteGeopolyContainsExpression",
    "SQLiteGeopolyAreaExpression",
    "SQLiteJsonExtractFunction",
]

# No registration loop: the framework's assembly point walks this package and
# registers every expression defined in it, so a hand-maintained list here could
# only ever be out of date.
