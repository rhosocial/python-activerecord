# src/rhosocial/activerecord/backend/expression/types/uuid_.py
"""UUID — universally unique identifier."""

from __future__ import annotations

from ._base import DataType


class UUIDType(DataType):
    """UUID — universally unique identifier (RFC 4122).

    A *semantic* type: each backend renders it to its native / most compact
    storage, e.g. PostgreSQL ``UUID``, MySQL/MariaDB ``BINARY(16)``,
    SQL Server ``uniqueidentifier``, Oracle ``RAW(16)``, Firebird
    ``CHAR(16) CHARACTER SET OCTETS``, SQLite ``TEXT``.
    """