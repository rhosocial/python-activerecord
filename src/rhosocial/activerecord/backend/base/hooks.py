# src/rhosocial/activerecord/backend/base/hooks.py
from typing import Optional, Tuple

class ExecutionHooksMixin:
    """Mixin for synchronous execution hook methods."""
    def _get_cursor(self):
        """Get or create a cursor for query execution."""
        return self._cursor or self._connection.cursor()

    def _execute_query(self, cursor, sql: str, params: Optional[Tuple]):
        """Execute the query with prepared SQL and parameters."""
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        return cursor

    def _handle_auto_commit_if_needed(self) -> None:
        """Handle auto-commit if not in transaction."""
        if not self.in_transaction:
            self._handle_auto_commit()

    def _handle_auto_commit(self) -> None:
        """Handle auto commit (to be overridden by concrete backends)."""
        pass

    def _handle_execution_error(self, error: Exception):
        """Handle database-specific errors during query execution."""
        self._handle_error(error)


class AsyncExecutionHooksMixin:
    """Mixin for asynchronous execution hook methods."""
    async def _get_cursor(self):
        """Get or create a cursor asynchronously."""
        return self._cursor or await self._connection.cursor()

    async def _execute_query(self, cursor, sql: str, params: Optional[Tuple]):
        """Execute query asynchronously."""
        if params:
            await cursor.execute(sql, params)
        else:
            await cursor.execute(sql)
        return cursor

    async def _handle_auto_commit_if_needed(self) -> None:
        """Handle auto-commit asynchronously."""
        if not self.in_transaction:
            await self._handle_auto_commit()

    async def _handle_auto_commit(self) -> None:
        """Handle auto commit asynchronously (to be overridden)."""
        pass

    async def _handle_execution_error(self, error: Exception):
        """Handle database-specific errors during query execution."""
        await self._handle_error(error)
