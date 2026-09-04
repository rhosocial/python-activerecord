# tests/rhosocial/activerecord_test/feature/backend/backend/test_cursor_pollution.py
"""
Cursor result set pollution tests.

Verifies that after _detect_math_functions() / _detect_json1_extension()
close a cursor without fully consuming results, subsequent queries on
the same connection do not see polluted cursor.description.
"""

import logging

logger = logging.getLogger(__name__)


class TestCursorPollution:
    """Cursor pollution: sync SQLite backend."""

    def test_detect_math_functions_then_query(self, sqlite_file_backend):
        """_detect_math_functions() then a normal query."""
        backend = sqlite_file_backend

        # Detection runs: execute + fetchall + close
        result = backend._detect_math_functions()
        assert result is True

        cursor = backend._get_cursor()
        cursor.execute("SELECT 1 AS marker")
        rows = cursor.fetchall()
        cursor.close()

        assert len(rows) > 0
        assert cursor.description is not None
        col_name = cursor.description[0][0]
        assert col_name == "marker", (
            f"cursor.description polluted! expected 'marker', got: {col_name}"
        )

    def test_detect_json1_extension_then_query(self, sqlite_file_backend):
        """_detect_json1_extension() then a normal query."""
        backend = sqlite_file_backend

        result = backend._detect_json1_extension()
        assert result is True

        cursor = backend._get_cursor()
        cursor.execute("SELECT 42 AS answer")
        rows = cursor.fetchall()
        cursor.close()

        assert len(rows) > 0
        assert cursor.description is not None
        col_name = cursor.description[0][0]
        assert col_name == "answer", (
            f"cursor.description polluted! expected 'answer', got: {col_name}"
        )

    def test_introspect_and_adapt_then_query(self, sqlite_file_backend):
        """introspect_and_adapt() then a normal query."""
        backend = sqlite_file_backend
        backend.introspect_and_adapt()

        cursor = backend._get_cursor()
        cursor.execute("SELECT 'ok' AS status")
        rows = cursor.fetchall()
        cursor.close()

        assert len(rows) > 0
        assert cursor.description is not None
        col_name = cursor.description[0][0]
        assert col_name == "status", (
            f"cursor.description polluted! expected 'status', got: {col_name}"
        )

    def test_get_server_version_then_query(self, sqlite_file_backend):
        """get_server_version() then a normal query."""
        backend = sqlite_file_backend
        version = backend.get_server_version()
        assert version is not None

        cursor = backend._get_cursor()
        cursor.execute("SELECT 'v' AS ver")
        rows = cursor.fetchall()
        cursor.close()

        assert len(rows) > 0
        assert cursor.description is not None
        col_name = cursor.description[0][0]
        assert col_name == "ver", (
            f"cursor.description polluted! expected 'ver', got: {col_name}"
        )

    def test_high_frequency_detect_cycle(self, sqlite_file_backend):
        """High-frequency detection/query cycle to expose connection state leaks."""
        backend = sqlite_file_backend

        for i in range(200):
            backend._detect_math_functions()
            backend._detect_json1_extension()
            backend.introspect_and_adapt()
            backend.get_compile_options()

            cursor = backend._get_cursor()
            cursor.execute(f"SELECT {i} AS cycle")
            rows = cursor.fetchall()
            cursor.close()

            assert len(rows) > 0
            assert cursor.description is not None
            col_name = cursor.description[0][0]
            assert col_name == "cycle", (
                f"Iteration {i}: cursor.description polluted! "
                f"expected 'cycle', got: {col_name}"
            )

        logger.info("High-frequency detection cycle 200 iterations passed")