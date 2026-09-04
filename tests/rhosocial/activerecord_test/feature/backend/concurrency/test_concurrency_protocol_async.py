# tests/rhosocial/activerecord_test/feature/backend/concurrency/test_concurrency_protocol_async.py
"""
Async twin of test_concurrency_protocol.py: ConcurrencyAware protocol on AsyncSQLiteBackend.

get_concurrency_hint() is a sync mixin method shared by both backends; the
async twin drives it through an AsyncSQLiteBackend instance to prove the
protocol contract holds for the async backend as well.
"""

import pytest

from rhosocial.activerecord.backend.protocols import ConcurrencyAware, ConcurrencyHint
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend


class TestAsyncConcurrencyAwareProtocol:
    """Test ConcurrencyAware protocol implementation on AsyncSQLiteBackend."""

    @pytest.mark.asyncio
    async def test_sqlite_backend_implements_protocol(self):
        """Test that AsyncSQLiteBackend implements ConcurrencyAware protocol."""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()

        assert isinstance(backend, ConcurrencyAware)
        assert hasattr(backend, "get_concurrency_hint")

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_sqlite_get_concurrency_hint(self):
        """Test AsyncSQLiteBackend returns correct concurrency hint."""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()

        hint = backend.get_concurrency_hint()

        assert isinstance(hint, ConcurrencyHint)
        assert hint.max_concurrency == 1
        assert "SQLite" in hint.reason

        await backend.disconnect()

    def test_concurrency_hint_is_immutable(self):
        """Test ConcurrencyHint is a frozen dataclass."""
        hint = ConcurrencyHint(max_concurrency=1, reason="test")

        with pytest.raises(AttributeError):
            hint.max_concurrency = 2

    def test_concurrency_hint_default_reason(self):
        """Test ConcurrencyHint default reason is empty string."""
        hint = ConcurrencyHint(max_concurrency=1)
        assert hint.reason == ""

    def test_concurrency_hint_none_max(self):
        """Test ConcurrencyHint with max_concurrency=None."""
        hint = ConcurrencyHint(max_concurrency=None, reason="no limit")
        assert hint.max_concurrency is None
        assert hint.reason == "no limit"
