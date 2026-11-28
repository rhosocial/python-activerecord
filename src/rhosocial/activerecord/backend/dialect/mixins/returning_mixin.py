# .../mixins/returning_mixin.py
"""Mixin for ReturningSupport. Members/order/signature mirror the protocol."""
from ...expression.sources.subquery import Subquery
from ..exceptions import UnsupportedFeatureError

from typing import Any, List, Tuple

class ReturningMixin:

    def supports_returning_insert(self) -> bool:
            """Whether RETURNING clause is supported for INSERT statements."""
            return False

    def supports_returning_update(self) -> bool:
            """Whether RETURNING clause is supported for UPDATE statements."""
            return False

    def supports_returning_delete(self) -> bool:
            """Whether RETURNING clause is supported for DELETE statements."""
            return False

    def supports_returning_expressions(self) -> bool:
            """Whether non-column expressions (functions, arithmetic, CASE, ...) may
            appear in a RETURNING clause. Optimistic default; dialects that accept
            only column references (e.g. Oracle) override to ``False``.
            """
            return True

    def supports_returning_alias(self) -> bool:
            """Whether a clause-level alias (``RETURNING ... AS alias``) is
            supported. Optimistic default; dialects that reject it (e.g. SQL Server
            OUTPUT) override to ``False``.
            """
            return True

    def supports_returning_wildcard(self) -> bool:
            """Whether ``RETURNING *`` (wildcard) is supported. Optimistic default;
            dialects that reject it override to ``False``.
            """
            return True

    def supports_returning_single_row(self) -> bool:
            """Whether RETURNING is inherently single-row. Default ``False``
            (multi-row); Oracle / Firebird override to ``True``.
            """
            return False

    def supports_returning_old_new(self) -> bool:
            """Whether ``OLD.<col>`` / ``NEW.<col>`` references are permitted in a
            RETURNING clause. Default ``False``; PostgreSQL 17+ overrides.
            """
            return False

    def supports_returning_into(self) -> bool:
            """Whether a ``RETURNING ... INTO <target>`` / ``OUTPUT ... INTO``
            clause is supported. Default ``False``; SQL Server and Oracle override.
            """
            return False

    def format_returning_clause(self, expr: "ReturningClause") -> Tuple[str, Tuple]:
            """Format a RETURNING expr.

            Validates the requested expressions against the dialect's capability
            switches and raises :class:`UnsupportedFeatureError` when a requested
            feature is not supported by the dialect.

            Args:
                expr: ReturningClause object containing expressions to return

            Returns:
                Tuple of (SQL string, parameters tuple)

            Raises:
                UnsupportedFeatureError: If a requested RETURNING feature is not
                    supported by this dialect.
            """
            from ...expression.column_types.column_types import ColumnBase
            from ...expression.value_types.wildcards import AllColumnsWildcard
            from ...expression.functions.function_call import FunctionCall
            from ...expression.sources.subquery import Subquery
            from ...expression.functions.aggregate import AggregateFunction
            from ...expression.operators.operators import RawSQL

            all_params: List[Any] = []
            expr_parts: List[str] = []
            for item in expr.expressions:
                if (
                    (isinstance(item, FunctionCall) and item.is_aggregate)
                    or isinstance(item, AggregateFunction)
                    or isinstance(item, Subquery)
                ):
                    raise UnsupportedFeatureError(
                        self.name,
                        "aggregate/subquery in RETURNING",
                        "A RETURNING clause is evaluated per row and cannot contain "
                        "aggregate functions or subqueries.",
                    )
                if isinstance(item, AllColumnsWildcard):
                    if not self.supports_returning_wildcard():
                        raise UnsupportedFeatureError(
                            self.name,
                            "wildcard in RETURNING",
                            "This dialect does not support '*' in a RETURNING clause; "
                            "list the columns explicitly.",
                        )
                elif isinstance(item, ColumnBase):
                    if item.table and item.table.upper() in ("OLD", "NEW"):
                        if not self.supports_returning_old_new():
                            raise UnsupportedFeatureError(
                                self.name,
                                "OLD/NEW in RETURNING",
                                "This dialect does not support OLD/NEW row references "
                                "in a RETURNING clause.",
                            )
                elif not isinstance(item, RawSQL):
                    if not self.supports_returning_expressions():
                        raise UnsupportedFeatureError(
                            self.name,
                            "expressions in RETURNING",
                            "This dialect only supports column references in a "
                            "RETURNING clause.",
                        )

                expr_sql, expr_params = item.to_sql()
                expr_parts.append(expr_sql)
                all_params.extend(expr_params)

            returning_sql = f"RETURNING {', '.join(expr_parts)}"

            if expr.output_into:
                if not self.supports_returning_into():
                    raise UnsupportedFeatureError(
                        self.name,
                        "RETURNING ... INTO",
                        "This dialect does not support a RETURNING/OUTPUT ... INTO target.",
                    )
                returning_sql += f" INTO {expr.output_into}"

            if expr.alias:
                if not self.supports_returning_alias():
                    raise UnsupportedFeatureError(
                        self.name,
                        "alias in RETURNING",
                        "This dialect does not support a expr-level alias on a "
                        "RETURNING expr.",
                    )
                returning_sql += f" AS {self.format_identifier(expr.alias)}"

            return returning_sql, tuple(all_params)
