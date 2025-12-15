# src/rhosocial/activerecord/backend/base/sql_building.py
"""
SQL building operations mixin for backend implementations.

This mixin provides utility methods for preparing SQL statements and parameters
before execution.
"""
from typing import Optional, Tuple


class SQLBuildingMixin:
    """
    Mixin for SQL building operations.

    This mixin provides methods for preparing SQL statements and parameters
    for database execution. It works with the dialect system to ensure proper
    SQL formatting.
    """

    def _prepare_sql_and_params(
            self,
            sql: str,
            params: Optional[Tuple]
    ) -> Tuple[str, Optional[Tuple]]:
        """
        Prepare SQL and parameters for execution.

        This method can be overridden by subclasses to perform any
        dialect-specific transformations on SQL and parameters before
        they are sent to the database driver.

        Args:
            sql: SQL statement string
            params: Optional tuple of parameters

        Returns:
            Tuple of (prepared SQL, prepared parameters)
        """
        return sql, params