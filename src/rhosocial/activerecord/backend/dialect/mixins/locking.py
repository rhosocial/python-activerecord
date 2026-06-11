# src/rhosocial/activerecord/backend/dialect/mixins/locking.py
from typing import Any, List, Tuple, TYPE_CHECKING

from ...expression.bases import ToSQLProtocol

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.query_parts import ForUpdateClause


class LockingMixin:
    """Mixin for locking clause support."""

    def supports_for_update_skip_locked(self) -> bool:
        """Whether FOR UPDATE SKIP LOCKED is supported."""
        return False

    def format_for_update_clause(self, clause: "ForUpdateClause") -> Tuple[str, tuple]:
        """Default implementation for FOR UPDATE clause."""
        all_params = []
        sql_parts = ["FOR UPDATE"]

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
            sql_parts.append("SKIP LOCKED")

        return " ".join(sql_parts), tuple(all_params)
