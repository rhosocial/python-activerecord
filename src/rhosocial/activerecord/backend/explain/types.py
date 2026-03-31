# src/rhosocial/activerecord/backend/explain/types.py
"""
EXPLAIN result base types.

This module defines the base result class for EXPLAIN query execution.
Each backend provides its own subclass with backend-specific row types.

Design note:
    BaseExplainResult intentionally uses pydantic.BaseModel rather than
    ActiveRecord to avoid a circular dependency between the backend layer
    and the model layer.
"""

from typing import Any, Dict, List

from pydantic import BaseModel


class BaseExplainResult(BaseModel):
    """Base class for all backend EXPLAIN results.

    Attributes:
        raw_rows: Raw row data returned by fetch_all().
        sql:      The EXPLAIN SQL that was actually executed.
        duration: Wall-clock execution time in seconds.

    Backend subclasses add typed ``rows`` attributes and may add
    convenience methods suited to their specific output format.
    """

    raw_rows: List[Dict[str, Any]]
    sql: str
    duration: float
