# src/rhosocial/activerecord/backend/impl/sqlite/explain/__init__.py
"""
SQLite EXPLAIN result types.

Quick start::

    from rhosocial.activerecord.backend.impl.sqlite.explain import (
        SQLiteExplainRow,
        SQLiteExplainQueryPlanRow,
        SQLiteExplainResult,
        SQLiteExplainQueryPlanResult,
    )
"""

from .types import (
    SQLiteExplainRow,
    SQLiteExplainQueryPlanRow,
    SQLiteExplainResult,
    SQLiteExplainQueryPlanResult,
)

__all__ = [
    "SQLiteExplainRow",
    "SQLiteExplainQueryPlanRow",
    "SQLiteExplainResult",
    "SQLiteExplainQueryPlanResult",
]
