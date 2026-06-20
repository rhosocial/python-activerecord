# src/rhosocial/activerecord/backend/expression/types/binary.py
"""Binary / blob SQL types."""

from __future__ import annotations

from ._base import DataType


class BlobType(DataType):
    """BLOB / BYTEA / VARBINARY — binary large object."""
