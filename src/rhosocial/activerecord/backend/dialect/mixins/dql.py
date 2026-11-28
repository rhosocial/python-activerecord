# .../mixins/dql.py
"""Base DQL rendering mixin. Sub-features live in their own mixins."""

from typing import TYPE_CHECKING, Any, List, Tuple
from ...expression.bases.bases import ToSQLProtocol
from ...expression.query_parts.query_parts import SortDirection
from .dql_order_mixin import DqlOrderMixin
from .advanced_grouping_mixin import AdvancedGroupingMixin
from .locking_mixin import LockingMixin
from .qualify_clause_mixin import QualifyClauseMixin

from ..protocols.query.dql_support import DQLSupport

class DQLMixin(DqlOrderMixin, AdvancedGroupingMixin, LockingMixin, QualifyClauseMixin):
    def build_limit_offset(self, limit=None, offset=None) -> Tuple[str, List]:
            """Build a LIMIT/OFFSET fragment from raw values.

            This is a helper, not a formatter: it is intentionally not named
            ``format_*`` because dialect formatters take an expression node.
            """
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

    def format_limit_offset_clause(self, expr: "LimitOffsetClause") -> Tuple[str, tuple]:
            """Format a LIMIT/OFFSET expr object.

            Args:
                expr: Clause exposing ``limit``, ``offset`` and ``with_ties``
                    attributes, either raw values or objects implementing
                    ``ToSQLProtocol``.

            Returns:
                A ``(sql, params)`` tuple; the SQL is empty when both are ``None``.

            Raises:
                UnsupportedFeatureError: If ``with_ties`` is requested but the
                    dialect does not support ``FETCH FIRST ... WITH TIES``.
            """
            from ..exceptions import UnsupportedFeatureError

            all_params: List[Any] = []
            parts = []
            if expr.with_ties:
                if not self.supports_fetch_with_ties():
                    raise UnsupportedFeatureError(
                        self.name,
                        "FETCH FIRST ... WITH TIES",
                        "This dialect does not support FETCH FIRST ... WITH TIES.",
                    )
                if expr.limit is None:
                    raise UnsupportedFeatureError(
                        self.name,
                        "WITH TIES without a row limit",
                        "FETCH FIRST ... WITH TIES requires a row limit.",
                    )
                if expr.offset is not None:
                    if isinstance(expr.offset, ToSQLProtocol):
                        offset_sql, offset_params = expr.offset.to_sql()
                        parts.append(f"OFFSET {offset_sql} ROWS")
                        all_params.extend(offset_params)
                    else:
                        parts.append(f"OFFSET {self.get_parameter_placeholder()} ROWS")
                        all_params.append(expr.offset)
                if isinstance(expr.limit, ToSQLProtocol):
                    limit_sql, limit_params = expr.limit.to_sql()
                    parts.append(f"FETCH FIRST {limit_sql} ROWS WITH TIES")
                    all_params.extend(limit_params)
                else:
                    parts.append(f"FETCH FIRST {self.get_parameter_placeholder()} ROWS WITH TIES")
                    all_params.append(expr.limit)
                return " ".join(parts), tuple(all_params)

            if expr.limit is not None:
                if isinstance(expr.limit, ToSQLProtocol):
                    limit_sql, limit_params = expr.limit.to_sql()
                    parts.append(f"LIMIT {limit_sql}")
                    all_params.extend(limit_params)
                else:
                    parts.append(f"LIMIT {self.get_parameter_placeholder()}")
                    all_params.append(expr.limit)
            if expr.offset is not None:
                if isinstance(expr.offset, ToSQLProtocol):
                    offset_sql, offset_params = expr.offset.to_sql()
                    parts.append(f"OFFSET {offset_sql}")
                    all_params.extend(offset_params)
                else:
                    parts.append(f"OFFSET {self.get_parameter_placeholder()}")
                    all_params.append(expr.offset)
            return " ".join(parts), tuple(all_params)

    def format_where_clause(self, expr: "WhereClause") -> Tuple[str, tuple]:
            """Format a WHERE expr.

            Args:
                expr: Clause exposing a ``condition`` expression.

            Returns:
                A ``(sql, params)`` tuple beginning with ``WHERE``.
            """
            condition_sql, condition_params = expr.condition.to_sql()
            return f"WHERE {condition_sql}", condition_params

    def format_order_by_clause(self, expr: "OrderByClause") -> Tuple[str, tuple]:
            """Format an ORDER BY expr.

            Args:
                expr: Clause exposing ``expressions``; each item is either an
                    expression or a ``(expression, direction)`` tuple.

            Returns:
                A ``(sql, params)`` tuple beginning with ``ORDER BY``.

            Raises:
                ValueError: If a supplied sort direction is not ``ASC`` or ``DESC``.
            """
            all_params: List[Any] = []
            expr_parts = []
            for item in expr.expressions:
                if isinstance(item, tuple):
                    expr, direction = item
                    expr_sql, expr_params = expr.to_sql()
                    # The word travels; the keyword is written here.
                    direction = SortDirection.parse(direction)
                    # No direction is ordinary, not an error. The wire says null and
                    # the SQL says nothing: leaving the row order to the engine is
                    # what the artifact asked for -- and it is the shape Go writes,
                    # so a reader that rejected it would reject its counterpart.
                    if direction is None:
                        expr_parts.append(expr_sql)
                    else:
                        expr_parts.append(f"{expr_sql} {direction.keyword}")
                    all_params.extend(expr_params)
                else:
                    expr_sql, expr_params = item.to_sql()
                    expr_parts.append(expr_sql)
                    all_params.extend(expr_params)
            return f"ORDER BY {', '.join(expr_parts)}", tuple(all_params)

    def format_order_by_item(self, expr: "OrderByItem") -> Tuple[str, tuple]:
            """Format a single sort element of an ORDER BY clause.

            Args:
                expr: An :class:`OrderByItem` carrying the sort operand,
                    optional direction and optional null ordering.

            Returns:
                A ``(sql, params)`` tuple.

            Raises:
                UnsupportedFeatureError: If ``NULLS FIRST`` / ``NULLS LAST`` is
                    requested but the dialect does not support it.
            """
            from ..exceptions import UnsupportedFeatureError

            operand_sql, expr_params = expr.operand.to_sql()
            parts = [operand_sql]
            if expr.direction is not None:
                # The node carries the word; the keyword is written here, so the
                # artifact stays language-neutral.
                parts.append(expr.direction.keyword)
            if expr.nulls is not None:
                if not self.supports_nulls_first_last():
                    raise UnsupportedFeatureError(
                        self.name,
                        "NULLS FIRST/LAST in ORDER BY",
                        "This dialect does not support explicit NULLS FIRST/LAST "
                        "ordering in an ORDER BY clause.",
                    )
                parts.append("NULLS FIRST" if expr.nulls == "first" else "NULLS LAST")
            return " ".join(parts), tuple(expr_params)

    def format_group_by_having_clause(self, expr: "GroupByHavingClause") -> Tuple[str, tuple]:
            """Format a combined GROUP BY / HAVING expr.

            Args:
                expr: Clause exposing ``group_by`` (iterable of expressions) and
                    an optional ``having`` expression.

            Returns:
                A ``(sql, params)`` tuple; empty when there is neither grouping nor
                a HAVING condition.
            """
            all_params: List[Any] = []
            group_parts = []
            for item in expr.group_by:
                expr_sql, expr_params = item.to_sql()
                group_parts.append(expr_sql)
                all_params.extend(expr_params)
            sql_parts = []
            if group_parts:
                sql_parts.append(f"GROUP BY {', '.join(group_parts)}")
            if expr.having:
                having_sql, having_params = expr.having.to_sql()
                sql_parts.append(f"HAVING {having_sql}")
                all_params.extend(having_params)
            return " ".join(sql_parts), tuple(all_params)

    def format_query_statement(self, expr: "QueryStatement") -> Tuple[str, tuple]:
            """Format a complete SELECT query.

            Args:
                expr: The QueryStatement to render.

            Returns:
                A ``(sql, params)`` tuple of the statement text and its bind
                parameters.

            Raises:
                UnsupportedFeatureError: If a FOR UPDATE clause is requested but the
                    dialect does not support it.
            """
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
                # The keyword comes from the enum, so the wire value stays the
                # language-neutral word.
                modifier_str = f" {expr.select_modifier.keyword}"
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
                            if source.__class__.__name__ == "SetOperation":
                                part_sql = f"({part_sql})"
                        from_parts.append(part_sql)
                        from_expr_params.extend(part_params)
                    from_expr_sql = ", ".join(from_parts)
                else:
                    from_expr_sql, from_expr_params = expr.from_.to_sql()
                    if expr.from_.__class__.__name__ == "ValuesExpression" and expr.from_.alias is None:
                        from_expr_sql = f"({from_expr_sql})"
                    if expr.from_.__class__.__name__ == "SetOperation":
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
                qualify_sql = f" {qualify_expr_sql}"
                all_params.extend(qualify_expr_params)
            sql = f"{select_sql}{from_sql}{where_sql}{group_by_having_sql}{qualify_sql}{order_by_sql}"
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
