# src/rhosocial/activerecord/backend/result.py
"""
Defines common data structures and type hints for backend operations.

This file serves as a central place for core backend-related types,
focusing on query results to avoid circular imports.
"""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum, auto
from typing import Any, Dict, Generic, Optional, TypeVar, Union

# Base type aliases
DatabaseValue = Union[str, int, float, bool, datetime, Decimal, bytes, None]
PythonValue = TypeVar('PythonValue')
T = TypeVar('T')

@dataclass
class QueryResult(Generic[T]):
    """Query result wrapper"""
    data: Optional[T] = None
    affected_rows: int = 0
    last_insert_id: Optional[int] = None
    duration: float = 0.0  # Query execution time (seconds)
