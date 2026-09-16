# src/rhosocial/activerecord/backend/expression/types/string.py
"""Character / string SQL types."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ._base import DataType


class CharType(DataType):
    """CHAR[(n)] / CHARACTER[(n)] — fixed-length string."""

    name = "char"

    length: Optional[int] = None

    def __init__(self, dialect=None, length: Optional[int] = None,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.length = length

    def _type_params(self) -> tuple:
        return (self.length,)


class VarCharType(DataType):
    """VARCHAR(n) — variable-length string."""

    name = "varchar"

    length: Optional[int] = None

    def __init__(self, dialect=None, length: Optional[int] = None,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.length = length

    def _type_params(self) -> tuple:
        return (self.length,)


class TextType(DataType):
    """TEXT / CLOB / LONGVARCHAR — unbounded string."""

    name = "text"
