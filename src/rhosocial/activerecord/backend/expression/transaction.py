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

from typing import Any, Dict, Optional, TYPE_CHECKING

from .bases import BaseExpression, SQLQueryAndParams
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

    def get_params(self) -> Dict[str, Any]:
        """Get all parameters.

        Subclasses should override this method to return specific parameters.

        Returns:
            Dictionary containing all parameters.
        """
        return {}


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

    def __init__(self, dialect: "SQLDialectBase"):
        super().__init__(dialect)
        self._isolation_level: Optional[IsolationLevel] = None
        self._mode: Optional[TransactionMode] = None
        # PostgreSQL-specific: deferrable mode for SERIALIZABLE
        self._deferrable: Optional[bool] = None

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

    def deferrable(self, value: bool = True) -> "BeginTransactionExpression":
        """Set deferrable mode (PostgreSQL-specific).

        Deferrable mode is only valid for SERIALIZABLE isolation level
        and affects when constraint checking occurs.

        Args:
            value: True for DEFERRABLE, False for NOT DEFERRABLE.

        Returns:
            Self for method chaining.
        """
        self._deferrable = value
        return self

    def get_params(self) -> Dict[str, Any]:
        """Get all parameters.

        Returns:
            Dictionary containing isolation_level, mode, and deferrable.
        """
        params: Dict[str, Any] = {}
        if self._isolation_level is not None:
            params["isolation_level"] = self._isolation_level
        if self._mode is not None:
            params["mode"] = self._mode
        if self._deferrable is not None:
            params["deferrable"] = self._deferrable
        return params

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL, delegating to dialect's format_begin_transaction method."""
        return self._dialect.format_begin_transaction(self)


class CommitTransactionExpression(TransactionExpression):
    """Expression for COMMIT statement.

    Commits the current transaction, making all changes permanent.

    Usage:
        expr = CommitTransactionExpression(dialect)
        sql, params = expr.to_sql()
    """

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL, delegating to dialect's format_commit_transaction method."""
        return self._dialect.format_commit_transaction(self)


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

    def __init__(self, dialect: "SQLDialectBase"):
        super().__init__(dialect)
        self._savepoint: Optional[str] = None

    def to_savepoint(self, name: str) -> "RollbackTransactionExpression":
        """Rollback to a specific savepoint.

        Args:
            name: The name of the savepoint to rollback to.

        Returns:
            Self for method chaining.
        """
        self._savepoint = name
        return self

    def get_params(self) -> Dict[str, Any]:
        """Get all parameters.

        Returns:
            Dictionary containing savepoint name if set.
        """
        params: Dict[str, Any] = {}
        if self._savepoint is not None:
            params["savepoint"] = self._savepoint
        return params

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL, delegating to dialect's format_rollback_transaction method."""
        return self._dialect.format_rollback_transaction(self)


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

    def get_params(self) -> Dict[str, Any]:
        """Get all parameters.

        Returns:
            Dictionary containing the savepoint name.
        """
        return {"name": self._name}

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL, delegating to dialect's format_savepoint method."""
        return self._dialect.format_savepoint(self)


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

    def get_params(self) -> Dict[str, Any]:
        """Get all parameters.

        Returns:
            Dictionary containing the savepoint name.
        """
        return {"name": self._name}

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL, delegating to dialect's format_release_savepoint method."""
        return self._dialect.format_release_savepoint(self)


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

    def __init__(self, dialect: "SQLDialectBase"):
        super().__init__(dialect)
        self._isolation_level: Optional[IsolationLevel] = None
        self._mode: Optional[TransactionMode] = None
        self._session: bool = False
        self._deferrable: Optional[bool] = None

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

    def deferrable(self, value: bool = True) -> "SetTransactionExpression":
        """Set DEFERRABLE mode for SERIALIZABLE transactions (PostgreSQL specific).

        Args:
            value: Whether the transaction is deferrable.

        Returns:
            Self for method chaining.
        """
        self._deferrable = value
        return self

    def get_params(self) -> Dict[str, Any]:
        """Get all parameters.

        Returns:
            Dictionary containing isolation_level, mode, session, and deferrable.
        """
        params: Dict[str, Any] = {}
        if self._isolation_level is not None:
            params["isolation_level"] = self._isolation_level
        if self._mode is not None:
            params["mode"] = self._mode
        if self._session:
            params["session"] = self._session
        if self._deferrable is not None:
            params["deferrable"] = self._deferrable
        return params

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL, delegating to dialect's format_set_transaction method."""
        return self._dialect.format_set_transaction(self)
