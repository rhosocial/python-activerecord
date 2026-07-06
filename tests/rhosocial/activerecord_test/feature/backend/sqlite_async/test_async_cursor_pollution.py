# tests/rhosocial/activerecord_test/feature/backend/sqlite_async/test_async_cursor_pollution.py
"""
Async cursor result set pollution tests.

Verifies that after _detect_math_functions() / _detect_json1_extension()
close a cursor without fully consuming results, subsequent async queries on
the same connection do not see polluted cursor.description.
"""

import logging

logger = logging.getLogger(__name__)


class TestAsyncCursorPollution:
    """Cursor pollution: async SQLite backend."""

    async def test_detect_math_functions_then_query(self, async_sqlite_memory_backend):
        """_detect_math_functions() then a normal async query."""
        backend = async_sqlite_memory_backend

        result = await backend._detect_math_functions()
        assert result is True

        cursor = await backend._get_cursor()
        await cursor.execute("SELECT 1 AS marker")
        rows = await cursor.fetchall()
        await cursor.close()

        assert len(rows) > 0
        assert cursor.description is not None
        col_name = cursor.description[0][0]
        assert col_name == "marker", (
            f"cursor.description polluted! expected 'marker', got: {col_name}"
        )

    async def test_detect_json1_extension_then_query(self, async_sqlite_memory_backend):
        """_detect_json1_extension() then a normal async query."""
        backend = async_sqlite_memory_backend

        result = await backend._detect_json1_extension()
        assert result is True

        cursor = await backend._get_cursor()
        await cursor.execute("SELECT 42 AS answer")
        rows = await cursor.fetchall()
        await cursor.close()

        assert len(rows) > 0
        assert cursor.description is not None
        col_name = cursor.description[0][0]
        assert col_name == "answer", (
            f"cursor.description polluted! expected 'answer', got: {col_name}"
        )

    async def test_introspect_and_adapt_then_query(self, async_sqlite_memory_backend):
        """introspect_and_adapt() then a normal async query."""
        backend = async_sqlite_memory_backend
        await backend.introspect_and_adapt()

        cursor = await backend._get_cursor()
        await cursor.execute("SELECT 'ok' AS status")
        rows = await cursor.fetchall()
        await cursor.close()

        assert len(rows) > 0
        assert cursor.description is not None
        col_name = cursor.description[0][0]
        assert col_name == "status", (
            f"cursor.description polluted! expected 'status', got: {col_name}"
        )

    async def test_get_server_version_then_query(self, async_sqlite_memory_backend):
        """get_server_version() then a normal async query."""
        backend = async_sqlite_memory_backend
        version = backend.get_server_version()
        assert version is not None

        cursor = await backend._get_cursor()
        await cursor.execute("SELECT 'v' AS ver")
        rows = await cursor.fetchall()
        await cursor.close()

        assert len(rows) > 0
        assert cursor.description is not None
        col_name = cursor.description[0][0]
        assert col_name == "ver", (
            f"cursor.description polluted! expected 'ver', got: {col_name}"
        )

    async def test_high_frequency_detect_cycle(self, async_sqlite_memory_backend):
        """High-frequency async detection/query cycle to expose connection state leaks."""
        backend = async_sqlite_memory_backend

        for i in range(200):
            await backend._detect_math_functions()
            await backend._detect_json1_extension()
            await backend.introspect_and_adapt()
            await backend.get_compile_options()

            cursor = await backend._get_cursor()
            await cursor.execute(f"SELECT {i} AS cycle")
            rows = await cursor.fetchall()
            await cursor.close()

            assert len(rows) > 0
            assert cursor.description is not None
            col_name = cursor.description[0][0]
            assert col_name == "cycle", (
                f"Iteration {i}: cursor.description polluted! "
                f"expected 'cycle', got: {col_name}"
            )

        logger.info("Async high-frequency detection cycle 200 iterations passed")