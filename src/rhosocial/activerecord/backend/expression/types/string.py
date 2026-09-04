# src/rhosocial/activerecord/backend/expression/types/string.py
"""Character / string SQL types."""

from __future__ import annotations

from typing import Optional

from ._base import DataType
from ._validation import LENGTH_MIN, require_optional_range


class CharType(DataType):
    """CHAR[(n)] / CHARACTER[(n)] — fixed-length string."""

    # SQL-standard minimum; backend subtypes may tighten the upper bound.
    LENGTH_MIN = LENGTH_MIN
    LENGTH_MAX: Optional[int] = None

    length: Optional[int] = None

    def __init__(self, dialect=None, *, length: Optional[int] = None):
        super().__init__(dialect)
        self.length = require_optional_range(
            length, type(self).__name__, "length", self.LENGTH_MIN, self.LENGTH_MAX
        )

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.length == other.length

    def __hash__(self) -> int:
        return hash((type(self), self.length))


class VarCharType(DataType):
    """VARCHAR(n) — variable-length string."""

    # SQL-standard minimum; backend subtypes may tighten the upper bound.
    LENGTH_MIN = LENGTH_MIN
    LENGTH_MAX: Optional[int] = None

    length: Optional[int] = None

    def __init__(self, dialect=None, *, length: Optional[int] = None):
        super().__init__(dialect)
        self.length = require_optional_range(
            length, type(self).__name__, "length", self.LENGTH_MIN, self.LENGTH_MAX
        )

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.length == other.length

    def __hash__(self) -> int:
        return hash((type(self), self.length))


class TextType(DataType):
    """TEXT / CLOB / LONGVARCHAR — unbounded string."""
