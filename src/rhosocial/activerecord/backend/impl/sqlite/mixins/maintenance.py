# src/rhosocial/activerecord/backend/impl/sqlite/mixins/maintenance.py
"""
SQLite-specific maintenance statement implementation.

This module provides the SQLiteMaintenanceMixin class covering VACUUM,
ANALYZE, ATTACH DATABASE, and DETACH DATABASE formatting.
"""

from typing import Tuple, TYPE_CHECKING

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

if TYPE_CHECKING:
    from ..expression.attach import SQLiteAttachExpression, SQLiteDetachExpression
    from ..expression.vacuum import SQLiteAnalyzeExpression, SQLiteVacuumExpression


class SQLiteMaintenanceMixin:
    """Mixin for SQLite VACUUM / ANALYZE / ATTACH / DETACH support.

    Implements the SQLiteMaintenanceSupport protocol, providing capability
    detection and SQL formatting methods for database-maintenance statements.
    """

    def supports_vacuum(self) -> bool:
        """VACUUM is supported since SQLite 3.0."""
        return True

    def supports_vacuum_into(self) -> bool:
        """VACUUM INTO 'filename' is supported since SQLite 3.27.0."""
        return self.version >= (3, 27, 0)

    def supports_analyze(self) -> bool:
        """ANALYZE is supported since SQLite 3.0."""
        return True

    def supports_attach(self) -> bool:
        """ATTACH DATABASE is supported since SQLite 3.0."""
        return True

    def supports_detach(self) -> bool:
        """DETACH DATABASE is supported since SQLite 3.0."""
        return True

    def format_vacuum_statement(self, expr: "SQLiteVacuumExpression") -> Tuple[str, tuple]:
        """Format the VACUUM statement for SQLite.

        SQLite VACUUM syntax:
        - VACUUM                        -- Rebuild the whole database
        - VACUUM schema                 -- Vacuum a specific attached schema
        - VACUUM INTO 'filename'        -- Write vacuumed db to a new file (3.27.0+)

        Args:
            expr: SQLiteVacuumExpression instance.

        Returns:
            Tuple of (SQL string, empty parameters tuple).

        Raises:
            UnsupportedFeatureError: If VACUUM INTO is requested on SQLite
                versions below 3.27.0.
        """
        if expr.into is not None:
            if not self.supports_vacuum_into():
                raise UnsupportedFeatureError(
                    self.name, "VACUUM INTO", "VACUUM INTO requires SQLite 3.27.0 or later."
                )
            escaped = self._escape_sql_string(expr.into)
            return f"VACUUM INTO '{escaped}'", ()

        if expr.schema is not None:
            return f"VACUUM {self.format_identifier(expr.schema)}", ()

        return "VACUUM", ()

    def format_analyze_statement(self, expr: "SQLiteAnalyzeExpression") -> Tuple[str, tuple]:
        """Format the ANALYZE statement for SQLite.

        SQLite ANALYZE syntax: ``ANALYZE``.

        Args:
            expr: SQLiteAnalyzeExpression instance.

        Returns:
            Tuple of (SQL string, empty parameters tuple).
        """
        return "ANALYZE", ()

    def format_attach_statement(self, expr: "SQLiteAttachExpression") -> Tuple[str, tuple]:
        """Format the ATTACH DATABASE statement for SQLite.

        SQLite ATTACH syntax: ``ATTACH DATABASE 'filename' AS schema_name``.

        Args:
            expr: SQLiteAttachExpression instance.

        Returns:
            Tuple of (SQL string, empty parameters tuple).
        """
        escaped = self._escape_sql_string(expr.database)
        return f"ATTACH DATABASE '{escaped}' AS {self.format_identifier(expr.schema)}", ()

    def format_detach_statement(self, expr: "SQLiteDetachExpression") -> Tuple[str, tuple]:
        """Format the DETACH DATABASE statement for SQLite.

        SQLite DETACH syntax: ``DETACH DATABASE schema_name``.

        Args:
            expr: SQLiteDetachExpression instance.

        Returns:
            Tuple of (SQL string, empty parameters tuple).
        """
        return f"DETACH DATABASE {self.format_identifier(expr.schema)}", ()