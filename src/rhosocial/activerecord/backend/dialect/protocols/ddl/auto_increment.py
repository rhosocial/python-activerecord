# src/rhosocial/activerecord/backend/dialect/protocols/autoincrementsupport.py
"""AutoIncrementSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Protocol, runtime_checkable

@runtime_checkable
class AutoIncrementSupport(Protocol):
    """
    Protocol for AUTO_INCREMENT / IDENTITY column support.

    This is a *DDL column-definition* capability: the auto-increment attribute
    is declared on a column in CREATE TABLE (e.g. MySQL ``AUTO_INCREMENT``,
    SQLite ``AUTOINCREMENT``, SQL-standard ``GENERATED ... AS IDENTITY``) and
    rendered by the DDLColumnMixin family. It is orthogonal to RETURNING
    support — MySQL generates keys server-side but has no RETURNING (values
    are fetched via LAST_INSERT_ID()), while PostgreSQL offers both.

    Support varies:
    - MySQL: AUTO_INCREMENT on integer key columns
    - SQLite: AUTOINCREMENT keyword (ROWID aliasing)
    - PostgreSQL: GENERATED ALWAYS AS IDENTITY / SERIAL
    - SQL Server: IDENTITY(seed, increment)
    - ClickHouse: not supported (client-side key generation required)
    """

    def supports_auto_increment(self) -> bool:
        """Whether AUTO_INCREMENT/IDENTITY column attributes are supported."""
        ...  # pragma: no cover
