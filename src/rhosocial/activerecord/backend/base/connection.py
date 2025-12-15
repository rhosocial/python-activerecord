# src/rhosocial/activerecord/backend/base/connection.py
from typing import Any

class ConnectionMixin:
    """Mixin for synchronous connection and context management."""
    @property
    def connection(self) -> Any:
        if self._connection is None:
            self.connect()
        return self._connection
    def __enter__(self):
        if not self._connection:
            self.connect()
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
    def __del__(self):
        self.disconnect()

class AsyncConnectionMixin:
    """Mixin for asynchronous connection and context management."""
    @property
    async def connection(self) -> Any:
        if self._connection is None:
            await self.connect()
        return self._connection
    async def __aenter__(self):
        if not self._connection:
            await self.connect()
        return self
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()