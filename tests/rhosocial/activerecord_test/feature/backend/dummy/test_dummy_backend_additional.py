"""
Additional test suite for DummyBackend to cover remaining uncovered lines.
"""
import pytest
from rhosocial.activerecord.backend.impl.dummy.backend import AsyncDummyBackend
from rhosocial.activerecord.backend.errors import DatabaseError


class TestAsyncDummyBackendRemaining:
    """Tests for remaining uncovered lines in AsyncDummyBackend."""

    @pytest.mark.asyncio
    async def test_async_dummy_backend_initialize_capabilities(self):
        """Test AsyncDummyBackend._initialize_capabilities method."""
        backend = AsyncDummyBackend()
        capabilities = backend._initialize_capabilities()
        # This tests the method at line 94-96 in backend.py
        assert capabilities is not None

    @pytest.mark.asyncio
    async def test_async_dummy_backend_handle_error_with_not_implemented_error(self):
        """Test AsyncDummyBackend._handle_error with NotImplementedError."""
        backend = AsyncDummyBackend()
        error = NotImplementedError("Test error")
        with pytest.raises(NotImplementedError):
            await backend._handle_error(error)

    @pytest.mark.asyncio
    async def test_async_dummy_backend_handle_error_with_other_error(self):
        """Test AsyncDummyBackend._handle_error with other error."""
        backend = AsyncDummyBackend()
        error = ValueError("Test error")
        with pytest.raises(DatabaseError):
            await backend._handle_error(error)

    def test_async_dummy_backend_transaction_manager_property(self):
        """Test AsyncDummyBackend.transaction_manager property raises NotImplementedError."""
        backend = AsyncDummyBackend()
        with pytest.raises(NotImplementedError) as excinfo:
            _ = backend.transaction_manager
        assert "does not support real database operations" in str(excinfo.value)