# src/rhosocial/activerecord/backend/dialect/mixins/cte.py
from typing import Any, List, Optional, Dict, Tuple


class CTEMixin:
    """Mixin for Common Table Expression (CTE) support."""

    def supports_basic_cte(self) -> bool:
        """Whether basic CTEs are supported."""
        return False

    def supports_recursive_cte(self) -> bool:
        """Whether recursive CTEs are supported."""
        return False

    def supports_materialized_cte(self) -> bool:
        """Whether MATERIALIZED hint is supported."""
        return False

    def format_cte(
        self,
        name: str,
        query_sql: str,
        columns: Optional[List[str]] = None,
        recursive: bool = False,
        materialized: Optional[bool] = None,
        dialect_options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Format a single CTE definition."""
        materialized_hint = ""
        if materialized is not None:
            materialized_hint = "MATERIALIZED " if materialized else "NOT MATERIALIZED "

        name_part = self.format_identifier(name)
        columns_part = f" ({', '.join(self.format_identifier(c) for c in columns)})" if columns else ""
        return f"{name_part}{columns_part} AS {materialized_hint}({query_sql})"

    def format_with_query(
        self,
        cte_sql_parts: List[str],
        main_query_sql: str,
        dialect_options: Optional[Dict[str, Any]] = None,
        has_recursive: bool = False,  # Added parameter to indicate if any CTE is recursive
    ) -> str:
        """Format a complete query with WITH clause."""
        if not cte_sql_parts:
            return main_query_sql
        with_clause = self.format_with_clause(cte_sql_parts, has_recursive)
        return f"{with_clause} {main_query_sql}"

    def format_with_clause(self, ctes_sql: List[str], has_recursive: bool = False) -> str:
        """Helper to format complete WITH clause from list of CTE definitions."""
        if not ctes_sql:
            return ""
        recursive_str = "RECURSIVE " if has_recursive else ""
        return f"WITH {recursive_str}{', '.join(ctes_sql)}"
