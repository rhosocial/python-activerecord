# .../mixins/locking_mixin.py
"""Per-feature mixin for LockingSupport. Members/order/signature mirror the protocol."""

from typing import TYPE_CHECKING, Any, List, Tuple
from ...expression.bases import ToSQLProtocol
from ...expression.query_parts import SortDirection

class LockingMixin:
    def supports_for_update(self) -> bool:
            """Whether row-level locking with FOR UPDATE is supported (defaults to False)."""
            return False

    def supports_for_update_skip_locked(self) -> bool:
            """Whether FOR UPDATE SKIP LOCKED is supported. Defaults to False."""
            return False

    def supports_for_update_nowait(self) -> bool:
            """Whether FOR UPDATE NOWAIT is supported. Defaults to False.

            A separate probe from ``supports_for_update_skip_locked`` because the
            two do not travel together: Oracle spells the pair ``NOWAIT`` /
            ``SKIP LOCKED``, PostgreSQL since 9.5 accepts both but older versions
            only ``SKIP LOCKED``, and SQLite accepts neither. A dialect that has one
            has no reason to have the other, so a shared probe would have to be
            answered ``True`` for a dialect that would only reject half the requests
            it admitted.
            """
            return False

    def supports_for_share(self) -> bool:
            """Whether the FOR SHARE lock strength is supported. Defaults to False."""
            return False

    def supports_for_no_key_update(self) -> bool:
            """Whether FOR NO KEY UPDATE is supported. Defaults to False."""
            return False

    def supports_for_key_share(self) -> bool:
            """Whether FOR KEY SHARE is supported. Defaults to False."""
            return False

    def supports_lock_in_share_mode(self) -> bool:
            """Whether the legacy LOCK IN SHARE MODE syntax is supported."""
            return False

    def format_for_update_clause(self, expr: "ForUpdateClause") -> Tuple[str, tuple]:
            """Format a FOR UPDATE / FOR SHARE expr into dialect SQL.

            Args:
                expr: The ForUpdateClause node carrying the lock ``strength``,
                    optional OF columns and the NOWAIT / SKIP LOCKED flags.

            Returns:
                Tuple of (SQL string, parameters tuple) for the expr.

            Raises:
                UnsupportedFeatureError: If the requested lock strength or option
                    is not supported by the dialect.
            """
            from ...expression.query_parts import LockStrength
            from ..exceptions import UnsupportedFeatureError

            all_params = []
            strength = expr.strength

            if strength == LockStrength.NO_KEY_UPDATE and not self.supports_for_no_key_update():
                raise UnsupportedFeatureError(self.name, "FOR NO KEY UPDATE")
            if strength == LockStrength.SHARE and not self.supports_for_share():
                raise UnsupportedFeatureError(self.name, "FOR SHARE")
            if strength == LockStrength.KEY_SHARE and not self.supports_for_key_share():
                raise UnsupportedFeatureError(self.name, "FOR KEY SHARE")
            if strength == LockStrength.LOCK_IN_SHARE_MODE and not self.supports_lock_in_share_mode():
                raise UnsupportedFeatureError(self.name, "LOCK IN SHARE MODE")

            # The expr text comes from the enum's phrase, so the wire value stays the
            # language-neutral strength word.
            sql_parts = [strength.phrase]

            # Handle OF columns if specified
            if expr.of_columns:
                of_parts = []
                for col in expr.of_columns:
                    if isinstance(col, str):
                        of_parts.append(self.format_identifier(col))
                    elif isinstance(col, ToSQLProtocol):  # BaseExpression
                        col_sql, col_params = col.to_sql()
                        of_parts.append(col_sql)
                        all_params.extend(col_params)
                if of_parts:
                    sql_parts.append(f"OF {', '.join(of_parts)}")

            # Both wait modifiers are gated. Rendering either one for a dialect that
            # does not have it produces a statement the database rejects at
            # execution time, which is a worse answer than refusing here: the
            # failure arrives with the caller's data already in flight (§6).
            if expr.nowait:
                if not self.supports_for_update_nowait():
                    raise UnsupportedFeatureError(self.name, "NOWAIT")
                sql_parts.append("NOWAIT")
            elif expr.skip_locked:
                if not self.supports_for_update_skip_locked():
                    raise UnsupportedFeatureError(self.name, "SKIP LOCKED")
                sql_parts.append("SKIP LOCKED")

            return " ".join(sql_parts), tuple(all_params)
