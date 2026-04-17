# src/rhosocial/activerecord/backend/base/connection.py
from contextlib import contextmanager, asynccontextmanager
from typing import Any, Generator


class ConnectionMixin:
    """
    Mixin for synchronous connection and context management.

    This mixin provides standard connection lifecycle management methods
    for synchronous backends. It handles automatic connection establishment
    and cleanup through property access and context manager protocols.
    """

    @property
    def connection(self) -> Any:
        """
        Gets the active database connection, connecting if necessary.

        This property provides lazy connection establishment. If no connection
        exists, it automatically establishes one before returning the connection
        object. This ensures that a valid connection is always available when
        accessed.

        Returns:
            The active database connection object for the backend.
        """
        if self._connection is None:
            self.connect()
        return self._connection

    def __enter__(self):
        """
        Context manager entry method for synchronous operations.

        Establishes a connection if one doesn't exist and returns the backend
        instance for use in 'with' statements. This enables automatic connection
        management in synchronous contexts.

        Returns:
            The backend instance for use within the context block.
        """
        if not self._connection:
            self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit method for synchronous operations.

        Cleans up the connection when exiting a 'with' statement. This ensures
        that connections are properly closed even if exceptions occur within
        the context block.

        Args:
            exc_type: Exception type if an exception occurred, None otherwise
            exc_val: Exception instance if an exception occurred, None otherwise
            exc_tb: Exception traceback if an exception occurred, None otherwise
        """
        self.disconnect()

    @contextmanager
    def context(self) -> Generator['ConnectionMixin', None, None]:
        """
        Context manager for explicit connection lifecycle control.

        Establishes a connection on context entry and disconnects on context exit.
        This ensures the connection is created and destroyed in the same thread,
        avoiding cross-thread SQLite connection issues.

        After connecting, introspect_and_adapt() is called to ensure the dialect
        is properly configured based on the actual database server capabilities.

        The connection backend is also set in a context variable, enabling
        request-level isolation in concurrent environments (e.g., web frameworks).
        ``model.backend()`` will resolve to this instance via the context variable
        rather than the class-level ``__backend__`` fallback.

        Usage:
            with backend.context() as ctx:
                result = ctx.execute("SELECT 1")

        Yields:
            The backend instance for use within the context block.
        """
        from ...connection.pool.context import (
            _set_connection_backend,
            _reset_connection_backend,
        )

        token = _set_connection_backend(self)
        try:
            self.connect()
            try:
                # Ensure dialect is properly configured based on actual server capabilities
                self.introspect_and_adapt()
                yield self
            finally:
                self.disconnect()
        finally:
            _reset_connection_backend(token)

    def __del__(self):
        """
        Destructor to ensure connection cleanup when object is garbage collected.

        This method attempts to disconnect the database connection when the
        backend instance is being destroyed. It serves as a safety net to
        prevent connection leaks, though explicit disconnection is preferred.

        Note:
            Only performs cleanup if connection is active to avoid logging
            errors during Python interpreter shutdown when stdout/stderr may
            already be closed.
        """
        # Only disconnect if connection is active to avoid logging errors
        # during interpreter shutdown
        if hasattr(self, '_connection') and self._connection is not None:
            try:
                self.disconnect()
            except Exception:
                # Silently ignore any errors during garbage collection
                pass


class AsyncConnectionMixin:
    """
    Mixin for asynchronous connection and context management.

    This mixin provides standard connection lifecycle management methods
    for asynchronous backends. It handles automatic connection establishment
    and cleanup through async property access and async context manager protocols.
    """

    @property
    async def connection(self) -> Any:
        """
        Gets the active database connection asynchronously, connecting if necessary.

        This async property provides lazy connection establishment for asynchronous
        backends. If no connection exists, it asynchronously establishes one before
        returning the connection object. This ensures that a valid connection is
        always available when accessed in async contexts.

        Returns:
            The active database connection object for the async backend.
        """
        if self._connection is None:
            await self.connect()
        return self._connection

    async def __aenter__(self):
        """
        Async context manager entry method for asynchronous operations.

        Asynchronously establishes a connection if one doesn't exist and returns
        the backend instance for use in 'async with' statements. This enables
        automatic connection management in asynchronous contexts.

        Returns:
            The backend instance for use within the async context block.
        """
        if not self._connection:
            await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Async context manager exit method for asynchronous operations.

        Asynchronously cleans up the connection when exiting an 'async with'
        statement. This ensures that connections are properly closed even if
        exceptions occur within the async context block.

        Args:
            exc_type: Exception type if an exception occurred, None otherwise
            exc_val: Exception instance if an exception occurred, None otherwise
            exc_tb: Exception traceback if an exception occurred, None otherwise
        """
        await self.disconnect()

    @asynccontextmanager
    async def context(self) -> Generator['AsyncConnectionMixin', None, None]:
        """
        Async context manager for explicit connection lifecycle control.

        Establishes a connection on context entry and disconnects on context exit.
        This ensures the connection is created and destroyed in the same async context,
        avoiding cross-thread/cross-task SQLite connection issues.

        After connecting, introspect_and_adapt() is called to ensure the dialect
        is properly configured based on the actual database server capabilities.

        The connection backend is also set in a context variable, enabling
        request-level isolation in concurrent async environments (e.g., FastAPI).
        ``model.backend()`` will resolve to this instance via the context variable
        rather than the class-level ``__backend__`` fallback, which is critical
        when multiple async requests share the same event loop.

        Usage:
            async with backend.context() as ctx:
                result = await ctx.execute("SELECT 1")

        Yields:
            The backend instance for use within the context block.
        """
        from ...connection.pool.context import (
            _set_async_connection_backend,
            _reset_async_connection_backend,
        )

        token = _set_async_connection_backend(self)
        try:
            await self.connect()
            try:
                # Ensure dialect is properly configured based on actual server capabilities
                await self.introspect_and_adapt()
                yield self
            finally:
                await self.disconnect()
        finally:
            _reset_async_connection_backend(token)
