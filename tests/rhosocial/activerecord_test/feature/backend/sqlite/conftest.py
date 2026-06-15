# tests/rhosocial/activerecord_test/feature/backend/sqlite/conftest.py
"""
Pytest fixtures for SQLite backend tests.
"""

import os
import tempfile
from typing import Generator

import pytest

from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "requires_functions(functions): Skip test if the backend dialect "
        "does not support the required functions. "
        "Usage: @pytest.mark.requires_functions(['json_extract_text'])",
    )
    config.addinivalue_line(
        "markers",
        "requires_protocol(protocol_and_method): Skip test if the backend "
        "dialect does not support the required protocol or method. "
        "Usage: @pytest.mark.requires_protocol((None, 'supports_fts5'))",
    )


def _get_backend_from_item(item):
    """Resolve the backend fixture value from a pytest Item."""
    backend = item.funcargs.get("backend")
    if backend is not None:
        return backend
    # Fallback: class-level fixture cache
    try:
        fixture_defs = item._fixtureinfo.name2fixturedefs.get("backend", [])
        if fixture_defs:
            return fixture_defs[0].cached_result[0]
    except (AttributeError, IndexError):
        pass
    return None


def _process_requires_functions(item, backend):
    """Process requires_functions marker and skip if unsupported."""
    marker = item.get_closest_marker("requires_functions")
    if marker is None:
        return True

    required_functions = marker.args[0] if marker.args else []
    if not required_functions:
        return True

    dialect = backend.dialect
    supported = dialect.supports_functions()
    unsupported = [fn for fn in required_functions if not supported.get(fn, False)]
    if unsupported:
        pytest.skip(
            f"Skipping test - backend dialect does not support "
            f"required functions: {', '.join(unsupported)}"
        )
    return True


def _process_requires_protocol(item, backend):
    """Process requires_protocol marker and skip if unsupported."""
    marker = item.get_closest_marker("requires_protocol")
    if marker is None:
        return True

    protocol_class, method_name = marker.args[0] if marker.args else (None, None)
    dialect = backend.dialect

    if protocol_class is not None and not isinstance(dialect, protocol_class):
        pytest.skip(
            f"Skipping test - backend dialect does not implement "
            f"{protocol_class.__name__}"
        )

    if method_name is not None:
        method = getattr(dialect, method_name, None)
        if method is None or (callable(method) and not method()):
            readable = method_name.replace("supports_", "").replace("_", " ").title()
            pytest.skip(
                f"Skipping test - backend dialect does not support {readable}"
            )

    return True


def pytest_runtest_call(item):
    """Process requires_functions and requires_protocol markers."""
    if not item.get_closest_marker("requires_functions") and not item.get_closest_marker("requires_protocol"):
        return

    backend = _get_backend_from_item(item)
    if backend is None:
        return

    _process_requires_functions(item, backend)
    _process_requires_protocol(item, backend)


@pytest.fixture
def sqlite_file_backend() -> Generator[SQLiteBackend, None, None]:
    """Create a file-based SQLite backend for tests requiring real files."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    backend = SQLiteBackend(database=db_path)
    backend.connect()
    backend.introspect_and_adapt()

    yield backend

    backend.disconnect()
    if os.path.exists(db_path):
        os.unlink(db_path)
