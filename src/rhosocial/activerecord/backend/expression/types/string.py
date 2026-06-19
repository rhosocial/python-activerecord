# src/rhosocial/activerecord/backend/expression/types/string.py
"""Character / string SQL types."""

from __future__ import annotations

from typing import Optional, Set

from ._base import DataType


class CharType(DataType):
    """CHAR[(n)] / CHARACTER[(n)] — fixed-length string."""

    length: Optional[int] = None

    def __init__(self, length: Optional[int] = None, dialect=None):
        super().__init__(dialect)
        self.length = length

    def _type_params(self) -> tuple:
        return (self.length,)

    def _default_sql(self) -> str:
        return f"CHAR({self.length})" if self.length is not None else "CHAR"


class VarCharType(DataType):
    """VARCHAR(n) / CHARACTER VARYING(n) — variable-length string."""

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'CharacterVaryingType'}

    length: Optional[int] = None

    def __init__(self, length: Optional[int] = None, dialect=None):
        super().__init__(dialect)
        self.length = length

    def _type_params(self) -> tuple:
        return (self.length,)

    def _default_sql(self) -> str:
        if self.length is not None:
            return f"VARCHAR({self.length})"
        return "VARCHAR"


class CharacterVaryingType(VarCharType):
    """CHARACTER VARYING(n) — canonical synonym of VARCHAR(n)."""

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'VarCharType'}

    def _default_sql(self) -> str:
        if self.length is not None:
            return f"CHARACTER VARYING({self.length})"
        return "CHARACTER VARYING"


class TextType(DataType):
    """TEXT / CLOB / LONGVARCHAR — unbounded string."""

    def _default_sql(self) -> str:
        return "TEXT"
