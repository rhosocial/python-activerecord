# tests/rhosocial/activerecord_test/feature/backend/base/test_transaction.py
import pytest
import logging
from unittest.mock import MagicMock, AsyncMock, patch
from rhosocial.activerecord.backend.transaction import (
    TransactionManager,
    AsyncTransactionManager,
    IsolationLevel,
)
from rhosocial.activerecord.backend.errors import TransactionError, IsolationLevelError


class ConcreteTransactionManager(TransactionManager):
    def _do_begin(self) -> None: pass
    def _do_commit(self) -> None: pass
    def _do_rollback(self) -> None: pass
    def _do_create_savepoint(self, name: str) -> None: pass
    def _do_release_savepoint(self, name: str) -> None: pass
    def _do_rollback_savepoint(self, name: str) -> None: pass
    def supports_savepoint(self) -> bool: return True

class ConcreteAsyncTransactionManager(AsyncTransactionManager):
    async def _do_begin(self) -> None: pass
    async def _do_commit(self) -> None: pass
    async def _do_rollback(self) -> None: pass
    async def _do_create_savepoint(self, name: str) -> None: pass
    async def _do_release_savepoint(self, name: str) -> None: pass
    async def _do_rollback_savepoint(self, name: str) -> None: pass
    async def supports_savepoint(self) -> bool: return True


class TestTransactionManagerBase:
    @pytest.fixture
    def manager(self):
        return ConcreteTransactionManager(MagicMock())

    def test_logger_property(self, manager):
        """Tests the logger property setter."""
        new_logger = logging.getLogger("new_logger")
        manager.logger = new_logger
        assert manager.logger is new_logger

        manager.logger = None
        assert manager.logger.name == 'transaction'

        with pytest.raises(ValueError, match="logger must be an instance of logging.Logger"):
            manager.logger = "not a logger"

    def test_is_active(self, manager):
        """Tests the is_active property."""
        assert manager.is_active is False
        manager._transaction_level = 1
        assert manager.is_active is True

    def test_set_isolation_level_while_active_raises_error(self, manager):
        """Tests that setting isolation level during a transaction raises an error."""
        manager.begin()
        with pytest.raises(IsolationLevelError):
            manager.isolation_level = IsolationLevel.READ_COMMITTED
        manager.rollback()


class TestTransactionManager(TestTransactionManagerBase):
    @pytest.fixture
    def manager(self):
        return ConcreteTransactionManager(MagicMock())

    def test_commit_no_active_transaction(self, manager):
        """Tests committing without an active transaction raises an error."""
        with pytest.raises(TransactionError, match="No active transaction to commit"):
            manager.commit()

    def test_rollback_no_active_transaction(self, manager):
        """Tests rolling back without an active transaction raises an error."""
        with pytest.raises(TransactionError, match="No active transaction to rollback"):
            manager.rollback()

    def test_savepoint_no_active_transaction(self, manager):
        """Tests creating a savepoint without an active transaction raises an error."""
        with pytest.raises(TransactionError, match="Cannot create savepoint: no active transaction"):
            manager.savepoint()

    def test_release_invalid_savepoint(self, manager):
        """Tests releasing an invalid savepoint raises an error."""
        manager.begin()
        with pytest.raises(TransactionError, match="Invalid savepoint name: invalid_sp"):
            manager.release("invalid_sp")
        manager.rollback()

    def test_rollback_to_invalid_savepoint(self, manager):
        """Tests rolling back to an invalid savepoint raises an error."""
        manager.begin()
        with pytest.raises(TransactionError, match="Invalid savepoint name: invalid_sp"):
            manager.rollback_to("invalid_sp")
        manager.rollback()

    def test_transaction_context_manager_exception(self, manager):
        """Tests the transaction context manager rolls back on exception."""
        with patch.object(manager, '_do_rollback') as mock_rollback:
            with pytest.raises(ValueError, match="Test exception"):
                with manager.transaction():
                    raise ValueError("Test exception")
            mock_rollback.assert_called_once()

    def test_nested_transaction_commit_no_savepoint(self, manager):
        """Tests committing a nested transaction when no savepoint is available."""
        manager.begin()
        manager._transaction_level = 2 # Manually simulate nested state
        with patch.object(manager, '_do_release_savepoint') as mock_release:
            manager.commit()
            mock_release.assert_not_called()
        manager.rollback()

    def test_nested_transaction_rollback_no_savepoint(self, manager):
        """Tests rolling back a nested transaction when no savepoint is available."""
        manager.begin()
        manager._transaction_level = 2 # Manually simulate nested state
        with patch.object(manager, '_do_rollback_savepoint') as mock_rollback:
            manager.rollback()
            mock_rollback.assert_not_called()
        manager.rollback()

class TestAsyncTransactionManager:
    @pytest.fixture
    def async_manager(self):
        return ConcreteAsyncTransactionManager(AsyncMock())

    @pytest.mark.asyncio
    async def test_commit_no_active_transaction(self, async_manager):
        """Tests async committing without an active transaction raises an error."""
        with pytest.raises(TransactionError, match="No active transaction to commit"):
            await async_manager.commit()

    @pytest.mark.asyncio
    async def test_rollback_no_active_transaction(self, async_manager):
        """Tests async rolling back without an active transaction raises an error."""
        with pytest.raises(TransactionError, match="No active transaction to rollback"):
            await async_manager.rollback()

    @pytest.mark.asyncio
    async def test_savepoint_no_active_transaction(self, async_manager):
        """Tests async creating a savepoint without an active transaction raises an error."""
        with pytest.raises(TransactionError, match="Cannot create savepoint: no active transaction"):
            await async_manager.savepoint()

    @pytest.mark.asyncio
    async def test_release_invalid_savepoint(self, async_manager):
        """Tests async releasing an invalid savepoint raises an error."""
        await async_manager.begin()
        with pytest.raises(TransactionError, match="Invalid savepoint name: invalid_sp"):
            await async_manager.release("invalid_sp")
        await async_manager.rollback()

    @pytest.mark.asyncio
    async def test_rollback_to_invalid_savepoint(self, async_manager):
        """Tests async rolling back to an invalid savepoint raises an error."""
        await async_manager.begin()
        with pytest.raises(TransactionError, match="Invalid savepoint name: invalid_sp"):
            await async_manager.rollback_to("invalid_sp")
        await async_manager.rollback()

    @pytest.mark.asyncio
    async def test_transaction_context_manager_exception(self, async_manager):
        """Tests the async transaction context manager rolls back on exception."""
        with patch.object(async_manager, '_do_rollback') as mock_rollback:
            with pytest.raises(ValueError, match="Test exception"):
                async with async_manager.transaction():
                    raise ValueError("Test exception")
            mock_rollback.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_nested_transaction_commit_no_savepoint(self, async_manager):
        """Tests async committing a nested transaction when no savepoint is available."""
        await async_manager.begin()
        async_manager._transaction_level = 2 # Manually simulate nested state
        with patch.object(async_manager, '_do_release_savepoint') as mock_release:
            await async_manager.commit()
            mock_release.assert_not_called()
        await async_manager.rollback()

    @pytest.mark.asyncio
    async def test_nested_transaction_rollback_no_savepoint(self, async_manager):
        """Tests async rolling back a nested transaction when no savepoint is available."""
        await async_manager.begin()
        async_manager._transaction_level = 2 # Manually simulate nested state
        with patch.object(async_manager, '_do_rollback_savepoint') as mock_rollback:
            await async_manager.rollback()
            mock_rollback.assert_not_called()
        await async_manager.rollback()
