# src/rhosocial/activerecord/backend/impl/sqlite/backend/common.py
"""
Common base classes and mixins for SQLite backend implementations.

This module provides shared functionality between sync and async SQLite backends,
including type adapters, error handling, and common utilities.
"""

import logging
import sqlite3
from sqlite3 import ProgrammingError
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from ..adapters import SQLiteBlobAdapter, SQLiteJSONAdapter, SQLiteUUIDAdapter
from rhosocial.activerecord.backend.errors import (
    DatabaseError,
    DeadlockError,
    IntegrityError,
    OperationalError,
    QueryError,
)
from rhosocial.activerecord.backend.protocols import ConcurrencyHint
from rhosocial.activerecord.backend.type_adapter import SQLTypeAdapter


DEFAULT_PRAGMAS = {
    "foreign_keys": "ON",
    "journal_mode": "WAL",
    "synchronous": "FULL",
    "wal_autocheckpoint": "1000",
    "wal_checkpoint": "FULL",
}


TYPE_MAPPINGS = [
    (bool, int),
    (dict, str),
    (list, str),
]

_sqlite_version_cache: Optional[Tuple[int, int, int]] = None


def get_type_mappings():
    """Get type mappings with lazy imports."""
    from datetime import date, datetime, time
    from decimal import Decimal
    from uuid import UUID
    from enum import Enum

    return [
        (bool, int),
        (datetime, str),
        (date, str),
        (time, str),
        (Decimal, float),
        (UUID, str),
        (dict, str),
        (list, str),
        (Enum, str),
    ]


class SQLiteBackendMixin:
    """Mixin providing common SQLite backend functionality."""

    _sqlite_version_cache: Optional[Tuple[int, int, int]] = None
    _default_suggestions_cache: Optional[Dict[Type, Tuple["SQLTypeAdapter", Type]]] = None

    def _register_sqlite_adapters(self) -> None:
        """Register SQLite-specific type adapters to the adapter_registry."""
        sqlite_adapters = [
            SQLiteBlobAdapter(),
            SQLiteJSONAdapter(),
            SQLiteUUIDAdapter(),
        ]
        for adapter in sqlite_adapters:
            for py_type, db_types in adapter.supported_types.items():
                for db_type in db_types:
                    self.adapter_registry.register(adapter, py_type, db_type, allow_override=True)
        self.logger.debug("Registered SQLite-specific type adapters.")

    def get_default_adapter_suggestions(self) -> Dict[Type, Tuple["SQLTypeAdapter", Type]]:
        """Provides default type adapter suggestions for SQLite."""
        if self._default_suggestions_cache is not None:
            return self._default_suggestions_cache

        suggestions: Dict[Type, Tuple["SQLTypeAdapter", Type]] = {}
        type_mappings = get_type_mappings()

        for py_type, db_type in type_mappings:
            adapter = self.adapter_registry.get_adapter(py_type, db_type)
            if adapter:
                suggestions[py_type] = (adapter, db_type)
            else:
                self.logger.debug(f"No adapter found for ({py_type.__name__}, {db_type.__name__}).")

        self._default_suggestions_cache = suggestions
        return suggestions

    @property
    def pragmas(self) -> Dict[str, str]:
        """Get current pragma settings."""
        return self.config.pragmas.copy()

    def _handle_sqlite_error(self, error: Exception) -> None:
        """Handle SQLite-specific errors and convert to appropriate exceptions."""
        error_msg = str(error)

        if isinstance(error, sqlite3.Error):
            if isinstance(error, sqlite3.OperationalError):
                if "database is locked" in error_msg:
                    self.log(logging.ERROR, f"Database lock error: {error_msg}")
                    raise OperationalError("Database is locked") from error
                elif "no such table" in error_msg:
                    self.log(logging.ERROR, f"Table not found: {error_msg}")
                    raise QueryError(f"Table not found: {error_msg}") from error
                self.log(logging.ERROR, f"SQLite operational error: {error_msg}")
                raise OperationalError(error_msg) from error
            elif isinstance(error, sqlite3.IntegrityError):
                if "UNIQUE constraint failed" in error_msg:
                    self.log(logging.ERROR, f"Unique constraint violation: {error_msg}")
                    raise IntegrityError(f"Unique constraint violation: {error_msg}") from error
                elif "FOREIGN KEY constraint failed" in error_msg:
                    self.log(logging.ERROR, f"Foreign key constraint violation: {error_msg}")
                    raise IntegrityError(f"Foreign key constraint violation: {error_msg}") from error
                self.log(logging.ERROR, f"SQLite integrity error: {error_msg}")
                raise IntegrityError(error_msg) from error
            elif "database is locked" in error_msg:
                self.log(logging.ERROR, f"Database deadlock: {error_msg}")
                raise DeadlockError(error_msg) from error
            elif isinstance(error, ProgrammingError):
                self.log(logging.ERROR, f"SQLite programming error: {error_msg}")
                raise DatabaseError(error_msg) from error
            else:
                self.log(logging.ERROR, f"Unhandled SQLite error: {error_msg}")
                raise DatabaseError(f"Unhandled SQLite error: {error_msg}") from error
        else:
            self.log(logging.ERROR, f"Unhandled non-SQLite error: {error_msg}")
            raise error

    def _is_select_statement(self, stmt_type: str) -> bool:
        """Check if statement is a SELECT-like query."""
        return stmt_type in ("SELECT", "EXPLAIN", "PRAGMA", "ANALYZE")

    def _convert_params(self, params: Union[Dict[str, Any], Tuple, List]) -> Union[Tuple, List]:
        """Convert parameters for SQLite."""
        if isinstance(params, dict):
            return tuple(params.values())
        return params

    def _prepare_sql_and_params(self, sql: str, params: Optional[Union[Tuple, Dict, List]]) -> Tuple[str, Tuple]:
        """Prepare SQL and parameters."""
        if isinstance(params, dict):
            final_params = tuple(params.values()) if params else ()
        elif isinstance(params, (tuple, list)):
            final_params = tuple(params) if params else ()
        else:
            final_params = params or ()
        return sql, final_params

    def _build_query_result(self, cursor, data, duration: float):
        """Build QueryResult from cursor, data and duration."""
        from rhosocial.activerecord.backend.result import QueryResult

        if data is not None:
            affected_rows = len(data) if data else 0
            last_insert_id = getattr(cursor, "lastrowid", None)
        else:
            affected_rows = cursor.rowcount
            last_insert_id = getattr(cursor, "lastrowid", None)

        return QueryResult(data=data, affected_rows=affected_rows, last_insert_id=last_insert_id, duration=duration)

    def is_connected(self) -> bool:
        """Check if connected to database.

        This is a non-I/O operation that checks the connection state.

        Returns:
            True if connection is established, False otherwise.
        """
        return self._connection is not None


class SQLiteConcurrencyMixin:
    """Mixin providing SQLite-specific concurrency hint."""

    def get_concurrency_hint(self) -> ConcurrencyHint:
        return ConcurrencyHint(
            max_concurrency=1,
            reason="SQLite file-level write lock; concurrent writes serialize",
        )
