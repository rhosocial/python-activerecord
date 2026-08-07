# src/rhosocial/activerecord/backend/dialect/mixins/transaction.py
from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ...expression.transaction import (
        BeginTransactionExpression,
        CommitTransactionExpression,
        ReleaseSavepointExpression,
        RollbackTransactionExpression,
        SavepointExpression,
        SetTransactionExpression,
    )


class TransactionControlMixin:
    """Mixin for transaction control statement formatting."""

    def format_begin_transaction(self, expr: "BeginTransactionExpression") -> Tuple[str, tuple]:
        return "BEGIN", ()

    def format_commit_transaction(self, expr: "CommitTransactionExpression") -> Tuple[str, tuple]:
        return "COMMIT", ()

    def format_rollback_transaction(self, expr: "RollbackTransactionExpression") -> Tuple[str, tuple]:
        params = expr.get_params()
        savepoint = params.get("savepoint")
        if savepoint:
            return f"ROLLBACK TO SAVEPOINT {self.format_identifier(savepoint)}", ()
        return "ROLLBACK", ()

    def format_savepoint(self, expr: "SavepointExpression") -> Tuple[str, tuple]:
        return f"SAVEPOINT {self.format_identifier(expr.name)}", ()

    def format_release_savepoint(self, expr: "ReleaseSavepointExpression") -> Tuple[str, tuple]:
        return f"RELEASE SAVEPOINT {self.format_identifier(expr.name)}", ()

    def format_set_transaction(self, expr: "SetTransactionExpression") -> Tuple[str, tuple]:
        raise NotImplementedError(f"{self.name} dialect does not support SET TRANSACTION statement")
