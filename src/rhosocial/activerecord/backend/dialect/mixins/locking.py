# src/rhosocial/activerecord/backend/dialect/mixins/locking.py
"""Dialect mixin for row-locking clauses.

Formats FOR UPDATE / FOR SHARE clauses, including the typed lock strength,
optional OF columns and the NOWAIT / SKIP LOCKED modifiers.
"""
from typing import Tuple, TYPE_CHECKING

from ...expression.bases import ToSQLProtocol

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.query_parts import ForUpdateClause


class LockingMixin:
    """Mixin for locking clause support.

    The lock strength is carried by the :class:`ForUpdateClause` as a typed
    field. Dialects advertise the strengths and options they support through
    the ``supports_*`` probes and override :meth:`format_for_update_clause`
    when their syntax differs.
    """

    def supports_for_update_skip_locked(self) -> bool:
        """Whether FOR UPDATE SKIP LOCKED is supported. Defaults to False."""
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

    def format_for_update_clause(self, clause: "ForUpdateClause") -> Tuple[str, tuple]:
        """Format a FOR UPDATE / FOR SHARE clause into dialect SQL.

        Args:
            clause: The ForUpdateClause node carrying the lock ``strength``,
                optional OF columns and the NOWAIT / SKIP LOCKED flags.

        Returns:
            Tuple of (SQL string, parameters tuple) for the clause.

        Raises:
            UnsupportedFeatureError: If the requested lock strength or option
                is not supported by the dialect.
        """
        from ..exceptions import UnsupportedFeatureError
        from ...expression.query_parts import LockStrength

        all_params = []
        strength = clause.strength

        if strength == LockStrength.NO_KEY_UPDATE and not self.supports_for_no_key_update():
            raise UnsupportedFeatureError(self.name, "FOR NO KEY UPDATE")
        if strength == LockStrength.SHARE and not self.supports_for_share():
            raise UnsupportedFeatureError(self.name, "FOR SHARE")
        if strength == LockStrength.KEY_SHARE and not self.supports_for_key_share():
            raise UnsupportedFeatureError(self.name, "FOR KEY SHARE")
        if strength == LockStrength.LOCK_IN_SHARE_MODE and not self.supports_lock_in_share_mode():
            raise UnsupportedFeatureError(self.name, "LOCK IN SHARE MODE")

        sql_parts = [strength.value]

        # Handle OF columns if specified
        if clause.of_columns:
            of_parts = []
            for col in clause.of_columns:
                if isinstance(col, str):
                    of_parts.append(self.format_identifier(col))
                elif isinstance(col, ToSQLProtocol):  # BaseExpression
                    col_sql, col_params = col.to_sql()
                    of_parts.append(col_sql)
                    all_params.extend(col_params)
            if of_parts:
                sql_parts.append(f"OF {', '.join(of_parts)}")

        # Handle NOWAIT/SKIP LOCKED options
        if clause.nowait:
            sql_parts.append("NOWAIT")
        elif clause.skip_locked:
            if not self.supports_for_update_skip_locked():
                raise UnsupportedFeatureError(self.name, "SKIP LOCKED")
            sql_parts.append("SKIP LOCKED")

        return " ".join(sql_parts), tuple(all_params)
