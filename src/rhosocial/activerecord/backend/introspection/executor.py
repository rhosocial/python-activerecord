# src/rhosocial/activerecord/backend/introspection/executor.py
"""
Introspector executor abstractions.

Executors decouple the Introspector from sync/async execution details.
The Introspector generates SQL; the executor runs it against the backend.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple


class IntrospectorExecutor(ABC):
    """Abstract executor that runs SQL on behalf of an Introspector.

    The Introspector builds SQL via Expression+Dialect and delegates
    the actual execution here, keeping itself free of sync/async concerns.
    """

    @abstractmethod
    def execute(self, sql: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """Execute SQL synchronously and return rows as a list of dicts.

        Args:
            sql: SQL statement to execute.
            params: Positional parameters for the statement.

        Returns:
            List of rows, each represented as a column-name → value dict.

        Raises:
            TypeError: If this executor does not support synchronous execution.
        """
        ...

    @abstractmethod
    async def execute_async(self, sql: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """Execute SQL asynchronously and return rows as a list of dicts.

        Args:
            sql: SQL statement to execute.
            params: Positional parameters for the statement.

        Returns:
            List of rows, each represented as a column-name → value dict.

        Raises:
            TypeError: If this executor does not support asynchronous execution.
        """
        ...


class SyncIntrospectorExecutor(IntrospectorExecutor):
    """Executor that wraps a synchronous backend."""

    def __init__(self, backend: Any) -> None:
        self._backend = backend

    def execute(self, sql: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        cursor = self._backend._get_cursor()
        try:
            cursor.execute(sql, params)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            cursor.close()

    async def execute_async(self, sql: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        raise TypeError(
            "SyncIntrospectorExecutor does not support async execution. "
            "Use AsyncIntrospectorExecutor for async backends."
        )


class AsyncIntrospectorExecutor(IntrospectorExecutor):
    """Executor that wraps an asynchronous backend."""

    def __init__(self, backend: Any) -> None:
        self._backend = backend

    def execute(self, sql: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        raise TypeError(
            "AsyncIntrospectorExecutor does not support sync execution. "
            "Use SyncIntrospectorExecutor for sync backends."
        )

    async def execute_async(self, sql: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        cursor = await self._backend._get_cursor()
        try:
            await cursor.execute(sql, params)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = await cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
        finally:
            await cursor.close()
