# src/.../test_capability_integration.py
"""Integration tests for dialect protocol-based capability detection."""

import pytest

pytestmark = [pytest.mark.feature, pytest.mark.backend]

PROTOCOLS_PKG = "rhosocial.activerecord.backend.dialect.protocols"


def test_sqlite_dialect_window_protocol(sqlite_backend):
    """Test that SQLite dialect implements WindowFunctionSupport protocol."""
    WindowFunctionSupport = _get_protocol("WindowFunctionSupport")
    dialect = sqlite_backend.dialect
    assert isinstance(dialect, WindowFunctionSupport)
    assert dialect.supports_window_functions() is True


def test_sqlite_dialect_cte_protocol(sqlite_backend):
    """Test that SQLite dialect implements CTESupport protocol."""
    CTESupport = _get_protocol("CTESupport")
    dialect = sqlite_backend.dialect
    assert isinstance(dialect, CTESupport)
    assert dialect.supports_basic_cte() is True


def test_sqlite_dialect_returning_protocol(sqlite_backend):
    """Test that SQLite dialect implements ReturningSupport protocol."""
    ReturningSupport = _get_protocol("ReturningSupport")
    dialect = sqlite_backend.dialect
    assert isinstance(dialect, ReturningSupport)


def test_sqlite_dialect_json_protocol(sqlite_backend):
    """Test that SQLite dialect implements JSONSupport protocol (might be runtime-dependent)."""
    JSONSupport = _get_protocol("JSONSupport")
    dialect = sqlite_backend.dialect
    assert isinstance(dialect, JSONSupport)


def test_dummy_dialect_protocol_checks(dummy_backend):
    """Test that dummy dialect implements default protocol checks."""
    WindowFunctionSupport = _get_protocol("WindowFunctionSupport")
    CTESupport = _get_protocol("CTESupport")
    ReturningSupport = _get_protocol("ReturningSupport")
    JSONSupport = _get_protocol("JSONSupport")
    dialect = dummy_backend.dialect
    assert isinstance(dialect, WindowFunctionSupport)
    assert isinstance(dialect, CTESupport)
    assert isinstance(dialect, ReturningSupport)
    assert isinstance(dialect, JSONSupport)


def test_dialect_supports_boolean_results(sqlite_backend):
    """Test that dialect supports_* methods return boolean values."""
    dialect = sqlite_backend.dialect
    checks = [
        ("supports_window_functions", True),
        ("supports_window_frame_clause", True),
        ("supports_basic_cte", True),
        ("supports_returning_clause", True),
    ]
    for method_name, expected in checks:
        if hasattr(dialect, method_name):
            result = getattr(dialect, method_name)()
            assert isinstance(result, bool), f"{method_name} should return bool"
            assert result is expected, f"{method_name} expected {expected}, got {result}"


def test_dummy_dialect_introspection_disabled(dummy_backend):
    """Test that dummy dialect introspection features are disabled."""
    dialect = dummy_backend.dialect
    if hasattr(dialect, "supports_procedures"):
        result = dialect.supports_procedures()
        assert result is False, "supports_procedures should be False"


def _get_protocol(name):
    import importlib
    mod = importlib.import_module(PROTOCOLS_PKG)
    return getattr(mod, name)


@pytest.fixture
def sqlite_backend():
    from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
    backend = SQLiteBackend(database=":memory:")
    backend.connect()
    backend.introspect_and_adapt()
    return backend


@pytest.fixture
def dummy_backend():
    from rhosocial.activerecord.backend.impl.dummy import DummyBackend
    return DummyBackend()