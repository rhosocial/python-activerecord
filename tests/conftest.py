# tests/conftest.py
"""
This is the root pytest configuration file for the rhosocial-activerecord package's test suite.

Its primary responsibility is to configure the environment so that the external
`rhosocial-activerecord-testsuite` can find and use the backend-specific
implementations (Providers) defined within this project.
"""

import os

# Set the environment variable that the testsuite uses to locate the provider registry.
# The testsuite is a generic package and doesn't know the specific location of the
# provider implementations for this backend (SQLite). This environment variable
# acts as a bridge, pointing the testsuite to the correct import path.
#
# `setdefault` is used to ensure that this value is set only if it hasn't been
# set already, allowing for overrides in different environments if needed.
os.environ.setdefault("TESTSUITE_PROVIDER_REGISTRY", "providers.registry:provider_registry")

import pytest


def pytest_configure(config):
    """Register the async-backend reap hook, if the async backend is importable."""
    try:
        from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
    except ImportError:  # pragma: no cover - core backend always present here
        return

    @pytest.fixture(autouse=True)
    def _reap_abandoned_async_backends():
        """Fail fast on async backends left connected across a test.

        A backend still connected at teardown means its owner forgot to
        disconnect; once this function-scoped loop closes, the aiosqlite
        worker thread crashes with 'Event loop is closed' (the source of
        the flaky PytestUnhandledThreadExceptionWarning in CI). Closing
        it here keeps the leak visible in *this* test instead of a
        random later one, and stops the worker thread cleanly.
        """
        yield
        for backend in AsyncSQLiteBackend.iter_live_backends():
            backend.close_sync()
