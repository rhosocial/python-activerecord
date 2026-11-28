# src/rhosocial/activerecord/backend/impl/sqlite/expression/predicates/__init__.py
"""SQLite-specific predicate expressions."""

from .predicates import SQLiteMatchPredicate

__all__ = ["SQLiteMatchPredicate"]
