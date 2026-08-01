# src/rhosocial/activerecord/backend/dialect/mixins/set_operation.py
from typing import Optional, Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError
from ...expression import bases

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.query_parts import (
        OrderByClause,
        LimitOffsetClause,
        ForUpdateClause,
    )


class SetOperationMixin:
    """Mixin for set operation (UNION, INTERSECT, EXCEPT) support."""

    def supports_union(self) -> bool:
        """Whether UNION operation is supported."""
        return False

    def supports_union_all(self) -> bool:
        """Whether UNION ALL operation is supported."""
        return False

    def supports_intersect(self) -> bool:
        """Whether INTERSECT operation is supported."""
        return False

    def supports_except(self) -> bool:
        """Whether EXCEPT operation is supported."""
        return False

    def supports_set_operation_order_by(self) -> bool:
        """Whether set operations support ORDER BY clauses."""
        return False

    def supports_set_operation_limit_offset(self) -> bool:
        """Whether set operations support LIMIT and OFFSET clauses."""
        return False

    def supports_set_operation_for_update(self) -> bool:
        """Whether set operations support FOR UPDATE clauses."""
        return False

    def format_set_operation_expression(
        self,
        left: "bases.BaseExpression",
        right: "bases.BaseExpression",
        operation: str,
        alias: Optional[str],
        all_: bool,
        order_by_clause: Optional["OrderByClause"] = None,
        limit_offset_clause: Optional["LimitOffsetClause"] = None,
        for_update_clause: Optional["ForUpdateClause"] = None,
    ) -> Tuple[str, Tuple]:
        """Format set operation expression (UNION, INTERSECT, EXCEPT)."""
        left_sql, left_params = left.to_sql()
        right_sql, right_params = right.to_sql()
        all_str = " ALL" if all_ else ""

        # Build the base set operation SQL
        base_sql = f"{left_sql} {operation}{all_str} {right_sql}"

        all_params = list(left_params + right_params)

        # Set operations at top level do not need outer parentheses.
        # When used as a subquery (e.g. in a FROM clause), the caller
        # (Subquery / QueryExpression / dql.py) adds the required wrapping.
        sql_parts = [base_sql]

        # Add alias if present
        if alias:
            sql_parts.append(f"AS {self.format_identifier(alias)}")

        # Add ORDER BY clause if present
        if order_by_clause:
            order_by_sql, order_by_params = order_by_clause.to_sql()
            sql_parts.append(order_by_sql)
            all_params.extend(order_by_params)

        # Add LIMIT/OFFSET clause if present
        if limit_offset_clause:
            limit_offset_sql, limit_offset_params = limit_offset_clause.to_sql()
            sql_parts.append(limit_offset_sql)
            all_params.extend(limit_offset_params)

        # Add FOR UPDATE clause if present
        if for_update_clause:
            for_update_sql, for_update_params = for_update_clause.to_sql()
            sql_parts.append(for_update_sql)
            all_params.extend(for_update_params)

        sql = " ".join(sql_parts)
        return sql, tuple(all_params)
