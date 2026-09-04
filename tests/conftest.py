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


def _install_aiosqlite_closed_loop_guard() -> None:
    """Harden the aiosqlite worker thread against closed event loops.

    When an async test ends while an operation is still in flight, the
    function-scoped loop is closed before the aiosqlite worker thread
    processes the queued item; its ``call_soon_threadsafe`` delivery then
    raises 'Event loop is closed', which pytest reports as a flaky
    PytestUnhandledThreadExceptionWarning attributed to whichever test
    happens to run next.

    This mirrors aiosqlite's worker loop (same queue semantics, same stop
    sentinel) and guards each delivery with ``loop.is_closed()``: results
    for dead loops are dropped instead of crashing the thread. Threaded
    builds (3.13t/3.14t/3.15t) are especially prone to the race, which is
    why the guard ships for every job rather than behind a marker.
    """
    try:
        import aiosqlite.core
    except ImportError:  # pragma: no cover
        return

    core = aiosqlite.core
    worker = getattr(core, "_connection_worker_thread", None)
    if worker is None:
        # aiosqlite < 0.21 ships a different worker layout; guard not applicable.
        return

    if getattr(worker, "_closed_loop_guard", False):
        return

    set_result = core.set_result
    set_exception = core.set_exception
    stop_sentinel = core._STOP_RUNNING_SENTINEL

    def _guarded_worker_thread(tx):
        while True:
            future, function = tx.get()
            try:
                result = function()
                if future:
                    loop = future.get_loop()
                    if not loop.is_closed():
                        loop.call_soon_threadsafe(set_result, future, result)
                if result is stop_sentinel:
                    break
            except BaseException as e:  # noqa: B036 - mirror aiosqlite
                if future:
                    loop = future.get_loop()
                    if not loop.is_closed():
                        loop.call_soon_threadsafe(set_exception, future, e)

    _guarded_worker_thread._closed_loop_guard = True
    core._connection_worker_thread = _guarded_worker_thread


def pytest_configure(config):
    """Install test-environment guards for the whole run."""
    _install_aiosqlite_closed_loop_guard()

    try:
        from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
    except ImportError:  # pragma: no cover - core backend always present here
        return

    @pytest.fixture(autouse=True)
    def _reap_abandoned_async_backends():
        """Disconnect async backends still connected at test teardown.

        A backend still connected after its test means the owner forgot to
        disconnect; the reap makes the leak attributable to *this* test
        (via the warning below) instead of a random later one, and stops
        the worker thread cleanly.
        """
        yield
        for backend in AsyncSQLiteBackend.iter_live_backends():
            import warnings

            warnings.warn(
                "AsyncSQLiteBackend left connected; disconnected by test harness",
                ResourceWarning,
                stacklevel=1,
            )
            backend.close_sync()
