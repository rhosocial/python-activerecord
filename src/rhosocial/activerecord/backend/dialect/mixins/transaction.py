# src/rhosocial/activerecord/backend/dialect/mixins/transaction.py
"""Transaction control statement formatting for the dialect layer.

Provides default SQL rendering for BEGIN, COMMIT, ROLLBACK, savepoints, and
SET TRANSACTION statements.
"""
from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ...expression.transaction import (
        BeginTransactionStatement,
        CommitStatement,
        ReleaseSavepointStatement,
        RollbackStatement,
        SavepointStatement,
        SetTransactionExpression,
    )


class TransactionControlMixin:
    """Mixin providing transaction control statement formatting."""

    def format_begin_transaction_statement(self, expr: "BeginTransactionStatement") -> Tuple[str, tuple]:
        """Format a BEGIN transaction statement.

        Args:
            expr: Begin transaction expression.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return "BEGIN", ()

    def format_commit_transaction_statement(self, expr: "CommitStatement") -> Tuple[str, tuple]:
        """Format a COMMIT transaction statement.

        Args:
            expr: Commit transaction expression.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return "COMMIT", ()

    def format_rollback_transaction_statement(self, expr: "RollbackStatement") -> Tuple[str, tuple]:
        """Format a ROLLBACK statement, optionally to a savepoint.

        Args:
            expr: Rollback expression exposing an optional ``savepoint``
                parameter.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        params = expr.get_params()
        savepoint = params.get("savepoint")
        if savepoint:
            return f"ROLLBACK TO SAVEPOINT {self.format_identifier(savepoint)}", ()
        return "ROLLBACK", ()

    def format_savepoint_statement(self, expr: "SavepointStatement") -> Tuple[str, tuple]:
        """Format a SAVEPOINT statement.

        Args:
            expr: Savepoint expression exposing ``name``.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return f"SAVEPOINT {self.format_identifier(expr.name)}", ()

    def format_release_savepoint_statement(self, expr: "ReleaseSavepointStatement") -> Tuple[str, tuple]:
        """Format a RELEASE SAVEPOINT statement.

        Args:
            expr: Release savepoint expression exposing ``name``.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return f"RELEASE SAVEPOINT {self.format_identifier(expr.name)}", ()

    def format_set_transaction(self, expr: "SetTransactionExpression") -> Tuple[str, tuple]:
        """Format a SET TRANSACTION statement.

        Args:
            expr: Set transaction expression.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            NotImplementedError: Always, unless a dialect overrides this.
        """
        raise NotImplementedError(f"{self.name} dialect does not support SET TRANSACTION statement")
