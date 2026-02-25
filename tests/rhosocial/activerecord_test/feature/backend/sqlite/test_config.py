# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_config.py
import os
import pytest
from unittest.mock import patch
from rhosocial.activerecord.backend.impl.sqlite.config import (
    SQLiteConnectionConfig,
    SQLiteInMemoryConfig,
    SQLiteTempFileConfig,
)


class TestSQLiteConnectionConfig:

    def test_to_dict(self):
        """Tests that to_dict includes SQLite-specific options."""
        config = SQLiteConnectionConfig(
            database="test.db",
            uri=True,
            pragmas={"journal_mode": "WAL"}
        )
        config_dict = config.to_dict()
        assert config_dict['database'] == "test.db"
        assert config_dict['options']['uri'] is True
        assert config_dict['options']['pragmas']['journal_mode'] == "WAL"

    @patch.dict(os.environ, {
        "SQLITE_DATABASE": "env.db",
        "SQLITE_TIMEOUT": "15.5",
        "SQLITE_URI": "true",
        "SQLITE_PRAGMA_SYNCHRONOUS": "NORMAL",
        "SQLITE_DETECT_TYPES": "0"
    })
    def test_from_env(self):
        """Tests creating a config from environment variables."""
        config = SQLiteConnectionConfig.from_env()
        assert config.database == "env.db"
        assert config.timeout == 15.5
        assert config.uri is True
        assert config.pragmas['synchronous'] == "NORMAL"
        assert config.detect_types == 0

    @patch.dict(os.environ, {
        "SQLITE_DATABASE": "env.db",
        "SQLITE_TIMEOUT": "invalid_float",
        "SQLITE_URI": "not_a_bool",
    })
    def test_from_env_invalid_values(self):
        """Tests from_env with invalid values, which should be ignored."""
        config = SQLiteConnectionConfig.from_env()
        # Should fall back to defaults
        assert config.database == "env.db"
        assert config.timeout == 5.0  # default
        assert config.uri is False # default for "not_a_bool"

    def test_clone(self):
        """Test cloning a config and updating attributes."""
        config1 = SQLiteConnectionConfig(
            database="original.db",
            pragmas={"journal_mode": "DELETE"}
        )
        config2 = config1.clone(database="clone.db", pragmas={"journal_mode": "WAL"})
        assert config2.database == "clone.db"
        assert config2.pragmas['journal_mode'] == "WAL"
        # Ensure original is unchanged
        assert config1.database == "original.db"

class TestSpecializedConfigs:

    def test_in_memory_config(self):
        """Tests SQLiteInMemoryConfig for correct defaults."""
        config = SQLiteInMemoryConfig()
        assert config.database == ":memory:"
        assert config.is_memory_db() is True
        assert config.pragmas['journal_mode'] == "MEMORY"
        assert config.pragmas['synchronous'] == "OFF"

    def test_temp_file_config(self):
        """Tests SQLiteTempFileConfig for correct setup."""
        config = SQLiteTempFileConfig()
        assert config.database != ":memory:"
        assert os.path.exists(config.database)
        assert config.delete_on_close is True
        # Clean up the temp file
        os.remove(config.database)
