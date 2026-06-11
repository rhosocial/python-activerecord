# src/rhosocial/activerecord/backend/dialect/mixins/transaction.py
from typing import Tuple


class TransactionControlMixin:
    """Mixin for transaction control statement formatting."""

    def format_begin_transaction(self, expr) -> Tuple[str, tuple]:
        return "BEGIN", ()

    def format_commit_transaction(self, expr) -> Tuple[str, tuple]:
        return "COMMIT", ()

    def format_rollback_transaction(self, expr) -> Tuple[str, tuple]:
        params = expr.get_params()
        savepoint = params.get("savepoint")
        if savepoint:
            return f"ROLLBACK TO SAVEPOINT {self.format_identifier(savepoint)}", ()
        return "ROLLBACK", ()

    def format_savepoint(self, expr) -> Tuple[str, tuple]:
        return f"SAVEPOINT {self.format_identifier(expr.name)}", ()

    def format_release_savepoint(self, expr) -> Tuple[str, tuple]:
        return f"RELEASE SAVEPOINT {self.format_identifier(expr.name)}", ()

    def format_set_transaction(self, expr) -> Tuple[str, tuple]:
        raise NotImplementedError(f"{self.name} dialect does not support SET TRANSACTION statement")
