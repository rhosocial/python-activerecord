import logging
import os
import tempfile

import pytest

from src.rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from src.rhosocial.activerecord.backend.typing import ConnectionConfig


class TestSQLitePragma:
    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database file path"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        # Cleanup
        if os.path.exists(path):
            os.unlink(path)
        # Cleanup related WAL and SHM files
        for ext in ['-wal', '-shm']:
            wal_path = path + ext
            if os.path.exists(wal_path):
                os.unlink(wal_path)

    def verify_pragma_value(self, backend, pragma_name, expected_string_value):
        """Helper method to verify PRAGMA values considering SQLite's behavior"""
        # Query the current PRAGMA value
        row = backend.fetch_one(f"PRAGMA {pragma_name}")

        # If we're dealing with temp_store, SQLite might return numeric values
        # MEMORY for temp_store is 2, but SQLite might convert string "MEMORY" to 2
        if pragma_name == "temp_store" and expected_string_value == "MEMORY":
            if row and row[pragma_name] == 2:
                return True

        # For journal_mode, check case-insensitive
        if pragma_name == "journal_mode" and expected_string_value:
            if row and row[pragma_name].upper() == expected_string_value.upper():
                return True

        # For synchronous, map string values to numeric
        if pragma_name == "synchronous":
            sync_map = {"OFF": 0, "NORMAL": 1, "FULL": 2}
            if expected_string_value in sync_map and row and row[pragma_name] == sync_map[expected_string_value]:
                return True

        # For boolean PRAGMAs like foreign_keys, map ON/OFF to 1/0
        if expected_string_value in ["ON", "OFF"]:
            expected_value = 1 if expected_string_value == "ON" else 0
            if row and row[pragma_name] == expected_value:
                return True

        # Direct comparison for other cases
        if row and str(row[pragma_name]).upper() == expected_string_value.upper():
            return True

        # Return the actual value for debugging/display
        return row[pragma_name] if row else None

    def test_default_pragmas(self, temp_db_path):
        """Test default PRAGMA settings"""
        # Create backend
        config = ConnectionConfig(database=temp_db_path)
        backend = SQLiteBackend(connection_config=config)
        backend.connect()

        # Verify internal PRAGMA dictionary
        assert backend._pragmas["foreign_keys"] == "ON"
        assert backend._pragmas["journal_mode"] == "WAL"
        assert backend._pragmas["synchronous"] == "FULL"
        assert backend._pragmas["wal_autocheckpoint"] == "1000"
        assert "wal_checkpoint" in backend._pragmas

        # Verify PRAGMA settings in database
        # Note: SQLite might store these values differently, so we check internal and DB values separately
        foreign_keys = backend.fetch_one("PRAGMA foreign_keys")
        journal_mode = backend.fetch_one("PRAGMA journal_mode")
        synchronous = backend.fetch_one("PRAGMA synchronous")
        wal_autocheckpoint = backend.fetch_one("PRAGMA wal_autocheckpoint")

        assert foreign_keys["foreign_keys"] == 1, "foreign_keys should be enabled by default"
        assert journal_mode["journal_mode"].upper() == "WAL", "journal_mode should be WAL by default"
        assert synchronous["synchronous"] == 2, "synchronous should be FULL (2) by default"
        assert wal_autocheckpoint["wal_autocheckpoint"] == 1000, "wal_autocheckpoint should be 1000 by default"

        # Ensure default PRAGMAs come from DEFAULT_PRAGMAS
        for key, value in SQLiteBackend.DEFAULT_PRAGMAS.items():
            assert key in backend._pragmas
            assert backend._pragmas[key] == value

        backend.disconnect()

    def test_pragmas_via_constructor_kwargs(self, temp_db_path):
        """Test setting PRAGMAs via constructor kwargs"""
        # Create backend with custom PRAGMAs
        custom_pragmas = {
            "cache_size": "5000",
            "journal_mode": "MEMORY",
            "synchronous": "NORMAL"
        }
        backend = SQLiteBackend(
            database=temp_db_path,
            pragmas=custom_pragmas
        )
        backend.connect()

        # Verify internal PRAGMA dictionary contains our custom values
        assert backend._pragmas["cache_size"] == "5000"
        assert backend._pragmas["journal_mode"] == "MEMORY"
        assert backend._pragmas["synchronous"] == "NORMAL"

        # Verify in database - query and check the actual values
        cache_size = backend.fetch_one("PRAGMA cache_size")
        journal_mode = backend.fetch_one("PRAGMA journal_mode")
        synchronous = backend.fetch_one("PRAGMA synchronous")

        # Cache size could be stored as-is
        assert cache_size["cache_size"] == 5000, "cache_size should be custom value 5000"

        # Journal mode should match our setting (case-insensitive)
        assert journal_mode["journal_mode"].upper() == "MEMORY", "journal_mode should be MEMORY"

        # Synchronous NORMAL typically maps to 1
        assert synchronous["synchronous"] == 1, "synchronous NORMAL should map to 1"

        backend.disconnect()

    def test_pragmas_via_config_pragmas(self, temp_db_path):
        """Test setting PRAGMAs via ConnectionConfig pragmas field"""
        # Create config with custom PRAGMAs
        custom_pragmas = {
            "synchronous": "OFF"
        }
        config = ConnectionConfig(
            database=temp_db_path,
            pragmas=custom_pragmas
        )
        backend = SQLiteBackend(connection_config=config)
        backend.connect()

        # Verify internal PRAGMA setting
        assert backend._pragmas["synchronous"] == "OFF"

        # Verify in database
        synchronous = backend.fetch_one("PRAGMA synchronous")
        assert synchronous["synchronous"] == 0, "synchronous OFF should map to 0"

        backend.disconnect()

    def test_temp_store_pragma(self, temp_db_path):
        """Test specifically the temp_store PRAGMA behavior"""
        # SQLite allows setting temp_store to MEMORY (2) or FILE (1) or DEFAULT (0)
        backend = SQLiteBackend(
            database=temp_db_path,
            pragmas={"temp_store": "2"}  # Use numeric value to be more explicit
        )
        backend.connect()

        # Verify internal setting
        assert backend._pragmas["temp_store"] == "2"

        # Verify in database
        temp_store = backend.fetch_one("PRAGMA temp_store")
        assert temp_store["temp_store"] == 2, "temp_store should be 2"

        backend.disconnect()

    def test_pragmas_via_config_options(self, temp_db_path):
        """Test setting PRAGMAs via ConnectionConfig options field"""
        # Create config with custom PRAGMAs in options
        config = ConnectionConfig(
            database=temp_db_path,
            options={
                "pragmas": {
                    "locking_mode": "EXCLUSIVE",
                    "journal_mode": "TRUNCATE"
                }
            }
        )
        backend = SQLiteBackend(connection_config=config)
        backend.connect()

        # Verify internal settings
        assert backend._pragmas["locking_mode"] == "EXCLUSIVE"
        assert backend._pragmas["journal_mode"] == "TRUNCATE"

        # Verify in database
        locking_mode = backend.fetch_one("PRAGMA locking_mode")
        journal_mode = backend.fetch_one("PRAGMA journal_mode")

        assert locking_mode["locking_mode"].upper() == "EXCLUSIVE", "locking_mode should be EXCLUSIVE"
        assert journal_mode["journal_mode"].upper() == "TRUNCATE", "journal_mode should be TRUNCATE"

        backend.disconnect()

    def test_runtime_pragma_changes(self, temp_db_path):
        """Test changing PRAGMA settings at runtime"""
        # Create backend
        backend = SQLiteBackend(database=temp_db_path)
        backend.connect()

        # Modify PRAGMAs using set_pragma method
        backend.set_pragma("cache_size", 10000)
        backend.set_pragma("synchronous", "NORMAL")

        # Verify internal settings
        assert backend._pragmas["cache_size"] == "10000"
        assert backend._pragmas["synchronous"] == "NORMAL"

        # Verify in database
        cache_size = backend.fetch_one("PRAGMA cache_size")
        synchronous = backend.fetch_one("PRAGMA synchronous")

        assert cache_size["cache_size"] == 10000, "cache_size should be changed to 10000"
        assert synchronous["synchronous"] == 1, "synchronous NORMAL should map to 1"

        backend.disconnect()

    def test_case_sensitive_like_pragma(self, temp_db_path):
        """Test case_sensitive_like PRAGMA specifically"""
        # This is a functional test rather than just checking the PRAGMA value
        backend = SQLiteBackend(
            database=temp_db_path,
            pragmas={"case_sensitive_like": "ON"}
        )
        backend.connect()

        # Verify internal setting
        assert backend._pragmas["case_sensitive_like"] == "ON"

        # Test with a sample table
        backend.execute("CREATE TABLE test_case (text TEXT)")
        backend.execute("INSERT INTO test_case VALUES ('ABC')")

        # With case_sensitive_like ON, case-sensitive search shouldn't find lowercase
        result = backend.fetch_all("SELECT * FROM test_case WHERE text LIKE 'abc'")
        assert len(result) == 0, "case_sensitive_like ON: should not find lowercase match"

        backend.disconnect()

        # Compare with default behavior (OFF)
        backend2 = SQLiteBackend(database=temp_db_path)
        backend2.connect()

        # Now set it explicitly to OFF
        backend2.set_pragma("case_sensitive_like", "OFF")

        # With case_sensitive_like OFF, case-insensitive search should work
        result = backend2.fetch_all("SELECT * FROM test_case WHERE text LIKE 'abc'")
        assert len(result) >= 1, "case_sensitive_like OFF: should find case-insensitive match"

        backend2.disconnect()

    def test_pragma_validation(self, temp_db_path):
        """Test that pragmas are being set correctly"""
        test_pragmas = {
            "synchronous": "NORMAL",
            "journal_mode": "MEMORY",
            "cache_size": "5000"
        }
        backend = SQLiteBackend(
            database=temp_db_path,
            pragmas=test_pragmas
        )
        backend.connect()

        # Create a logger to capture warnings
        test_logger = logging.getLogger("test_logger")
        handler = logging.StreamHandler()
        test_logger.addHandler(handler)
        backend.logger = test_logger

        # Try to set journal_mode to an invalid value
        # This might be accepted by SQLite but not take effect
        backend.set_pragma("journal_mode", "NONEXISTENT_MODE")

        # Check what the value actually is - it should remain MEMORY
        journal_mode = backend.fetch_one("PRAGMA journal_mode")
        assert journal_mode["journal_mode"].upper() == "MEMORY", "Invalid journal_mode should not change existing value"

        backend.disconnect()

    def test_pragma_priority_implementation(self, temp_db_path):
        """Test how pragma priority is actually implemented"""
        # This test needs to look at how the backend actually implements priority
        # Let's check all combinations to determine the actual implementation

        # Create separate backends with different arrangements of the same pragma

        # 1. Only constructor pragmas
        backend1 = SQLiteBackend(
            database=temp_db_path,
            pragmas={"synchronous": "OFF"}
        )
        backend1.connect()

        # 2. Only config.pragmas
        config2 = ConnectionConfig(
            database=temp_db_path,
            pragmas={"synchronous": "NORMAL"}
        )
        backend2 = SQLiteBackend(connection_config=config2)
        backend2.connect()

        # 3. Only options.pragmas
        config3 = ConnectionConfig(
            database=temp_db_path,
            options={"pragmas": {"synchronous": "FULL"}}
        )
        backend3 = SQLiteBackend(connection_config=config3)
        backend3.connect()

        # 4. Constructor + config.pragmas
        config4 = ConnectionConfig(
            database=temp_db_path,
            pragmas={"synchronous": "NORMAL"}
        )
        backend4 = SQLiteBackend(
            connection_config=config4,
            pragmas={"synchronous": "OFF"}
        )
        backend4.connect()

        # 5. Constructor + options.pragmas
        config5 = ConnectionConfig(
            database=temp_db_path,
            options={"pragmas": {"synchronous": "FULL"}}
        )
        backend5 = SQLiteBackend(
            connection_config=config5,
            pragmas={"synchronous": "OFF"}
        )
        backend5.connect()

        # 6. Config.pragmas + options.pragmas
        config6 = ConnectionConfig(
            database=temp_db_path,
            pragmas={"synchronous": "NORMAL"},
            options={"pragmas": {"synchronous": "FULL"}}
        )
        backend6 = SQLiteBackend(connection_config=config6)
        backend6.connect()

        # Query all values
        sync1 = backend1.fetch_one("PRAGMA synchronous")["synchronous"]
        sync2 = backend2.fetch_one("PRAGMA synchronous")["synchronous"]
        sync3 = backend3.fetch_one("PRAGMA synchronous")["synchronous"]
        sync4 = backend4.fetch_one("PRAGMA synchronous")["synchronous"]
        sync5 = backend5.fetch_one("PRAGMA synchronous")["synchronous"]
        sync6 = backend6.fetch_one("PRAGMA synchronous")["synchronous"]

        # Print values for debugging
        print(f"\nPRAGMA priority test results:")
        print(f"1. Constructor only: {sync1}")
        print(f"2. Config.pragmas only: {sync2}")
        print(f"3. Options.pragmas only: {sync3}")
        print(f"4. Constructor + config.pragmas: {sync4}")
        print(f"5. Constructor + options.pragmas: {sync5}")
        print(f"6. Config.pragmas + options.pragmas: {sync6}")

        # Clean up
        backend1.disconnect()
        backend2.disconnect()
        backend3.disconnect()
        backend4.disconnect()
        backend5.disconnect()
        backend6.disconnect()

        # Check if our understanding is correct
        assert sync1 == 0, "Constructor only should set synchronous to OFF (0)"
        assert sync2 == 1, "Config.pragmas only should set synchronous to NORMAL (1)"
        assert sync3 == 2, "Options.pragmas only should set synchronous to FULL (2)"
        assert sync4 == 0, "Constructor should have priority over config.pragmas"
        assert sync5 == 0, "Constructor should have priority over options.pragmas"
        assert sync6 == 1, "Config.pragmas should have priority over options.pragmas"

    def test_reconnect_preserves_pragmas(self, temp_db_path):
        """Test that PRAGMA settings are preserved on reconnection"""
        # Create backend with custom PRAGMAs
        backend = SQLiteBackend(
            database=temp_db_path,
            pragmas={"cache_size": "5000", "synchronous": "NORMAL"}
        )
        backend.connect()

        # Verify settings
        cache_size = backend.fetch_one("PRAGMA cache_size")
        synchronous = backend.fetch_one("PRAGMA synchronous")
        assert cache_size["cache_size"] == 5000
        assert synchronous["synchronous"] == 1

        # Disconnect
        backend.disconnect()

        # Reconnect
        backend.connect()

        # Verify PRAGMA settings are preserved
        cache_size = backend.fetch_one("PRAGMA cache_size")
        synchronous = backend.fetch_one("PRAGMA synchronous")
        assert cache_size["cache_size"] == 5000, "cache_size should remain unchanged after reconnection"
        assert synchronous["synchronous"] == 1, "synchronous should remain unchanged after reconnection"

        backend.disconnect()

    def test_set_pragma_without_connection(self, temp_db_path):
        """Test setting PRAGMAs without an active connection"""
        # Create backend but don't connect
        backend = SQLiteBackend(database=temp_db_path)

        # Set PRAGMA
        backend.set_pragma("cache_size", 10000)

        # Verify internal store
        assert backend._pragmas["cache_size"] == "10000"

        # Now connect and verify
        backend.connect()
        cache_size = backend.fetch_one("PRAGMA cache_size")
        assert cache_size["cache_size"] == 10000, "Previously set PRAGMA should be applied on connect"

        backend.disconnect()