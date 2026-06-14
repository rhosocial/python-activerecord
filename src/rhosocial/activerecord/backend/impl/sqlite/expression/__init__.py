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
from .predicates import SQLiteMatchPredicate
from .fts5 import (
    FTS5MatchExpression,
    FTS5CreateVirtualTable,
    FTS5RankExpression,
    FTS5HighlightExpression,
    FTS5SnippetExpression,
)
from .rtree import (
    RTreeCreateVirtualTable,
    RTreeRangeQuery,
)
from .geopoly import (
    GeopolyCreateVirtualTable,
    GeopolyContainsExpression,
    GeopolyAreaExpression,
)

__all__ = [
    "SQLiteColumnInfoExpression",
    "SQLiteTableListExpression",
    "SQLiteReindexExpression",
    "SQLiteMatchPredicate",
    "FTS5MatchExpression",
    "FTS5CreateVirtualTable",
    "FTS5RankExpression",
    "FTS5HighlightExpression",
    "FTS5SnippetExpression",
    "RTreeCreateVirtualTable",
    "RTreeRangeQuery",
    "GeopolyCreateVirtualTable",
    "GeopolyContainsExpression",
    "GeopolyAreaExpression",
]

# Auto-register all SQLite expression classes when this module is imported
from rhosocial.activerecord.backend.expression.serialization import ExpressionRegistry

for _expr_cls in (
    SQLiteColumnInfoExpression,
    SQLiteTableListExpression,
    SQLiteReindexExpression,
    SQLiteMatchPredicate,
    FTS5MatchExpression,
    FTS5CreateVirtualTable,
    FTS5RankExpression,
    FTS5HighlightExpression,
    FTS5SnippetExpression,
    RTreeCreateVirtualTable,
    RTreeRangeQuery,
    GeopolyCreateVirtualTable,
    GeopolyContainsExpression,
    GeopolyAreaExpression,
):
    ExpressionRegistry.register(_expr_cls)
