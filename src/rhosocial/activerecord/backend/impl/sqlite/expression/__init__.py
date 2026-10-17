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

# Auto-register all SQLite expression classes when this module is imported
from rhosocial.activerecord.backend.expression.serialization import register_expression_class

for _expr_cls in (
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
    CreateVirtualTableStatement,
    DropVirtualTableStatement,
    SQLiteRTreeCreateVirtualTable,
    SQLiteRTreeRangeQuery,
    SQLiteGeopolyCreateVirtualTable,
    SQLiteGeopolyContainsExpression,
    SQLiteGeopolyAreaExpression,
    SQLiteJsonExtractFunction,
):
    register_expression_class(_expr_cls)
