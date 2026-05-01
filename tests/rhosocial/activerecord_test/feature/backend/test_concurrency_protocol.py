# tests/rhosocial/activerecord_test/feature/backend/test_concurrency_protocol.py
"""
Test for ConcurrencyAware protocol implementation.

This test verifies that the ConcurrencyAware protocol and ConcurrencyAwareMixin
work correctly for backend implementations.
"""
import pytest

from rhosocial.activerecord.backend.protocols import ConcurrencyAware, ConcurrencyHint
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend


class TestConcurrencyAwareProtocol:
    """Test ConcurrencyAware protocol implementation."""

    def test_sqlite_backend_implements_protocol(self):
        """Test that SQLiteBackend implements ConcurrencyAware protocol."""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = SQLiteBackend(connection_config=config)
        backend.connect()

        assert isinstance(backend, ConcurrencyAware)
        assert hasattr(backend, "get_concurrency_hint")

        backend.disconnect()

    def test_sqlite_get_concurrency_hint(self):
        """Test SQLiteBackend returns correct concurrency hint."""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = SQLiteBackend(connection_config=config)
        backend.connect()

        hint = backend.get_concurrency_hint()

        assert isinstance(hint, ConcurrencyHint)
        assert hint.max_concurrency == 1
        assert "SQLite" in hint.reason

        backend.disconnect()

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