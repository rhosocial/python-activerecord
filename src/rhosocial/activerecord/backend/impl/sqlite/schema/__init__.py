# src/rhosocial/activerecord/backend/impl/sqlite/schema/__init__.py
"""SQLite schema differ."""

from .differ import SQLiteSchemaDiffer

__all__ = ["SQLiteSchemaDiffer"]
