# src/rhosocial/activerecord/backend/expression/types/json_.py
"""JSON / JSONB types."""

from __future__ import annotations

from typing import Set

from ._base import DataType


class JsonType(DataType):
    """JSON — standard JSON (SQL:2016)."""

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'JsonBType'}

    def _default_sql(self) -> str:
        return "JSON"


class JsonBType(DataType):
    """JSONB — binary JSON (PostgreSQL)."""

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'JsonType'}

    def _default_sql(self) -> str:
        return "JSONB"
