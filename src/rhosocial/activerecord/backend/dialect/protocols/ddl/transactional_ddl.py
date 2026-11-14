# src/rhosocial/activerecord/backend/dialect/protocols/ddl/transactional_ddl.py
"""TransactionalDDLSupport.

Whether a backend's DDL statements can participate in a transaction: commit
them together, or roll them back together.  MySQL/MariaDB commit each DDL
statement implicitly, so a multi-step migration cannot be atomic there;
PostgreSQL, SQLite and Firebird can hold DDL inside a transaction.

There is no safe default: a dialect must answer for itself, and a plan that
needs atomicity must ask rather than assume.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class TransactionalDDLSupport(Protocol):
    """Whether the engine's DDL statements are transactional."""

    def supports_transactional_ddl(self) -> bool:
        """``True`` when DDL inside a transaction commits or rolls back with it."""
        ...  # pragma: no cover
