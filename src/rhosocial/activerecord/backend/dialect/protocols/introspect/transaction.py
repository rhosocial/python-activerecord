# src/rhosocial/activerecord/backend/dialect/protocols/transactioncontrolsupport.py
"""TransactionControlSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression import (
        BeginTransactionExpression,
        CommitTransactionExpression,
        ReleaseSavepointExpression,
        RollbackTransactionExpression,
        SavepointExpression,
        SetTransactionExpression,
    )


@runtime_checkable
class TransactionControlSupport(Protocol):
    """
    Protocol for transaction control statement support.

    This protocol defines methods that dialects implement to declare which
    transaction control features they support. Dialects also provide format_*
    methods to generate database-specific SQL for transaction control statements.

    Layer responsibilities:
    - Dialect layer: Declares capabilities (supports_*) and formats SQL (format_*)
    - Backend layer: Executes SQL and manages transaction state

    Expression pattern:
    - Expressions collect parameters (isolation_level, mode, etc.)
    - Dialects generate SQL from expression parameters
    - Backends execute SQL and manage state

    Database Differences:
    - SQLite: Does not support READ ONLY transactions, uses PRAGMA for isolation
    - MySQL: Uses SET TRANSACTION before START TRANSACTION, supports READ ONLY (5.6.5+)
    - PostgreSQL: Full inline syntax (BEGIN ISOLATION LEVEL ... READ ONLY ... DEFERRABLE)
    """

    # ========== Capability Detection ==========

    def supports_transaction_mode(self) -> bool:
        """Whether transaction access mode (READ ONLY/READ WRITE) is supported.

        - PostgreSQL: True
        - MySQL: True (5.6.5+)
        - SQLite: False
        """
        ...  # pragma: no cover

    def supports_isolation_level_in_begin(self) -> bool:
        """Whether isolation level can be specified in BEGIN statement.

        - PostgreSQL: True (BEGIN ISOLATION LEVEL ...)
        - MySQL: False (uses SET TRANSACTION before START TRANSACTION)
        - SQLite: False (uses PRAGMA read_uncommitted)
        """
        ...  # pragma: no cover

    def supports_read_only_transaction(self) -> bool:
        """Whether READ ONLY transactions are supported.

        - PostgreSQL: True
        - MySQL: True (START TRANSACTION READ ONLY, 5.6.5+)
        - SQLite: False
        """
        ...  # pragma: no cover

    def supports_deferrable_transaction(self) -> bool:
        """Whether DEFERRABLE mode is supported.

        PostgreSQL-specific feature for SERIALIZABLE transactions.
        """
        ...  # pragma: no cover

    def supports_transaction_wait(self) -> bool:
        """Whether the transaction lock-wait clause (``WAIT`` / ``NO WAIT``) is supported.

        Firebird-specific: ``SET TRANSACTION ... [WAIT | NO WAIT]``.  The probe
        answers the capability question; ``wait`` / ``no_wait`` on
        :class:`~....expression.transaction.BeginTransactionExpression` and
        :class:`~....expression.transaction.SetTransactionExpression` select
        the spelling.  Defaults to False for dialects whose grammar has no
        such clause.
        """
        ...  # pragma: no cover

    def supports_savepoint(self) -> bool:
        """Whether savepoints are supported.

        All major databases support savepoints.
        """
        ...  # pragma: no cover

    # ========== SQL Formatting ==========

    def format_begin_transaction(self, expr: "BeginTransactionExpression") -> Tuple[str, tuple]:
        """
        Format BEGIN TRANSACTION statement.

        Args:
            expr: BeginTransactionExpression with isolation level and mode.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Important:
            MUST return a SINGLE SQL statement. Multiple statements separated by
            semicolons are NOT allowed because backend.execute() only supports
            single-statement execution. For databases that require multiple
            statements (e.g., MySQL needs SET TRANSACTION before START TRANSACTION),
            the TransactionManager subclass should override _do_begin() to execute
            them separately.

        Note:
            - MySQL: Returns "START TRANSACTION" only; SET TRANSACTION is handled
              by MySQLTransactionManager._do_begin() separately.
            - PostgreSQL: Returns "BEGIN ISOLATION LEVEL ... READ ONLY ..." as single statement.
            - SQLite: Returns "BEGIN [DEFERRED|IMMEDIATE] TRANSACTION" as single statement.
        """
        ...  # pragma: no cover

    def format_commit_transaction(self, expr: "CommitTransactionExpression") -> Tuple[str, tuple]:
        """
        Format COMMIT statement.

        Args:
            expr: CommitTransactionExpression.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_rollback_transaction(self, expr: "RollbackTransactionExpression") -> Tuple[str, tuple]:
        """
        Format ROLLBACK statement.

        Args:
            expr: RollbackTransactionExpression with optional savepoint.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_savepoint(self, expr: "SavepointExpression") -> Tuple[str, tuple]:
        """
        Format SAVEPOINT statement.

        Args:
            expr: SavepointExpression with savepoint name.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_release_savepoint(self, expr: "ReleaseSavepointExpression") -> Tuple[str, tuple]:
        """
        Format RELEASE SAVEPOINT statement.

        Args:
            expr: ReleaseSavepointExpression with savepoint name.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_set_transaction(self, expr: "SetTransactionExpression") -> Tuple[str, tuple]:
        """
        Format SET TRANSACTION statement.

        Used primarily by MySQL to set isolation level before START TRANSACTION.

        Args:
            expr: SetTransactionExpression with isolation level and/or mode.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover
