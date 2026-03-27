# src/rhosocial/activerecord/backend/introspection/executor.py
"""
Introspector executor abstractions.

Executors decouple the Introspector from sync/async execution details.
The Introspector generates SQL; the executor runs it against the backend.

Design principle: Sync and Async are separate and cannot coexist.
- SyncIntrospectorExecutor: for synchronous backends
- AsyncIntrospectorExecutor: for asynchronous backends
"""

from typing import Any, Dict, List, Tuple


class SyncIntrospectorExecutor:
    """Executor that wraps a synchronous backend.

    This executor is used by SyncAbstractIntrospector to execute SQL
    statements synchronously against the backend.
    """

    def __init__(self, backend: Any) -> None:
        self._backend = backend

    def execute(self, sql: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """Execute SQL synchronously and return rows as a list of dicts.

        Args:
            sql: SQL statement to execute.
            params: Positional parameters for the statement.

        Returns:
            List of rows, each represented as a column-name → value dict.
        """
        cursor = self._backend._get_cursor()
        try:
            cursor.execute(sql, params)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            cursor.close()


class AsyncIntrospectorExecutor:
    """Executor that wraps an asynchronous backend.

    This executor is used by AsyncAbstractIntrospector to execute SQL
    statements asynchronously against the backend.
    """

    def __init__(self, backend: Any) -> None:
        self._backend = backend

    async def execute(self, sql: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """Execute SQL asynchronously and return rows as a list of dicts.

        Args:
            sql: SQL statement to execute.
            params: Positional parameters for the statement.

        Returns:
            List of rows, each represented as a column-name → value dict.
        """
        cursor = await self._backend._get_cursor()
        try:
            await cursor.execute(sql, params)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = await cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
        finally:
            await cursor.close()
