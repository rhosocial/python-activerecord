# src/rhosocial/activerecord/backend/dialect/mixins/pivot.py
"""Dialect mixin for PIVOT / UNPIVOT clause support.

Provides the capability switches and the core SQL rendering shared by the
backends that support PIVOT / UNPIVOT. Dialects override
:meth:`format_pivot_value` and/or the whole formatter when their value
semantics or extensions differ.
"""
from typing import Any, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.pivot import PivotExpression, UnpivotExpression


class PivotMixin:
    """PIVOT / UNPIVOT capability and formatting support.

    ``supports_pivot()`` / ``supports_unpivot()`` default to False; dialects
    that support them (SQL Server, Oracle 11g+, Snowflake, ...) override.
    """

    def supports_pivot(self) -> bool:
        """Whether the PIVOT clause is supported. Defaults to False."""
        return False

    def supports_unpivot(self) -> bool:
        """Whether the UNPIVOT clause is supported. Defaults to False."""
        return False

    def format_pivot_value(self, value: Any) -> Tuple[str, tuple]:
        """Render a single value in a PIVOT ``IN (...)`` list.

        Strings/numbers are rendered as inline SQL literals; expression
        instances are rendered through ``to_sql()``. Dialects whose PIVOT
        values are identifiers (e.g. SQL Server) override this.
        """
        from ...expression.bases import BaseExpression

        if isinstance(value, BaseExpression):
            sql, params = value.to_sql()
            return sql, tuple(params)
        return self.format_literal(value), ()

    def format_pivot_expression(self, expr: "PivotExpression") -> Tuple[str, tuple]:
        """Format a PIVOT clause.

        Raises:
            UnsupportedFeatureError: If the dialect does not support PIVOT.
        """
        from ..exceptions import UnsupportedFeatureError

        if not self.supports_pivot():
            raise UnsupportedFeatureError(self.name, "PIVOT clause")

        all_params: List[Any] = []
        value_parts: List[str] = []
        for value in expr.values:
            value_sql, value_params = self.format_pivot_value(value)
            value_parts.append(value_sql)
            all_params.extend(value_params)

        sql = (
            f"PIVOT ({expr.aggregate_function}("
            f"{self.format_identifier(expr.value_column)}) "
            f"FOR {self.format_identifier(expr.pivot_column)} "
            f"IN ({', '.join(value_parts)})"
        )
        if expr.default is not None:
            sql += f" DEFAULT {self.format_literal(expr.default)}"
        sql += ")"

        if expr.alias:
            sql += f" {self.format_identifier(expr.alias)}"

        return sql, tuple(all_params)

    def format_unpivot_expression(self, expr: "UnpivotExpression") -> Tuple[str, tuple]:
        """Format an UNPIVOT clause.

        Raises:
            UnsupportedFeatureError: If the dialect does not support UNPIVOT.
        """
        from ..exceptions import UnsupportedFeatureError

        if not self.supports_unpivot():
            raise UnsupportedFeatureError(self.name, "UNPIVOT clause")

        nulls = "INCLUDE NULLS " if expr.include_nulls else "EXCLUDE NULLS "
        columns_sql = ", ".join(self.format_identifier(c) for c in expr.columns)

        sql = (
            f"UNPIVOT {nulls}"
            f"({self.format_identifier(expr.value_column)} "
            f"FOR {self.format_identifier(expr.pivot_column)} "
            f"IN ({columns_sql}))"
        )
        if expr.alias:
            sql += f" {self.format_identifier(expr.alias)}"

        return sql, ()
