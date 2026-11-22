# src/rhosocial/activerecord/backend/expression/types/binary.py
"""Binary / blob SQL types."""

from __future__ import annotations

from typing import Optional

from ._base import DataType, LENGTH_PARAMETERS


class BlobType(DataType):
    """BLOB / BYTEA — binary storage declared as a *minimum* size.

    ``BYTEA`` is PostgreSQL's name for the same unbounded byte storage.

    The unit is bytes, not characters, and the declaration is a minimum: a
    backend rounds up to a tier of its own (``BLOB`` to ``MEDIUMBLOB`` to
    ``LONGBLOB`` on MySQL, ``RAW`` past 2 000 bytes on Oracle, plain ``BYTEA``
    where there is no tier to choose), so one model can say "this column must
    hold N bytes" without naming a backend's spelling.
    """

    name = "blob"

    SPELLINGS = ("blob", "bytea")

    def __init__(self, dialect=None, length: Optional[int] = None, *,
                 spelling: str = "blob"):
        super().__init__(dialect)
        self._length = length
        self.spelling = spelling

    @property
    def length(self) -> Optional[int]:
        """The declared minimum, or the width this server supplies for none declared.

        Resolved rather than stored, exactly as on :class:`VarBinaryType`, so a
        dialect bound after the fact resolves the same way as one passed at
        construction.
        """
        return self._length

    @length.setter
    def length(self, value: Optional[int]) -> None:
        self._length = value

    PARAMETERS = LENGTH_PARAMETERS


class BinaryType(DataType):
    """BINARY(n) — fixed-length byte string."""

    name = "binary"

    length: Optional[int] = None

    def __init__(self, dialect=None, length: Optional[int] = None,
                 ):
        super().__init__(dialect)
        self.length = length

    PARAMETERS = LENGTH_PARAMETERS

class VarBinaryType(DataType):
    """VARBINARY(n) — variable-length byte string."""

    name = "varbinary"

    length: Optional[int] = None

    def __init__(self, dialect=None, length: Optional[int] = None,
                 ):
        super().__init__(dialect)
        self.length = length

    PARAMETERS = LENGTH_PARAMETERS
