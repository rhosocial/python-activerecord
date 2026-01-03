# tests/rhosocial/activerecord_test/feature/backend/base/test_hooks.py

import pytest
from unittest.mock import MagicMock, AsyncMock

from rhosocial.activerecord.backend.base.hooks import ExecutionHooksMixin, AsyncExecutionHooksMixin

# --- Tests for ExecutionHooksMixin ---

class TestExecutionHooksMixin:

    @pytest.fixture
    def mixin_instance(self):
        """Creates an instance of a class that uses ExecutionHooksMixin for testing."""
        class TestClass(ExecutionHooksMixin):
            def __init__(self):
                self._connection = MagicMock()
                self._cursor = None
                self.in_transaction = False
                self._handle_error = MagicMock()
                self._handle_auto_commit = MagicMock()

        return TestClass()

    def test_get_cursor_new(self, mixin_instance):
        """Tests _get_cursor when no cursor exists."""
        mixin_instance._connection.cursor.return_value = "new_cursor"
        cursor = mixin_instance._get_cursor()
        assert cursor == "new_cursor"
        mixin_instance._connection.cursor.assert_called_once()

    def test_get_cursor_existing(self, mixin_instance):
        """Tests _get_cursor when a cursor already exists."""
        mixin_instance._cursor = "existing_cursor"
        cursor = mixin_instance._get_cursor()
        assert cursor == "existing_cursor"
        mixin_instance._connection.cursor.assert_not_called()

    def test_execute_query_with_params(self):
        """Tests _execute_query with parameters."""
        mixin = ExecutionHooksMixin()
        mock_cursor = MagicMock()
        mixin._execute_query(mock_cursor, "SELECT * FROM test WHERE id = ?", (1,))
        mock_cursor.execute.assert_called_once_with("SELECT * FROM test WHERE id = ?", (1,))

    def test_execute_query_without_params(self):
        """Tests _execute_query without parameters."""
        mixin = ExecutionHooksMixin()
        mock_cursor = MagicMock()
        mixin._execute_query(mock_cursor, "SELECT * FROM test", None)
        mock_cursor.execute.assert_called_once_with("SELECT * FROM test")

    def test_handle_auto_commit_if_needed_in_transaction(self, mixin_instance):
        """Tests _handle_auto_commit_if_needed when in a transaction."""
        mixin_instance.in_transaction = True
        mixin_instance._handle_auto_commit_if_needed()
        mixin_instance._handle_auto_commit.assert_not_called()

    def test_handle_auto_commit_if_needed_not_in_transaction(self, mixin_instance):
        """Tests _handle_auto_commit_if_needed when not in a transaction."""
        mixin_instance.in_transaction = False
        mixin_instance._handle_auto_commit_if_needed()
        mixin_instance._handle_auto_commit.assert_called_once()

    def test_handle_execution_error(self, mixin_instance):
        """Tests that _handle_execution_error calls _handle_error."""
        error = ValueError("Test Error")
        mixin_instance._handle_execution_error(error)
        mixin_instance._handle_error.assert_called_once_with(error)

# --- Tests for AsyncExecutionHooksMixin ---

class TestAsyncExecutionHooksMixin:

    @pytest.fixture
    def async_mixin_instance(self):
        """Creates an instance of a class that uses AsyncExecutionHooksMixin for testing."""
        class AsyncTestClass(AsyncExecutionHooksMixin):
            def __init__(self):
                self._connection = AsyncMock()
                self._cursor = None
                self.in_transaction = False
                self._handle_error = AsyncMock()
                self._handle_auto_commit = AsyncMock()

        return AsyncTestClass()

    @pytest.mark.asyncio
    async def test_get_cursor_new_async(self, async_mixin_instance):
        """Tests async _get_cursor when no cursor exists."""
        async_mixin_instance._connection.cursor.return_value = "new_async_cursor"
        cursor = await async_mixin_instance._get_cursor()
        assert cursor == "new_async_cursor"
        async_mixin_instance._connection.cursor.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cursor_existing_async(self, async_mixin_instance):
        """Tests async _get_cursor when a cursor already exists."""
        async_mixin_instance._cursor = "existing_async_cursor"
        cursor = await async_mixin_instance._get_cursor()
        assert cursor == "existing_async_cursor"
        async_mixin_instance._connection.cursor.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_query_with_params_async(self):
        """Tests async _execute_query with parameters."""
        mixin = AsyncExecutionHooksMixin()
        mock_cursor = AsyncMock()
        await mixin._execute_query(mock_cursor, "SELECT * FROM test WHERE id = ?", (1,))
        mock_cursor.execute.assert_called_once_with("SELECT * FROM test WHERE id = ?", (1,))

    @pytest.mark.asyncio
    async def test_execute_query_without_params_async(self):
        """Tests async _execute_query without parameters."""
        mixin = AsyncExecutionHooksMixin()
        mock_cursor = AsyncMock()
        await mixin._execute_query(mock_cursor, "SELECT * FROM test", None)
        mock_cursor.execute.assert_called_once_with("SELECT * FROM test")

    @pytest.mark.asyncio
    async def test_handle_auto_commit_if_needed_in_transaction_async(self, async_mixin_instance):
        """Tests async _handle_auto_commit_if_needed when in a transaction."""
        async_mixin_instance.in_transaction = True
        await async_mixin_instance._handle_auto_commit_if_needed()
        async_mixin_instance._handle_auto_commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_auto_commit_if_needed_not_in_transaction_async(self, async_mixin_instance):
        """Tests async _handle_auto_commit_if_needed when not in a transaction."""
        async_mixin_instance.in_transaction = False
        await async_mixin_instance._handle_auto_commit_if_needed()
        async_mixin_instance._handle_auto_commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_execution_error_async(self, async_mixin_instance):
        """Tests that async _handle_execution_error calls _handle_error."""
        error = ValueError("Test Error")
        await async_mixin_instance._handle_execution_error(error)
        async_mixin_instance._handle_error.assert_called_once_with(error)
