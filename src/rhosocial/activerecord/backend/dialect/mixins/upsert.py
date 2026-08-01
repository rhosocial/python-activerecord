# src/rhosocial/activerecord/backend/dialect/mixins/upsert.py
from typing import Tuple, TYPE_CHECKING

from ...expression import bases
from ...expression.bases import ToSQLProtocol

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.statements import OnConflictClause


class UpsertMixin:
    """Mixin for UPSERT operation support."""

    def supports_upsert(self) -> bool:
        """Whether UPSERT is supported."""
        return False

    def get_upsert_syntax_type(self) -> str:
        """
        Get UPSERT syntax type.

        Returns:
            'ON CONFLICT' (PostgreSQL) or 'ON DUPLICATE KEY' (MySQL)
        """
        return "ON CONFLICT"

    def supports_on_conflict_clause(self) -> bool:
        """
        Whether the ON CONFLICT clause form is supported.

        UpsertMixin ships ``format_on_conflict_clause``, so dialects mixing
        it in are capable by default. Backends using a different upsert
        mechanism (e.g. Oracle MERGE) override to False.
        """
        return True

    def supports_multiple_on_conflict_clauses(self) -> bool:
        """
        Whether multiple ON CONFLICT clauses are supported.

        Default False; only SQLite (>= 3.35.0) overrides to True.
        """
        return False

    def format_on_conflict_clause(self, expr: "OnConflictClause") -> Tuple[str, tuple]:
        """Format ON CONFLICT clause."""
        all_params = []

        # Start with ON CONFLICT
        parts = ["ON CONFLICT"]

        # Add conflict target if specified
        if expr.conflict_target:
            target_parts = []
            for target in expr.conflict_target:
                if isinstance(target, str):
                    # Column name as string
                    target_parts.append(self.format_identifier(target))
                elif isinstance(target, ToSQLProtocol):
                    # Column expression
                    target_sql, target_params = target.to_sql()
                    target_parts.append(target_sql)
                    all_params.extend(target_params)
                else:
                    # Other types - format as identifier
                    target_parts.append(self.format_identifier(str(target)))

            if target_parts:
                parts.append(f"({', '.join(target_parts)})")

        # Add DO NOTHING or DO UPDATE
        if expr.do_nothing:
            parts.append("DO NOTHING")
        elif expr.update_assignments:
            # DO UPDATE SET assignments
            update_parts = []
            for col, expr_val in expr.update_assignments.items():
                if isinstance(expr_val, bases.BaseExpression):
                    val_sql, val_params = expr_val.to_sql()
                    update_parts.append(f"{self.format_identifier(col)} = {val_sql}")
                    all_params.extend(val_params)
                else:
                    update_parts.append(f"{self.format_identifier(col)} = {self.get_parameter_placeholder()}")
                    all_params.append(expr_val)

            parts.append(f"DO UPDATE SET {', '.join(update_parts)}")

            # Add WHERE clause if specified
            if expr.update_where:
                where_sql, where_params = expr.update_where.to_sql()
                parts.append(f"WHERE {where_sql}")
                all_params.extend(where_params)
        else:
            # Default to DO NOTHING if no action specified
            parts.append("DO NOTHING")

        return " ".join(parts), tuple(all_params)
