# src/rhosocial/activerecord/backend/dialect/mixins/identifier.py
from typing import Optional, Tuple


class IdentifierMixin:
    """Mixin for identifier and table/column reference formatting."""

    def format_column(
        self, name: str, table: Optional[str] = None, alias: Optional[str] = None, schema_name: Optional[str] = None
    ) -> Tuple[str, Tuple]:
        if schema_name and table:
            col_sql = f"{self.format_identifier(schema_name)}.{self.format_identifier(table)}.{self.format_identifier(name)}"
        elif table:
            col_sql = f"{self.format_identifier(table)}.{self.format_identifier(name)}"
        else:
            col_sql = self.format_identifier(name)
        if alias:
            return f"{col_sql} AS {self.format_identifier(alias)}", ()
        return col_sql, ()

    def format_wildcard(self, table: Optional[str] = None, schema_name: Optional[str] = None) -> Tuple[str, Tuple]:
        if schema_name and table:
            wildcard_sql = f"{self.format_identifier(schema_name)}.{self.format_identifier(table)}.*"
        elif table:
            wildcard_sql = f"{self.format_identifier(table)}.*"
        else:
            wildcard_sql = "*"
        return wildcard_sql, ()

    def supports_explicit_inner_join(self) -> bool:
        return False

    def format_table(
        self, table_name: str, alias: Optional[str] = None, schema_name: Optional[str] = None
    ) -> Tuple[str, Tuple]:
        if schema_name:
            table_sql = f"{self.format_identifier(schema_name)}.{self.format_identifier(table_name)}"
        else:
            table_sql = self.format_identifier(table_name)
        if alias:
            return f"{table_sql} AS {self.format_identifier(alias)}", ()
        return table_sql, ()
