# src/rhosocial/activerecord/backend/expression/types/uuid_.py
"""UUID — universally unique identifier."""

from __future__ import annotations

from ._base import DataType


class UUIDType(DataType):
    """UUID — universally unique identifier (RFC 9562, ISO/IEC 9834-8).

    A *semantic* type: the value means "a UUID" on every backend, while the
    storage is each backend's own choice. Backends that can render this type
    directly implement ``format_data_type_uuid``; the rest declare a
    substitute through ``suggested_data_types()``.

    Storage by backend, for reference when reading a DDL diff. Where a row
    names a spelling the dialect does not actually write, that is said in
    the row, because the point of the table is to help you read the DDL this
    framework *emits*, not to describe an abstract backend.

    ==============  ==========================
    Backend         Storage
    ==============  ==========================
    PostgreSQL      ``UUID`` — the native ``uuid`` type, for UUIDs "as
                     defined by RFC 9562, ISO/IEC 9834-8:2005, and related
                     standards"
    Oracle          **no ``UUID`` data type in any released version, 26ai
                     included** — 23ai added the ``UUID()`` *function*, which
                     "returns a version 4 variant 1 UUID as a ``RAW(16)`` value".
                     The substitute is ``RAW``, and ``RAW(size)`` is "raw binary
                     data of length *size* bytes", so the dialect gives
                     ``OracleRawType`` a default length of 16 — the width a
                     UUID actually needs, and the width ``UUID()`` returns
    SQL Server      ``UNIQUEIDENTIFIER`` — "a 16-byte GUID". Declared as the
                     substitute, so T-SQL never sees the core ``uuid`` name
    MySQL           no UUID type. MySQL spells the bare byte string
                     ``BINARY`` as ``BINARY(1)`` ("if omitted, *M* defaults
                     to 1"), which cannot hold 16 bytes; MySQL's own binary
                     UUID is 16 bytes — ``UUID_TO_BIN()`` returns "a
                     ``VARBINARY(16)`` value"
    MariaDB         native ``UUID``: "``UUID`` is available from MariaDB
                     10.7", for "the storage of 128-bit UUID data". The
                     dialect renders ``UUID`` and version-gates it;
                     ``BINARY(16)`` is only the pre-10.7 emulation
    SQLite          no native type — five storage classes, five affinities,
                     no UUID among them; a UUID gets TEXT affinity
    Snowflake       **native ``UUID``, added in server release 10.2**
                     (Jan 26-30, 2026) — "stores universally unique identifiers
                     (UUIDs)", and "a UUID is a 128-bit binary value". Syntax is
                     ``<column_name> UUID`` with no parameters. Our dialect
                     renders ``UUID`` (via ``SnowflakeUuidType``) and
                     version-gates it at 10.2; below that it still substitutes
                     ``VARCHAR``. Reading is the same either way — "Snowflake
                     drivers treat UUID values as text strings", in the 36-char
                     8-4-4-4-12 form
    BigQuery        no UUID type — its type list is closed and documented,
                     and ``STRING`` is the only character type in it
    ClickHouse      ``UUID`` (via its own ``ClickHouseUUIDType``) — "a
                     16-byte value used to identify records"
    Firebird        ``CHAR(16) CHARACTER SET OCTETS``, which is exactly the
                     type Firebird spells ``BINARY(16)``; all three of its
                     UUID functions return ``BINARY(16)``
    ==============  ==========================

    This is a *documentation* table, not a contract: a backend whose entry is
    missing has not implemented the type, and one whose row disagrees with its
    ``suggested_data_types()`` has a defect worth reporting. A row that
    contradicts the vendor's own documentation is a defect *here* — that is the
    rule this table is checked against, row by row.

    Vendor documentation, checked row by row:

    * PostgreSQL —
      https://www.postgresql.org/docs/current/datatype-uuid.html
    * Oracle — Built-In Data Type Summary and the datatype grammar, which
      list no ``UUID``:
      https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/Data-Types.html
      The ``UUID()`` function reference:
      https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/uuid.html
    * SQL Server —
      https://learn.microsoft.com/en-us/sql/t-sql/data-types/uniqueidentifier-transact-sql
    * MySQL — the closed chapter list, the ``BINARY[(M)]`` syntax rule and
      ``UUID_TO_BIN()``:
      https://dev.mysql.com/doc/refman/8.4/en/data-types.html
      https://dev.mysql.com/doc/refman/8.4/en/string-type-syntax.html
      https://dev.mysql.com/doc/refman/8.4/en/miscellaneous-functions.html
    * MariaDB —
      https://mariadb.com/docs/server/reference/data-types/string-data-types/uuid-data-type
    * SQLite — https://www.sqlite.org/datatype3.html
    * Snowflake — the type page and the release that introduced it:
      https://docs.snowflake.com/en/sql-reference/data-types-uuid
      https://docs.snowflake.com/en/release-notes/2026/10_2
    * BigQuery —
      https://cloud.google.com/bigquery/docs/reference/standard-sql/data-types
    * ClickHouse —
      https://clickhouse.com/docs/en/sql-reference/data-types/uuid
    * Firebird —
      https://www.firebirdsql.org/file/documentation/chunk/en/refdocs/fblangref50/fblangref50-functions-uuid.html
      https://www.firebirdsql.org/file/documentation/chunk/en/refdocs/fblangref50/fblangref50-datatypes-chartypes.html

    Generating a UUID is a separate concern and lives in the expression layer
    (:mod:`...expression.uuid`) — see ``UUIDSupport``. Storage says nothing
    about whether the database can produce a value: Oracle and Firebird both
    ship UUID *functions* and no UUID *type*.
    """

    name = "uuid"
