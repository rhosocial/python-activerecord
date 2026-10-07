# src/rhosocial/activerecord/backend/impl/sqlite/mixins/transaction.py
"""
SQLite-specific Transaction implementation.

This module provides the SQLiteTransactionMixin class.
"""

from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.transaction import BeginTransactionExpression

class SQLiteTransactionMixin:
    """SQLite transaction control formatting."""

    def supports_transaction_mode(self) -> bool:
        """SQLite does not support READ ONLY transactions."""
        return False

    def supports_isolation_level_in_begin(self) -> bool:
        """SQLite does not support isolation level in BEGIN statement."""
        return False

    def supports_read_only_transaction(self) -> bool:
        """SQLite does not support READ ONLY transactions."""
        return False

    def supports_deferrable_transaction(self) -> bool:
        """SQLite does not support DEFERRABLE mode."""
        return False

    def supports_transaction_wait(self) -> bool:
        """SQLite has no WAIT / NO WAIT transaction clause."""
        return False

    def supports_savepoint(self) -> bool:
        """SQLite supports savepoints."""
        return True

    def format_begin_transaction(self, expr: "BeginTransactionExpression") -> Tuple[str, tuple]:
        """Format BEGIN TRANSACTION statement for SQLite.

        SQLite has no DEFERRABLE transaction mode; a requested spelling is
        refused rather than silently dropped.
        """
        from rhosocial.activerecord.backend.errors import UnsupportedTransactionModeError
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        from rhosocial.activerecord.backend.transaction import IsolationLevel, TransactionMode

        params = expr.get_params()
        if params.get("deferrable") or params.get("not_deferrable"):
            raise UnsupportedFeatureError(
                self.name, "DEFERRABLE transaction",
                "SQLite does not support DEFERRABLE transactions.",
            )
        if params.get("wait") or params.get("no_wait"):
            feature = "WAIT" if params.get("wait") else "NO WAIT"
            raise UnsupportedFeatureError(
                self.name, f"transaction {feature}",
                f"SQLite does not support the {feature} transaction clause.",
            )
        mode = params.get("mode")

        if mode == TransactionMode.READ_ONLY:
            raise UnsupportedTransactionModeError(
                feature="READ ONLY transactions",
                backend="SQLite",
                message="Consider using a separate read-only database connection.",
            )

        begin_type = params.get("begin_type")
        if begin_type is not None:
            valid_types = ("DEFERRED", "IMMEDIATE", "EXCLUSIVE")
            bt_upper = begin_type.upper()
            if bt_upper not in valid_types:
                raise ValueError(f"Invalid SQLite begin type: {begin_type}. Must be one of {valid_types}")
            return f"BEGIN {bt_upper} TRANSACTION", ()

        isolation = params.get("isolation_level")

        if isolation == IsolationLevel.READ_UNCOMMITTED:
            return "BEGIN DEFERRED TRANSACTION", ()
        else:
            return "BEGIN IMMEDIATE TRANSACTION", ()


# =============================================================================
# SQLiteFunctionMixin — function support detection
# =============================================================================

