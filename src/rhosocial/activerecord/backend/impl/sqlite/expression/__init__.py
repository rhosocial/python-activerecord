# src/rhosocial/activerecord/backend/impl/sqlite/expression/__init__.py
"""
SQLite-specific expression classes.

This module provides expression classes that are specific to SQLite,
such as column info expressions, table list expressions, and REINDEX statement.

Directory structure:
- introspection.py  - Column info expression
- table_list.py     - Table list expression
- reindex.py        - REINDEX expression
- predicates.py    - FTS MATCH predicate expression
"""

from .introspection import SQLiteColumnInfoExpression
from .table_list import SQLiteTableListExpression
from .reindex import SQLiteReindexExpression
from .predicates import SQLiteMatchPredicate

__all__ = [
    "SQLiteColumnInfoExpression",
    "SQLiteTableListExpression",
    "SQLiteReindexExpression",
    "SQLiteMatchPredicate",
]