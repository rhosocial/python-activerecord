# src/rhosocial/activerecord/backend/expression/transaction.py
"""
Transaction control expression classes.

This module defines expression classes that collect parameters for
transaction control SQL statements (BEGIN, COMMIT, ROLLBACK, SAVEPOINT).
Expressions separate parameter collection from SQL generation:
- Expressions collect parameters (isolation level, access mode, etc.)
- Dialect's format_* methods generate SQL from expression parameters
- Backends execute SQL and manage transaction state

Expression classes inherit from BaseExpression and implement to_sql(),
delegating SQL generation to the dialect's corresponding format_* method.
"""

from typing import Optional, TYPE_CHECKING

from .bases import BaseExpression
from ..transaction import IsolationLevel, TransactionMode

if TYPE_CHECKING:
    from ..dialect import SQLDialectBase


class TransactionStatement(BaseExpression):
    """Base class for transaction statements.

    All transaction statements inherit from this class and provide
    fluent API for setting parameters. Transaction statements hold
    a dialect reference and delegate SQL generation to the corresponding
    dialect via the to_sql() method.
    """

    def __init__(self, dialect: "SQLDialectBase"):
        super().__init__(dialect)


class BeginTransactionStatement(TransactionStatement):
    """BEGIN TRANSACTION statement.

    Collects parameters for starting a new transaction with optional
    isolation level and access mode settings.

    Usage:
        expr = BeginTransactionStatement(dialect)
        expr.with_isolation_level(IsolationLevel.SERIALIZABLE)
        expr.read_only()
        sql, params = expr.to_sql()
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        *,
        isolation_level: Optional[IsolationLevel] = None,
        mode: Optional[TransactionMode] = None,
        deferrable: bool = False,
        not_deferrable: bool = False,
        wait: bool = False,
        no_wait: bool = False,
        begin_type: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.require_exclusive_options(deferrable, not_deferrable, "deferrable", "not_deferrable")
        self.require_exclusive_options(wait, no_wait, "wait", "no_wait")
        self.isolation_level: Optional[IsolationLevel] = isolation_level
        self.mode: Optional[TransactionMode] = mode
        # PostgreSQL-specific: deferrable mode for SERIALIZABLE transactions.
        # [NOT] DEFERRABLE is an independent transaction mode in the grammar;
        # it is rendered whenever requested, not only alongside SERIALIZABLE.
        self.deferrable: bool = deferrable
        self.not_deferrable: bool = not_deferrable
        # Firebird-specific: the lock-wait clause. WAIT and NO WAIT are two
        # spellings with one parameter each; neither set renders nothing.
        self.wait: bool = wait
        self.no_wait: bool = no_wait
        # SQLite-specific: BEGIN transaction type (DEFERRED|IMMEDIATE|EXCLUSIVE)
        self.begin_type: Optional[str] = begin_type

    def with_isolation_level(self, level: IsolationLevel) -> "BeginTransactionStatement":
        """Set the transaction isolation level.

        Args:
            level: The isolation level (READ_UNCOMMITTED, READ_COMMITTED,
                   REPEATABLE_READ, or SERIALIZABLE).

        Returns:
            Self for method chaining.
        """
        self.isolation_level = level
        return self

    def read_only(self) -> "BeginTransactionStatement":
        """Set transaction to read-only mode.

        In read-only mode, the transaction cannot modify data.
        Not all databases support this mode.

        Returns:
            Self for method chaining.
        """
        self.mode = TransactionMode.READ_ONLY
        return self

    def read_write(self) -> "BeginTransactionStatement":
        """Set transaction to read-write mode (default).

        In read-write mode, the transaction can read and modify data.

        Returns:
            Self for method chaining.
        """
        self.mode = TransactionMode.READ_WRITE
        return self

    def with_deferrable(self) -> "BeginTransactionStatement":
        """Set deferrable mode (PostgreSQL-specific).

        Deferrable mode is only *effective* for SERIALIZABLE transactions, but
        ``[NOT] DEFERRABLE`` is an independent transaction mode in the grammar:
        the clause is rendered whenever it is requested.

        Returns:
            Self for method chaining.
        """
        self.deferrable = True
        self.not_deferrable = False
        return self

    def with_not_deferrable(self) -> "BeginTransactionStatement":
        """Set NOT DEFERRABLE mode (PostgreSQL-specific).

        Returns:
            Self for method chaining.
        """
        self.not_deferrable = True
        self.deferrable = False
        return self

    def with_wait(self) -> "BeginTransactionStatement":
        """Set the lock-wait clause to WAIT (Firebird-specific).

        Returns:
            Self for method chaining.
        """
        self.wait = True
        self.no_wait = False
        return self

    def with_no_wait(self) -> "BeginTransactionStatement":
        """Set the lock-wait clause to NO WAIT (Firebird-specific).

        Returns:
            Self for method chaining.
        """
        self.no_wait = True
        self.wait = False
        return self

    def with_begin_type(self, begin_type: str) -> "BeginTransactionStatement":
        """Set the BEGIN transaction type (SQLite-specific).

        SQLite supports three transaction types:
        - DEFERRED: Does not acquire locks until first read/write
        - IMMEDIATE: Acquires RESERVED lock on BEGIN
        - EXCLUSIVE: Acquires EXCLUSIVE lock on BEGIN

        Args:
            begin_type: The transaction type string ("DEFERRED", "IMMEDIATE", or "EXCLUSIVE").

        Returns:
            Self for method chaining.
        """
        self.begin_type = begin_type
        return self

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_begin_transaction_statement"


class CommitStatement(TransactionStatement):
    """Expression for COMMIT statement.

    Commits the current transaction, making all changes permanent.

    Usage:
        expr = CommitStatement(dialect)
        sql, params = expr.to_sql()
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_commit_statement"


class RollbackStatement(TransactionStatement):
    """Expression for ROLLBACK statement.

    Rolls back the current transaction, discarding all changes.
    Can optionally rollback to a specific savepoint.

    Usage:
        # Full rollback
        expr = RollbackStatement(dialect)
        sql, params = expr.to_sql()

        # Rollback to savepoint
        expr = RollbackStatement(dialect)
        expr.to_savepoint("my_savepoint")
        sql, params = expr.to_sql()
    """

    def __init__(self, dialect: "SQLDialectBase", *, savepoint: Optional[str] = None):
        super().__init__(dialect)
        self.savepoint: Optional[str] = savepoint

    def to_savepoint(self, name: str) -> "RollbackStatement":
        """Rollback to a specific savepoint.

        Args:
            name: The name of the savepoint to rollback to.

        Returns:
            Self for method chaining.
        """
        self.savepoint = name
        return self

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_rollback_statement"


class SavepointStatement(TransactionStatement):
    """Expression for SAVEPOINT statement.

    Creates a savepoint within the current transaction.
    Savepoints allow partial rollback of transactions.

    Usage:
        expr = SavepointStatement(dialect, "my_savepoint")
        sql, params = expr.to_sql()
    """

    def __init__(self, dialect: "SQLDialectBase", name: str):
        super().__init__(dialect)
        self._name = name

    @property
    def name(self) -> str:
        """Get the savepoint name."""
        return self._name

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_savepoint_statement"


class ReleaseSavepointStatement(TransactionStatement):
    """Expression for RELEASE SAVEPOINT statement.

    Releases a savepoint, keeping the changes made after it.
    The savepoint can no longer be used for rollback.

    Usage:
        expr = ReleaseSavepointStatement(dialect, "my_savepoint")
        sql, params = expr.to_sql()
    """

    def __init__(self, dialect: "SQLDialectBase", name: str):
        super().__init__(dialect)
        self._name = name

    @property
    def name(self) -> str:
        """Get the savepoint name."""
        return self._name

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_release_savepoint_statement"


class SetTransactionStatement(TransactionStatement):
    """SET TRANSACTION statement.

    Sets transaction characteristics for the next transaction.
    Used primarily in MySQL where isolation level must be set
    before starting the transaction.

    Usage:
        expr = SetTransactionStatement(dialect)
        expr.with_isolation_level(IsolationLevel.READ_COMMITTED)
        expr.read_only()
        sql, params = expr.to_sql()
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        *,
        isolation_level: Optional[IsolationLevel] = None,
        mode: Optional[TransactionMode] = None,
        session: bool = False,
        deferrable: bool = False,
        not_deferrable: bool = False,
        wait: bool = False,
        no_wait: bool = False,
    ):
        super().__init__(dialect)
        self.require_exclusive_options(deferrable, not_deferrable, "deferrable", "not_deferrable")
        self.require_exclusive_options(wait, no_wait, "wait", "no_wait")
        self.isolation_level: Optional[IsolationLevel] = isolation_level
        self.mode: Optional[TransactionMode] = mode
        self.session: bool = session
        self.deferrable: bool = deferrable
        self.not_deferrable: bool = not_deferrable
        self.wait: bool = wait
        self.no_wait: bool = no_wait

    def with_isolation_level(self, level: IsolationLevel) -> "SetTransactionStatement":
        """Set the transaction isolation level.

        Args:
            level: The isolation level to set.

        Returns:
            Self for method chaining.
        """
        self.isolation_level = level
        return self

    def read_only(self) -> "SetTransactionStatement":
        """Set transaction to read-only mode.

        Returns:
            Self for method chaining.
        """
        self.mode = TransactionMode.READ_ONLY
        return self

    def read_write(self) -> "SetTransactionStatement":
        """Set transaction to read-write mode.

        Returns:
            Self for method chaining.
        """
        self.mode = TransactionMode.READ_WRITE
        return self

    def with_session(self, value: bool = True) -> "SetTransactionStatement":
        """Set whether to use SESSION CHARACTERISTICS (PostgreSQL specific).

        When True, sets transaction characteristics for all subsequent
        transactions in the current session.

        Args:
            value: Whether to set session characteristics.

        Returns:
            Self for method chaining.
        """
        self.session = value
        return self

    def with_deferrable(self) -> "SetTransactionStatement":
        """Set DEFERRABLE mode for SERIALIZABLE transactions (PostgreSQL specific).

        Returns:
            Self for method chaining.
        """
        self.deferrable = True
        self.not_deferrable = False
        return self

    def with_not_deferrable(self) -> "SetTransactionStatement":
        """Set NOT DEFERRABLE mode for transactions (PostgreSQL specific).

        Returns:
            Self for method chaining.
        """
        self.not_deferrable = True
        self.deferrable = False
        return self

    def with_wait(self) -> "SetTransactionStatement":
        """Set the lock-wait clause to WAIT (Firebird-specific).

        Returns:
            Self for method chaining.
        """
        self.wait = True
        self.no_wait = False
        return self

    def with_no_wait(self) -> "SetTransactionStatement":
        """Set the lock-wait clause to NO WAIT (Firebird-specific).

        Returns:
            Self for method chaining.
        """
        self.no_wait = True
        self.wait = False
        return self

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_set_transaction_statement"
