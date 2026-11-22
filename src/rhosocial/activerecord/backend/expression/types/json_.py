# src/rhosocial/activerecord/backend/expression/types/json_.py
"""JSON / JSONB types.

Both are *semantic* types: "the value means a JSON document" is the same on
every backend, while the storage is each backend's own choice (``JSON``,
``JSONB``, ``TEXT``, ``VARCHAR2``, ``NVARCHAR(MAX)``).

``length`` is a declared **minimum**. SQL has no "JSON of any size": the
fallbacks a backend chooses are tiers of its text family, so the only portable
statement is "this document must fit N characters", which a backend maps to the
tier that satisfies it -- and, where no tier is large enough, to the backend's
unbounded large-object type rather than to a runtime overflow.
"""
from __future__ import annotations

from typing import Optional

from ._base import LENGTH_PARAMETERS, DataType


class JsonType(DataType):
    """JSON — standard JSON (SQL:2016)."""

    name = "json"

    def __init__(self, dialect=None, length: Optional[int] = None):
        super().__init__(dialect)
        self._length = length

    @property
    def length(self) -> Optional[int]:
        """The declared minimum, or the width this server supplies for none declared.

        Resolved rather than stored, exactly as on :class:`VarCharType`, so a
        dialect bound after the fact resolves the same way as one passed at
        construction.
        """
        return self._length

    @length.setter
    def length(self, value: Optional[int]) -> None:
        self._length = value

    PARAMETERS = LENGTH_PARAMETERS


class JsonBType(DataType):
    """JSONB — binary JSON (PostgreSQL)."""

    name = "jsonb"

    def __init__(self, dialect=None, length: Optional[int] = None):
        super().__init__(dialect)
        self._length = length

    @property
    def length(self) -> Optional[int]:
        """The declared minimum, or the width this server supplies for none declared.

        Resolved rather than stored, exactly as on :class:`JsonType`.
        """
        return self._length

    @length.setter
    def length(self, value: Optional[int]) -> None:
        self._length = value

    PARAMETERS = LENGTH_PARAMETERS