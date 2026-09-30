# src/rhosocial/activerecord/backend/expression/types/uuid_.py
"""UUID — universally unique identifier."""

from __future__ import annotations

from ._base import DataType


class UUIDType(DataType):
    """UUID — universally unique identifier (RFC 4122).

    A *semantic* type: the value means "a UUID" on every backend, while the
    storage is each backend's own choice. Backends that can render this type
    directly implement ``format_data_type_uuid``; the rest declare a
    substitute through ``suggested_data_types()``.

    Storage by backend, for reference when reading a DDL diff:

    ==============  ==========================
    Backend         Storage
    ==============  ==========================
    PostgreSQL      ``UUID``
    Firebird        ``CHAR(16) CHARACTER SET OCTETS``
    MariaDB         ``BINARY(16)``
    MySQL           ``BINARY`` (no length; see its ``suggested_data_types``)
    ClickHouse      ``UUID`` (via its own ``ClickHouseUUIDType``)
    SQL Server      ``uniqueidentifier`` (via its own type class)
    Oracle          ``RAW(16)`` (via ``suggest_column_type``)
    Snowflake       ``VARCHAR``
    BigQuery        ``STRING``
    SQLite          ``TEXT`` (via ``suggested_data_types``)
    ==============  ==========================

    This is a *documentation* table, not a contract: a backend whose entry is
    missing has not implemented the type, and one whose row disagrees with its
    ``suggested_data_types()`` has a defect worth reporting.

    Generating a UUID is a separate concern and lives in the expression layer
    (:mod:`...expression.uuid`) — see ``UUIDSupport``. Storage says nothing
    about whether the database can produce a value.
    """

    name = "uuid"