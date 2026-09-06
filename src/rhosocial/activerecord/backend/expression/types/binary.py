# src/rhosocial/activerecord/backend/expression/types/binary.py
"""Binary / blob SQL types."""

from __future__ import annotations

from typing import Optional

from ._base import DataType
from ._validation import LENGTH_MIN, require_optional_range


class BlobType(DataType):
    """BLOB / BYTEA / VARBINARY(MAX) — binary large object."""


class BinaryType(DataType):
    """BINARY(n) — fixed-length binary string.

    A *semantic* type rendered per backend to its native fixed-width binary
    form, e.g. MySQL/MariaDB/SQL Server ``BINARY(n)``, Oracle ``RAW(n)``,
    PostgreSQL ``BYTEA`` (no fixed-width binary), Firebird
    ``CHAR(n) CHARACTER SET OCTETS``, SQLite ``BLOB``.
    """

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


class VarBinaryType(DataType):
    """VARBINARY(n) — variable-length binary string.

    A *semantic* type rendered per backend to its native variable-length
    binary form, e.g. MySQL/MariaDB/SQL Server ``VARBINARY(n)``, Oracle
    ``RAW(n)``, PostgreSQL ``BYTEA``, Firebird / SQLite ``BLOB``.
    """

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