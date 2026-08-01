# src/rhosocial/activerecord/backend/dialect/mixins/dql.py
from typing import Any, List, Tuple

from ..exceptions import UnsupportedFeatureError
from ...expression.bases import ToSQLProtocol


class DQLMixin:
    """Mixin for DQL (SELECT) statement formatting."""

    def supports_offset_without_limit(self) -> bool:
        return False

    def supports_for_update(self) -> bool:
        return False

    def format_limit_offset(self, limit=None, offset=None) -> Tuple[str, List]:
        parts = []
        params = []
        if limit is not None:
            parts.append(f"LIMIT {self.get_parameter_placeholder()}")
            params.append(limit)
        if offset is not None:
            parts.append(f"OFFSET {self.get_parameter_placeholder()}")
            params.append(offset)
        if not parts:
            return None, []
        return " ".join(parts), params

    def format_limit_offset_clause(self, clause) -> Tuple[str, tuple]:
        all_params: List[Any] = []
        parts = []
        if clause.limit is not None:
            if isinstance(clause.limit, ToSQLProtocol):
                limit_sql, limit_params = clause.limit.to_sql()
                parts.append(f"LIMIT {limit_sql}")
                all_params.extend(limit_params)
            else:
                parts.append(f"LIMIT {self.get_parameter_placeholder()}")
                all_params.append(clause.limit)
        if clause.offset is not None:
            if isinstance(clause.offset, ToSQLProtocol):
                offset_sql, offset_params = clause.offset.to_sql()
                parts.append(f"OFFSET {offset_sql}")
                all_params.extend(offset_params)
            else:
                parts.append(f"OFFSET {self.get_parameter_placeholder()}")
                all_params.append(clause.offset)
        return " ".join(parts), tuple(all_params)

    def format_where_clause(self, clause) -> Tuple[str, tuple]:
        condition_sql, condition_params = clause.condition.to_sql()
        return f"WHERE {condition_sql}", condition_params

    _VALID_ORDER_DIRECTIONS = frozenset({"ASC", "DESC"})

    def format_order_by_clause(self, clause) -> Tuple[str, tuple]:
        all_params: List[Any] = []
        expr_parts = []
        for item in clause.expressions:
            if isinstance(item, tuple):
                expr, direction = item
                expr_sql, expr_params = expr.to_sql()
                direction = direction.upper()
                if direction not in self._VALID_ORDER_DIRECTIONS:
                    raise ValueError(f"Invalid ORDER BY direction: {direction!r}. Must be 'ASC' or 'DESC'.")
                expr_parts.append(f"{expr_sql} {direction}")
                all_params.extend(expr_params)
            else:
                expr_sql, expr_params = item.to_sql()
                expr_parts.append(expr_sql)
                all_params.extend(expr_params)
        return f"ORDER BY {', '.join(expr_parts)}", tuple(all_params)

    def format_group_by_having_clause(self, clause) -> Tuple[str, tuple]:
        all_params: List[Any] = []
        group_parts = []
        for expr in clause.group_by:
            expr_sql, expr_params = expr.to_sql()
            group_parts.append(expr_sql)
            all_params.extend(expr_params)
        sql_parts = []
        if group_parts:
            sql_parts.append(f"GROUP BY {', '.join(group_parts)}")
        if clause.having:
            having_sql, having_params = clause.having.to_sql()
            sql_parts.append(f"HAVING {having_sql}")
            all_params.extend(having_params)
        return " ".join(sql_parts), tuple(all_params)

    def format_query_statement(self, expr) -> Tuple[str, tuple]:
        from ..exceptions import UnsupportedFeatureError
        if self.strict_validation:
            expr.validate(strict=True)
        all_params: List[Any] = []
        select_parts = []
        for e in expr.select:
            expr_sql, expr_params = e.to_sql()
            select_parts.append(expr_sql)
            all_params.extend(expr_params)
        modifier_str = ""
        if expr.select_modifier:
            modifier_str = f" {expr.select_modifier.value}"
        select_sql = f"SELECT{modifier_str} " + ", ".join(select_parts)
        from_sql = ""
        if expr.from_:
            if isinstance(expr.from_, str):
                from_expr_sql = self.format_identifier(expr.from_)
                from_expr_params = []
            elif isinstance(expr.from_, list):
                from_parts = []
                from_expr_params = []
                for source in expr.from_:
                    if isinstance(source, str):
                        part_sql = self.format_identifier(source)
                        part_params = []
                    else:
                        part_sql, part_params = source.to_sql()
                        if source.__class__.__name__ == "ValuesExpression" and source.alias is None:
                            part_sql = f"({part_sql})"
                        if source.__class__.__name__ == "SetOperationExpression" and source.alias is None:
                            part_sql = f"({part_sql})"
                    from_parts.append(part_sql)
                    from_expr_params.extend(part_params)
                from_expr_sql = ", ".join(from_parts)
            else:
                from_expr_sql, from_expr_params = expr.from_.to_sql()
                if expr.from_.__class__.__name__ == "ValuesExpression" and expr.from_.alias is None:
                    from_expr_sql = f"({from_expr_sql})"
                if expr.from_.__class__.__name__ == "SetOperationExpression" and expr.from_.alias is None:
                    from_expr_sql = f"({from_expr_sql})"
            from_sql = f" FROM {from_expr_sql}"
            all_params.extend(from_expr_params)
        where_sql = ""
        if expr.where:
            where_expr_sql, where_expr_params = expr.where.to_sql()
            where_sql = f" {where_expr_sql}"
            all_params.extend(where_expr_params)
        group_by_having_sql = ""
        if expr.group_by_having:
            gbh_expr_sql, gbh_expr_params = expr.group_by_having.to_sql()
            group_by_having_sql = f" {gbh_expr_sql}"
            all_params.extend(gbh_expr_params)
        order_by_sql = ""
        if expr.order_by:
            order_by_expr_sql, order_by_expr_params = expr.order_by.to_sql()
            order_by_sql = f" {order_by_expr_sql}"
            all_params.extend(order_by_expr_params)
        qualify_sql = ""
        if expr.qualify:
            qualify_expr_sql, qualify_expr_params = expr.qualify.to_sql()
            qualify_sql = f" QUALIFY {qualify_expr_sql}"
            all_params.extend(qualify_expr_params)
        sql = f"{select_sql}{from_sql}{where_sql}{group_by_having_sql}{order_by_sql}{qualify_sql}"
        if expr.limit_offset:
            limit_offset_sql, limit_offset_params = expr.limit_offset.to_sql()
            if limit_offset_sql:
                sql += f" {limit_offset_sql}"
                all_params.extend(limit_offset_params)
        if expr.for_update:
            if not self.supports_for_update():
                raise UnsupportedFeatureError(
                    self.name,
                    "FOR UPDATE clause",
                    "This backend does not support row-level locking with FOR UPDATE. "
                    "Use dialect.supports_for_update() to check support. "
                    "For SQLite, use BEGIN IMMEDIATE transactions for write serialization.",
                )
            for_update_sql, for_update_params = expr.for_update.to_sql()
            if for_update_sql:
                sql += f" {for_update_sql}"
                all_params.extend(for_update_params)
        return sql, tuple(all_params)
