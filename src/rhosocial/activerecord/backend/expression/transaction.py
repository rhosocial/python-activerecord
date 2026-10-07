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


class TransactionExpression(BaseExpression):
    """Base class for transaction control expressions.

    All transaction expressions inherit from this class and provide
    fluent API for setting parameters. Transaction expressions hold
    a dialect reference and delegate SQL generation to the corresponding
    dialect via the to_sql() method.
    """

    def __init__(self, dialect: "SQLDialectBase"):
        super().__init__(dialect)


class BeginTransactionExpression(TransactionExpression):
    """Expression for BEGIN TRANSACTION statement.

    Collects parameters for starting a new transaction with optional
    isolation level and access mode settings.

    Usage:
        expr = BeginTransactionExpression(dialect)
        expr.isolation_level(IsolationLevel.SERIALIZABLE)
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
        begin_type: Optional[str] = None,
    ):
        super().__init__(dialect)
        if deferrable and not_deferrable:
            raise ValueError("deferrable and not_deferrable are mutually exclusive options")
        self._isolation_level: Optional[IsolationLevel] = isolation_level
        self._mode: Optional[TransactionMode] = mode
        # PostgreSQL-specific: deferrable mode for SERIALIZABLE transactions.
        # [NOT] DEFERRABLE is an independent transaction mode in the grammar;
        # it is rendered whenever requested, not only alongside SERIALIZABLE.
        self._deferrable: bool = deferrable
        self._not_deferrable: bool = not_deferrable
        # SQLite-specific: BEGIN transaction type (DEFERRED|IMMEDIATE|EXCLUSIVE)
        self._begin_type: Optional[str] = begin_type

    def isolation_level(self, level: IsolationLevel) -> "BeginTransactionExpression":
        """Set the transaction isolation level.

        Args:
            level: The isolation level (READ_UNCOMMITTED, READ_COMMITTED,
                   REPEATABLE_READ, or SERIALIZABLE).

        Returns:
            Self for method chaining.
        """
        self._isolation_level = level
        return self

    def read_only(self) -> "BeginTransactionExpression":
        """Set transaction to read-only mode.

        In read-only mode, the transaction cannot modify data.
        Not all databases support this mode.

        Returns:
            Self for method chaining.
        """
        self._mode = TransactionMode.READ_ONLY
        return self

    def read_write(self) -> "BeginTransactionExpression":
        """Set transaction to read-write mode (default).

        In read-write mode, the transaction can read and modify data.

        Returns:
            Self for method chaining.
        """
        self._mode = TransactionMode.READ_WRITE
        return self

    def deferrable(self) -> "BeginTransactionExpression":
        """Set deferrable mode (PostgreSQL-specific).

        Deferrable mode is only *effective* for SERIALIZABLE transactions, but
        ``[NOT] DEFERRABLE`` is an independent transaction mode in the grammar:
        the clause is rendered whenever it is requested.

        Returns:
            Self for method chaining.
        """
        self._deferrable = True
        self._not_deferrable = False
        return self

    def not_deferrable(self) -> "BeginTransactionExpression":
        """Set NOT DEFERRABLE mode (PostgreSQL-specific).

        Returns:
            Self for method chaining.
        """
        self._not_deferrable = True
        self._deferrable = False
        return self

    def begin_type(self, begin_type: str) -> "BeginTransactionExpression":
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
        self._begin_type = begin_type
        return self

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_begin_transaction"


class CommitTransactionExpression(TransactionExpression):
    """Expression for COMMIT statement.

    Commits the current transaction, making all changes permanent.

    Usage:
        expr = CommitTransactionExpression(dialect)
        sql, params = expr.to_sql()
    """

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_commit_transaction"


class RollbackTransactionExpression(TransactionExpression):
    """Expression for ROLLBACK statement.

    Rolls back the current transaction, discarding all changes.
    Can optionally rollback to a specific savepoint.

    Usage:
        # Full rollback
        expr = RollbackTransactionExpression(dialect)
        sql, params = expr.to_sql()

        # Rollback to savepoint
        expr = RollbackTransactionExpression(dialect)
        expr.to_savepoint("my_savepoint")
        sql, params = expr.to_sql()
    """

    def __init__(self, dialect: "SQLDialectBase", *, savepoint: Optional[str] = None):
        super().__init__(dialect)
        self._savepoint: Optional[str] = savepoint

    def to_savepoint(self, name: str) -> "RollbackTransactionExpression":
        """Rollback to a specific savepoint.

        Args:
            name: The name of the savepoint to rollback to.

        Returns:
            Self for method chaining.
        """
        self._savepoint = name
        return self

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_rollback_transaction"


class SavepointExpression(TransactionExpression):
    """Expression for SAVEPOINT statement.

    Creates a savepoint within the current transaction.
    Savepoints allow partial rollback of transactions.

    Usage:
        expr = SavepointExpression(dialect, "my_savepoint")
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
        return "format_savepoint"


class ReleaseSavepointExpression(TransactionExpression):
    """Expression for RELEASE SAVEPOINT statement.

    Releases a savepoint, keeping the changes made after it.
    The savepoint can no longer be used for rollback.

    Usage:
        expr = ReleaseSavepointExpression(dialect, "my_savepoint")
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
        return "format_release_savepoint"


class SetTransactionExpression(TransactionExpression):
    """Expression for SET TRANSACTION statement.

    Sets transaction characteristics for the next transaction.
    Used primarily in MySQL where isolation level must be set
    before starting the transaction.

    Usage:
        expr = SetTransactionExpression(dialect)
        expr.isolation_level(IsolationLevel.READ_COMMITTED)
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
    ):
        super().__init__(dialect)
        if deferrable and not_deferrable:
            raise ValueError("deferrable and not_deferrable are mutually exclusive options")
        self._isolation_level: Optional[IsolationLevel] = isolation_level
        self._mode: Optional[TransactionMode] = mode
        self._session: bool = session
        self._deferrable: bool = deferrable
        self._not_deferrable: bool = not_deferrable

    def isolation_level(self, level: IsolationLevel) -> "SetTransactionExpression":
        """Set the transaction isolation level.

        Args:
            level: The isolation level to set.

        Returns:
            Self for method chaining.
        """
        self._isolation_level = level
        return self

    def read_only(self) -> "SetTransactionExpression":
        """Set transaction to read-only mode.

        Returns:
            Self for method chaining.
        """
        self._mode = TransactionMode.READ_ONLY
        return self

    def read_write(self) -> "SetTransactionExpression":
        """Set transaction to read-write mode.

        Returns:
            Self for method chaining.
        """
        self._mode = TransactionMode.READ_WRITE
        return self

    def session(self, value: bool = True) -> "SetTransactionExpression":
        """Set whether to use SESSION CHARACTERISTICS (PostgreSQL specific).

        When True, sets transaction characteristics for all subsequent
        transactions in the current session.

        Args:
            value: Whether to set session characteristics.

        Returns:
            Self for method chaining.
        """
        self._session = value
        return self

    def deferrable(self) -> "SetTransactionExpression":
        """Set DEFERRABLE mode for SERIALIZABLE transactions (PostgreSQL specific).

        Returns:
            Self for method chaining.
        """
        self._deferrable = True
        self._not_deferrable = False
        return self

    def not_deferrable(self) -> "SetTransactionExpression":
        """Set NOT DEFERRABLE mode for transactions (PostgreSQL specific).

        Returns:
            Self for method chaining.
        """
        self._not_deferrable = True
        self._deferrable = False
        return self

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_set_transaction"
