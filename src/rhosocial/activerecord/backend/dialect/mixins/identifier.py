# src/rhosocial/activerecord/backend/dialect/mixins/identifier.py
from typing import Tuple


class IdentifierMixin:
    """Mixin for identifier and table/column reference formatting.

    Formatting functions receive the expression instance only; every value
    they need was collected at expression construction time.
    """

    def format_column(self, expr) -> Tuple[str, Tuple]:
        """Format a :class:`~...expression.core.Column`.

        The dialect decides how to handle ``schema_name`` based on backend
        rules (e.g. SQLite silently drops schema-qualified columns), then
        applies type casts (outermost) and the alias (per SQL standard
        output order: expression, casts, alias).
        """
        if expr.schema_name and expr.table:
            col_sql = (
                f"{self.format_identifier(expr.schema_name)}."
                f"{self.format_identifier(expr.table)}.{self.format_identifier(expr.name)}"
            )
        elif expr.table:
            col_sql = f"{self.format_identifier(expr.table)}.{self.format_identifier(expr.name)}"
        else:
            col_sql = self.format_identifier(expr.name)

        if expr.alias:
            col_sql = f"{col_sql} AS {self.format_identifier(expr.alias)}"
        return col_sql, ()

    def format_wildcard(self, expr) -> Tuple[str, Tuple]:
        """Format a :class:`~...expression.core.WildcardExpression`."""
        if expr.schema_name and expr.table:
            wildcard_sql = f"{self.format_identifier(expr.schema_name)}.{self.format_identifier(expr.table)}.*"
        elif expr.table:
            wildcard_sql = f"{self.format_identifier(expr.table)}.*"
        else:
            wildcard_sql = "*"
        return wildcard_sql, ()

    def format_identifier_expression(self, expr) -> Tuple[str, Tuple]:
        """Format an :class:`~...expression.literals.Identifier` node."""
        return self.format_identifier(expr.name), ()

    def supports_explicit_inner_join(self) -> bool:
        return False

    def format_table(self, expr) -> Tuple[str, Tuple]:
        """Format a :class:`~...expression.core.TableExpression`."""
        if expr.schema_name:
            table_sql = f"{self.format_identifier(expr.schema_name)}.{self.format_identifier(expr.name)}"
        else:
            table_sql = self.format_identifier(expr.name)
        if expr.alias:
            table_sql = f"{table_sql} AS {self.format_identifier(expr.alias)}"
        params: tuple = ()
        if expr.temporal_options:
            result = self.format_temporal_options(expr.temporal_options)
            if result is not None:
                temporal_sql, temporal_params = result
                table_sql = f"{table_sql} {temporal_sql}"
                params += temporal_params
        return table_sql, params

    def format_qualified_identifier(self, expr) -> Tuple[str, Tuple]:
        """Format a :class:`~...expression.core.QualifiedIdentifierExpression`."""
        if expr.schema:
            return (
                f"{self.format_identifier(expr.schema)}.{self.format_identifier(expr.name)}",
                (),
            )
        return self.format_identifier(expr.name), ()
