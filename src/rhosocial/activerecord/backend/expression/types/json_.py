# src/rhosocial/activerecord/backend/expression/types/json_.py
"""JSON / JSONB types."""

from __future__ import annotations

from ._base import DataType


class JsonType(DataType):
    """JSON — standard JSON (SQL:2016)."""


class JsonBType(DataType):
    """JSONB — binary JSON (PostgreSQL)."""
