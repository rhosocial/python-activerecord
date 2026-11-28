# src/rhosocial/activerecord/backend/impl/sqlite/expression/__init__.py
"""
SQLite-specific expression classes.

This module provides expression classes that are specific to SQLite,
such as column info expressions, table list expressions, and REINDEX statement.

Directory structure (canonical top-level namespaces):
- introspection/  - Column info, PRAGMA, table count/DDL reads, and table list
- predicates/     - FTS MATCH predicate expression
- statements/     - REINDEX, VACUUM/ANALYZE, ATTACH/DETACH, DML, virtual tables (FTS5, R-Tree, Geopoly)
- query_parts/    - SQLite AUTOINCREMENT tail
- functions/      - SQLite JSON function
- sources/        - SQLite table source
- types/          - SQLite type-affinity classes
"""

from .introspection.introspection import (
    SQLiteColumnInfoExpression,
    SQLiteIndexDdlStatement,
    SQLiteIndexOwnerStatement,
    SQLitePragmaQueryStatement,
    SQLitePragmaSetStatement,
    SQLiteTableCountStatement,
    SQLiteTableDdlStatement,
    SQLiteTableStorageStatement,
)
from .sources.table import SQLiteTable
from .introspection.table_list import SQLiteTableListExpression
from .statements.reindex import SQLiteReindexStatement
from .statements.vacuum import SQLiteVacuumStatement, SQLiteAnalyzeStatement
from .statements.attach import SQLiteAttachStatement, SQLiteDetachStatement
from .predicates.predicates import SQLiteMatchPredicate
from .statements.dml import SQLiteInsertStatement
from .statements.fts5 import (
    SQLiteFTS5MatchPredicate,
    SQLiteFTS5CreateVirtualTable,
    SQLiteFTS5RankExpression,
    SQLiteFTS5HighlightExpression,
    SQLiteFTS5SnippetExpression,
)
from .statements.virtual_table import (
    SQLiteCreateVirtualTableStatement,
    SQLiteDropVirtualTableStatement,
)
from .statements.rtree import (
    SQLiteRTreeCreateVirtualTable,
    SQLiteRTreeRangeQuery,
)
from .statements.geopoly import (
    SQLiteGeopolyCreateVirtualTable,
    SQLiteGeopolyContainsExpression,
    SQLiteGeopolyAreaExpression,
)
from .functions.json import SQLiteJsonExtractFunction

# ``SQLite`` is the backend identifier spelled as §4.9.4 requires, and it is a
# compound word: the general capital-run rule would derive ``sq_lite_json_extract_function``
# instead of ``sqlite_json_extract_function``. Since a kind is part of the wire
# contract, the identifier is kept whole — and this is the SQLite package's own
# declaration, made where it assembles its own expressions. The core holds no
# backend names, so another backend declaring its own tokens needs no change here
# or in the core (§5.1: rhosocial's own packages get no privilege).
#
# The token itself is written once, in ``types.py`` beside the classes that
# declare it in their own bodies, and this loop and those classes both read the
# one value. A token spelled twice could drift, and a derived kind is part of
# the wire contract, so the two spellings would have been two places that have
# to stay in step with nothing keeping them in step — which is what
# ``.claude/rules/constants.md`` forbids and what its second check reports.
from .types.types import SQLITE_KIND_RESERVED

for _sqlite_expression in (
    SQLiteColumnInfoExpression,
    SQLiteIndexDdlStatement,
    SQLiteIndexOwnerStatement,
    SQLitePragmaQueryStatement,
    SQLitePragmaSetStatement,
    SQLiteTableCountStatement,
    SQLiteTableDdlStatement,
    SQLiteTableStorageStatement,
    SQLiteTable,
    SQLiteTableListExpression,
    SQLiteReindexStatement,
    SQLiteVacuumStatement,
    SQLiteAnalyzeStatement,
    SQLiteAttachStatement,
    SQLiteDetachStatement,
    SQLiteMatchPredicate,
    SQLiteInsertStatement,
    SQLiteFTS5MatchPredicate,
    SQLiteFTS5CreateVirtualTable,
    SQLiteFTS5RankExpression,
    SQLiteFTS5HighlightExpression,
    SQLiteFTS5SnippetExpression,
    SQLiteCreateVirtualTableStatement,
    SQLiteDropVirtualTableStatement,
    SQLiteRTreeCreateVirtualTable,
    SQLiteRTreeRangeQuery,
    SQLiteGeopolyCreateVirtualTable,
    SQLiteGeopolyContainsExpression,
    SQLiteGeopolyAreaExpression,
    SQLiteJsonExtractFunction,
):
    _sqlite_expression.KIND_RESERVED = SQLITE_KIND_RESERVED
del _sqlite_expression

__all__ = [
    "SQLiteColumnInfoExpression",
    "SQLiteIndexDdlStatement",
    "SQLiteIndexOwnerStatement",
    "SQLitePragmaQueryStatement",
    "SQLitePragmaSetStatement",
    "SQLiteTableCountStatement",
    "SQLiteTableDdlStatement",
    "SQLiteTableStorageStatement",
    "SQLiteTable",
    "SQLiteTableListExpression",
    "SQLiteReindexStatement",
    "SQLiteVacuumStatement",
    "SQLiteAnalyzeStatement",
    "SQLiteAttachStatement",
    "SQLiteDetachStatement",
    "SQLiteMatchPredicate",
    "SQLiteInsertStatement",
    "SQLiteFTS5MatchPredicate",
    "SQLiteFTS5CreateVirtualTable",
    "SQLiteFTS5RankExpression",
    "SQLiteFTS5HighlightExpression",
    "SQLiteFTS5SnippetExpression",
    "SQLiteCreateVirtualTableStatement",
    "SQLiteDropVirtualTableStatement",
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
