# tests/rhosocial/activerecord_test/feature/backend/sqlite/extensions/test_pragma_async.py
"""Async twin of test_pragma.py: PRAGMA configuration and runtime behavior on AsyncSQLiteBackend."""
import logging
import os
import tempfile

import pytest

from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig


class TestAsyncSQLitePragma:
    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database file path"""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        # Cleanup
        if os.path.exists(path):
            os.unlink(path)
        # Cleanup related WAL and SHM files
        for ext in ["-wal", "-shm"]:
            wal_path = path + ext
            if os.path.exists(wal_path):
                os.unlink(wal_path)

    async def verify_pragma_value(self, backend, pragma_name, expected_string_value):
        """Helper method to verify PRAGMA values considering SQLite's behavior"""
        row = await backend.fetch_one(f"PRAGMA {pragma_name}")

        if pragma_name == "temp_store" and expected_string_value == "MEMORY":
            if row and row[pragma_name] == 2:
                return True

        if pragma_name == "journal_mode" and expected_string_value:
            if row and row[pragma_name].upper() == expected_string_value.upper():
                return True

        if pragma_name == "synchronous":
            sync_map = {"OFF": 0, "NORMAL": 1, "FULL": 2}
            if expected_string_value in sync_map and row and row[pragma_name] == sync_map[expected_string_value]:
                return True

        if expected_string_value in ["ON", "OFF"]:
            expected_value = 1 if expected_string_value == "ON" else 0
            if row and row[pragma_name] == expected_value:
                return True

        if row and str(row[pragma_name]).upper() == expected_string_value.upper():
            return True

        return row[pragma_name] if row else None

    @pytest.mark.asyncio
    async def test_default_pragmas(self, temp_db_path):
        """Test default PRAGMA settings"""
        config = SQLiteConnectionConfig(database=temp_db_path)
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()

        assert backend.pragmas["foreign_keys"] == "ON"
        assert backend.pragmas["journal_mode"] == "WAL"
        assert backend.pragmas["synchronous"] == "FULL"
        assert backend.pragmas["wal_autocheckpoint"] == "1000"
        assert "wal_checkpoint" in backend.pragmas

        foreign_keys = await backend.fetch_one("PRAGMA foreign_keys")
        journal_mode = await backend.fetch_one("PRAGMA journal_mode")
        synchronous = await backend.fetch_one("PRAGMA synchronous")
        wal_autocheckpoint = await backend.fetch_one("PRAGMA wal_autocheckpoint")

        assert foreign_keys["foreign_keys"] == 1, "foreign_keys should be enabled by default"
        assert journal_mode["journal_mode"].upper() == "WAL", "journal_mode should be WAL by default"
        assert synchronous["synchronous"] == 2, "synchronous should be FULL (2) by default"
        assert wal_autocheckpoint["wal_autocheckpoint"] == 1000, "wal_autocheckpoint should be 1000 by default"

        for key, value in SQLiteConnectionConfig.DEFAULT_PRAGMAS.items():
            assert key in backend.pragmas
            assert backend.pragmas[key] == value

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_pragmas_via_constructor_kwargs(self, temp_db_path):
        """Test setting PRAGMAs via constructor kwargs"""
        custom_pragmas = {"cache_size": "5000", "journal_mode": "MEMORY", "synchronous": "NORMAL"}
        config = SQLiteConnectionConfig(database=temp_db_path, pragmas=custom_pragmas)
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()

        assert backend.pragmas["cache_size"] == "5000"
        assert backend.pragmas["journal_mode"] == "MEMORY"
        assert backend.pragmas["synchronous"] == "NORMAL"

        cache_size = await backend.fetch_one("PRAGMA cache_size")
        journal_mode = await backend.fetch_one("PRAGMA journal_mode")
        synchronous = await backend.fetch_one("PRAGMA synchronous")

        assert cache_size["cache_size"] == 5000, "cache_size should be custom value 5000"
        assert journal_mode["journal_mode"].upper() == "MEMORY", "journal_mode should be MEMORY"
        assert synchronous["synchronous"] == 1, "synchronous NORMAL should map to 1"

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_pragmas_via_config_pragmas(self, temp_db_path):
        """Test setting PRAGMAs via SQLiteConnectionConfig pragmas field"""
        custom_pragmas = {"synchronous": "OFF"}
        config = SQLiteConnectionConfig(database=temp_db_path, pragmas=custom_pragmas)
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()

        assert backend.pragmas["synchronous"] == "OFF"

        synchronous = await backend.fetch_one("PRAGMA synchronous")
        assert synchronous["synchronous"] == 0, "synchronous OFF should map to 0"

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_temp_store_pragma(self, temp_db_path):
        """Test specifically the temp_store PRAGMA behavior"""
        config = SQLiteConnectionConfig(
            database=temp_db_path,
            pragmas={"temp_store": "MEMORY"},
        )
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()

        assert backend.pragmas["temp_store"] == "MEMORY"

        temp_store = await backend.fetch_one("PRAGMA temp_store")
        assert temp_store["temp_store"] == 2, "temp_store should be 2 (MEMORY)"

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_pragmas_direct_setting(self, temp_db_path):
        """Test direct setting of PRAGMAs using set_pragma method"""
        sqlite_config = SQLiteConnectionConfig(database=temp_db_path)
        backend = AsyncSQLiteBackend(connection_config=sqlite_config)
        await backend.connect()

        await backend.set_pragma("journal_mode", "TRUNCATE")
        await backend.set_pragma("locking_mode", "EXCLUSIVE")

        journal_mode = await backend.fetch_one("PRAGMA journal_mode")
        locking_mode = await backend.fetch_one("PRAGMA locking_mode")

        assert journal_mode["journal_mode"].upper() == "TRUNCATE", "journal_mode should be TRUNCATE"
        assert locking_mode["locking_mode"].upper() == "EXCLUSIVE", "locking_mode should be EXCLUSIVE"

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_runtime_pragma_changes(self, temp_db_path):
        """Test changing PRAGMA settings at runtime"""
        config = SQLiteConnectionConfig(database=temp_db_path)
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()

        await backend.set_pragma("cache_size", 10000)
        await backend.set_pragma("synchronous", "NORMAL")

        assert backend.pragmas["cache_size"] == "10000"
        assert backend.pragmas["synchronous"] == "NORMAL"

        cache_size = await backend.fetch_one("PRAGMA cache_size")
        synchronous = await backend.fetch_one("PRAGMA synchronous")

        assert cache_size["cache_size"] == 10000, "cache_size should be changed to 10000"
        assert synchronous["synchronous"] == 1, "synchronous NORMAL should map to 1"

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_case_sensitive_like_pragma(self, temp_db_path):
        """Test case_sensitive_like PRAGMA specifically"""
        config = SQLiteConnectionConfig(database=temp_db_path, pragmas={"case_sensitive_like": "ON"})
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()

        assert backend.pragmas["case_sensitive_like"] == "ON"

        from rhosocial.activerecord.backend.options import ExecutionOptions
        from rhosocial.activerecord.backend.schema import StatementType

        await backend.execute(
            "CREATE TABLE test_case (text TEXT)", (), options=ExecutionOptions(stmt_type=StatementType.DDL)
        )
        await backend.execute(
            "INSERT INTO test_case VALUES ('ABC')", (), options=ExecutionOptions(stmt_type=StatementType.INSERT)
        )

        result = await backend.fetch_all("SELECT * FROM test_case WHERE text LIKE 'abc'")
        assert len(result) == 0, "case_sensitive_like ON: should not find lowercase match"

        await backend.disconnect()

        # Compare with default behavior (OFF)
        config2 = SQLiteConnectionConfig(database=temp_db_path)
        backend2 = AsyncSQLiteBackend(connection_config=config2)
        await backend2.connect()

        await backend2.set_pragma("case_sensitive_like", "OFF")

        result = await backend2.fetch_all("SELECT * FROM test_case WHERE text LIKE 'abc'")
        assert len(result) >= 1, "case_sensitive_like OFF: should find case-insensitive match"

        await backend2.disconnect()

    @pytest.mark.asyncio
    async def test_pragma_validation(self, temp_db_path):
        """Test that pragmas are being set correctly"""
        test_pragmas = {"synchronous": "NORMAL", "journal_mode": "MEMORY", "cache_size": "5000"}
        config = SQLiteConnectionConfig(database=temp_db_path, pragmas=test_pragmas)
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()

        test_logger = logging.getLogger("test_logger_async")
        handler = logging.StreamHandler()
        test_logger.addHandler(handler)
        backend.logger = test_logger

        # The whitelist validation rejects it outright
        with pytest.raises(ValueError, match="Invalid value"):
            await backend.set_pragma("journal_mode", "NONEXISTENT_MODE")

        journal_mode = await backend.fetch_one("PRAGMA journal_mode")
        assert journal_mode["journal_mode"].upper() == "MEMORY", "Invalid journal_mode should not change existing value"

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_pragma_priority_implementation(self, temp_db_path):
        """Test how pragma priority is actually implemented"""
        # 1. Only SQLiteConnectionConfig constructor pragmas
        sqlite_config1 = SQLiteConnectionConfig(database=temp_db_path, pragmas={"synchronous": "OFF"})
        backend1 = AsyncSQLiteBackend(connection_config=sqlite_config1)
        await backend1.connect()

        # 2. Only pragma set through set_pragma method
        sqlite_config2 = SQLiteConnectionConfig(database=temp_db_path)
        backend2 = AsyncSQLiteBackend(connection_config=sqlite_config2)
        await backend2.connect()
        await backend2.set_pragma("synchronous", "NORMAL")

        # 3. Config pragmas + set_pragma (set_pragma should override config)
        sqlite_config3 = SQLiteConnectionConfig(database=temp_db_path, pragmas={"synchronous": "FULL"})
        backend3 = AsyncSQLiteBackend(connection_config=sqlite_config3)
        await backend3.connect()
        await backend3.set_pragma("synchronous", "NORMAL")

        sync1 = (await backend1.fetch_one("PRAGMA synchronous"))["synchronous"]
        sync2 = (await backend2.fetch_one("PRAGMA synchronous"))["synchronous"]
        sync3 = (await backend3.fetch_one("PRAGMA synchronous"))["synchronous"]

        print("\nPRAGMA priority test results (async):")
        print(f"1. SQLiteConnectionConfig pragmas only: {sync1}")
        print(f"2. set_pragma only: {sync2}")
        print(f"3. Config.pragmas + set_pragma: {sync3}")

        await backend1.disconnect()
        await backend2.disconnect()
        await backend3.disconnect()

        assert sync1 == 0, "SQLiteConnectionConfig pragmas should set synchronous to OFF (0)"
        assert sync2 == 1, "set_pragma should set synchronous to NORMAL (1)"
        assert sync3 == 1, "set_pragma should override SQLiteConnectionConfig pragmas"

    @pytest.mark.asyncio
    async def test_reconnect_preserves_pragmas(self, temp_db_path):
        """Test that PRAGMA settings are preserved on reconnection"""
        config = SQLiteConnectionConfig(database=temp_db_path, pragmas={"cache_size": "5000", "synchronous": "NORMAL"})
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()

        cache_size = await backend.fetch_one("PRAGMA cache_size")
        synchronous = await backend.fetch_one("PRAGMA synchronous")
        assert cache_size["cache_size"] == 5000
        assert synchronous["synchronous"] == 1

        await backend.disconnect()

        await backend.connect()

        cache_size = await backend.fetch_one("PRAGMA cache_size")
        synchronous = await backend.fetch_one("PRAGMA synchronous")
        assert cache_size["cache_size"] == 5000, "cache_size should remain unchanged after reconnection"
        assert synchronous["synchronous"] == 1, "synchronous should remain unchanged after reconnection"

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_set_pragma_without_connection(self, temp_db_path):
        """Test setting PRAGMAs without an active connection"""
        config = SQLiteConnectionConfig(database=temp_db_path)
        backend = AsyncSQLiteBackend(connection_config=config)

        await backend.set_pragma("cache_size", 10000)

        assert backend.pragmas["cache_size"] == "10000"

        await backend.connect()
        cache_size = await backend.fetch_one("PRAGMA cache_size")
        assert cache_size["cache_size"] == 10000, "Previously set PRAGMA should be applied on connect"

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_sqlite_connection_config_specific_options(self, temp_db_path):
        """Test SQLite-specific options in SQLiteConnectionConfig"""
        sqlite_config = SQLiteConnectionConfig(
            database=temp_db_path,
            uri=True,
            timeout=10.0,
            detect_types=0,
            pragmas={"foreign_keys": "OFF"},
        )

        backend = AsyncSQLiteBackend(connection_config=sqlite_config)
        await backend.connect()

        foreign_keys = await backend.fetch_one("PRAGMA foreign_keys")
        assert foreign_keys["foreign_keys"] == 0, "SQLite-specific pragma should be applied"

        assert backend.config.uri is True
        assert backend.config.timeout == 10.0
        assert backend.config.detect_types == 0

        await backend.disconnect()
