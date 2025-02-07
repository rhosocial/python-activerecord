"""SQL query builder with methods for constructing query parts."""
from typing import List, Any, Tuple


class QueryBuilder:
    """SQL query builder with methods for constructing query parts."""

    @staticmethod
    def build_where(conditions: List[Tuple[str, tuple]]) -> Tuple[str, List[Any]]:
        """Build WHERE clause.

        Args:
            conditions: List of conditions, each condition is a (sql, params) tuple

        Returns:
            Tuple (sql_where, params), where sql_where is the complete WHERE clause,
            and params is the parameter list
        """
        where_clauses = []
        params = []
        for condition, condition_params in conditions:
            where_clauses.append(condition)
            if condition_params:
                params.extend(condition_params)
        return " AND ".join(where_clauses), params

    @staticmethod
    def build_order(clauses: List[str]) -> str:
        """Build ORDER BY clause."""
        return " ORDER BY " + ", ".join(clauses) if clauses else ""

    @staticmethod
    def build_group(clauses: List[str]) -> str:
        """Build GROUP BY clause."""
        return " GROUP BY " + ", ".join(clauses) if clauses else ""

    @staticmethod
    def build_having(conditions: List[Tuple[str, tuple]]) -> Tuple[str, List[Any]]:
        """Build HAVING clause."""
        having_clauses = []
        params = []
        for condition, condition_params in conditions:
            having_clauses.append(condition)
            if condition_params:
                params.extend(condition_params)
        return " HAVING " + " AND ".join(having_clauses), params