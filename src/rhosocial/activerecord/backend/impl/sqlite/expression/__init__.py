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
from .reindex import SQLiteReindexExpression
from .vacuum import SQLiteVacuumExpression, SQLiteAnalyzeExpression
from .attach import SQLiteAttachExpression, SQLiteDetachExpression
from .predicates import SQLiteMatchPredicate
from .fts5 import (
    SQLiteFTS5CreateVirtualTable,
    SQLiteFTS5RankExpression,
    SQLiteFTS5HighlightExpression,
    SQLiteFTS5SnippetExpression,
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

__all__ = [
    "SQLiteColumnInfoExpression",
    "SQLiteTableListExpression",
    "SQLiteReindexExpression",
    "SQLiteVacuumExpression",
    "SQLiteAnalyzeExpression",
    "SQLiteAttachExpression",
    "SQLiteDetachExpression",
    "SQLiteMatchPredicate",
    "SQLiteFTS5CreateVirtualTable",
    "SQLiteFTS5RankExpression",
    "SQLiteFTS5HighlightExpression",
    "SQLiteFTS5SnippetExpression",
    "SQLiteRTreeCreateVirtualTable",
    "SQLiteRTreeRangeQuery",
    "SQLiteGeopolyCreateVirtualTable",
    "SQLiteGeopolyContainsExpression",
    "SQLiteGeopolyAreaExpression",
]

# Auto-register all SQLite expression classes when this module is imported
from rhosocial.activerecord.backend.expression.serialization import ExpressionRegistry

for _expr_cls in (
    SQLiteColumnInfoExpression,
    SQLiteTableListExpression,
    SQLiteReindexExpression,
    SQLiteVacuumExpression,
    SQLiteAnalyzeExpression,
    SQLiteAttachExpression,
    SQLiteDetachExpression,
    SQLiteMatchPredicate,
    SQLiteFTS5CreateVirtualTable,
    SQLiteFTS5RankExpression,
    SQLiteFTS5HighlightExpression,
    SQLiteFTS5SnippetExpression,
    SQLiteRTreeCreateVirtualTable,
    SQLiteRTreeRangeQuery,
    SQLiteGeopolyCreateVirtualTable,
    SQLiteGeopolyContainsExpression,
    SQLiteGeopolyAreaExpression,
):
    ExpressionRegistry.register(_expr_cls)
