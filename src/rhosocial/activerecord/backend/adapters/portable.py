# src/rhosocial/activerecord/backend/adapters/portable.py
"""Portable ``(Python type, driver type)`` mapping -- a REUSABLE helper.

This is NOT a core suggestion implementation: the DataAdapterSuggestionSupport
protocol (backend.suggestion.protocols) has no default. A concrete backend MAY
reuse this baseline to answer the common scalar types, just as it reuses the
adapter classes here. Native types (str/int/float/bytes) are deliberately
absent = pass through untouched.
"""
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Tuple, Type
from uuid import UUID

PORTABLE_TYPE_MAPPINGS: Tuple[Tuple[Type, Type], ...] = (
    (bool, int),
    (datetime, str),
    (date, str),
    (time, str),
    (Decimal, float),
    (UUID, str),
    (dict, str),
    (list, str),
    (Enum, str),
)
