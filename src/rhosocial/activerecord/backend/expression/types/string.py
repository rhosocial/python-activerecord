# src/rhosocial/activerecord/backend/expression/types/string.py
"""Character / string SQL types."""

from __future__ import annotations

from typing import Optional

from ._base import DataType


class CharType(DataType):
    """CHAR[(n)] / CHARACTER[(n)] — fixed-length string."""

    length: Optional[int] = None

    def __init__(self, length: Optional[int] = None, dialect=None):
        super().__init__(dialect)
        self.length = length

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.length == other.length

    def __hash__(self) -> int:
        return hash((type(self), self.length))

    def _default_sql(self) -> str:
        return f"CHAR({self.length})" if self.length is not None else "CHAR"


class VarCharType(DataType):
    """VARCHAR(n) — variable-length string."""

    length: Optional[int] = None

    def __init__(self, length: Optional[int] = None, dialect=None):
        super().__init__(dialect)
        self.length = length

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.length == other.length

    def __hash__(self) -> int:
        return hash((type(self), self.length))

    def _default_sql(self) -> str:
        if self.length is not None:
            return f"VARCHAR({self.length})"
        return "VARCHAR"


class TextType(DataType):
    """TEXT / CLOB / LONGVARCHAR — unbounded string."""

    def _default_sql(self) -> str:
        return "TEXT"
