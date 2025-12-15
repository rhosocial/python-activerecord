# src/rhosocial/activerecord/backend/base/transaction_management.py
import logging
from abc import abstractmethod
from contextlib import contextmanager, asynccontextmanager
from typing import Generator, AsyncGenerator
from ..transaction import TransactionManager, AsyncTransactionManager

class TransactionManagementMixin:
    """Mixin for synchronous transaction management convenience methods."""
    @property
    @abstractmethod
    def transaction_manager(self) -> TransactionManager: ...
    def begin_transaction(self) -> None:
        self.log(logging.INFO, "Beginning transaction")
        self.transaction_manager.begin()
    def commit_transaction(self) -> None:
        self.log(logging.INFO, "Committing transaction")
        self.transaction_manager.commit()
    def rollback_transaction(self) -> None:
        self.log(logging.INFO, "Rolling back transaction")
        self.transaction_manager.rollback()
    @property
    def in_transaction(self) -> bool:
        is_active = self.transaction_manager.is_active if self._transaction_manager else False
        self.log(logging.DEBUG, f"Checking transaction status: {is_active}")
        return is_active
    @contextmanager
    def transaction(self) -> Generator[None, None, None]:
        with self.transaction_manager.transaction() as t:
            yield t

class AsyncTransactionManagementMixin:
    """Mixin for asynchronous transaction management convenience methods."""
    @property
    @abstractmethod
    def transaction_manager(self) -> AsyncTransactionManager: ...
    async def begin_transaction(self) -> None:
        await self.transaction_manager.begin()
    async def commit_transaction(self) -> None:
        await self.transaction_manager.commit()
    async def rollback_transaction(self) -> None:
        await self.transaction_manager.rollback()
    @property
    def in_transaction(self) -> bool:
        is_active = self.transaction_manager.is_active if self._transaction_manager else False
        self.log(logging.DEBUG, f"Checking transaction status: {is_active}")
        return is_active
    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[None, None]:
        await self.begin_transaction()
        try:
            yield
        except Exception:
            await self.rollback_transaction()
            raise
        else:
            await self.commit_transaction()