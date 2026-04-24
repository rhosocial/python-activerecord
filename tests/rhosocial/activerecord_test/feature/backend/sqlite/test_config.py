# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_config.py
import os
import pytest
import sqlite3
from unittest.mock import patch
from rhosocial.activerecord.backend.impl.sqlite.config import (
    SQLiteConnectionConfig,
    SQLiteInMemoryConfig,
    SQLiteTempFileConfig,
)


class TestSQLiteConnectionConfigParameters:
    """Test all SQLite connection parameters from sqlite3.connect."""

    def test_database_parameter(self):
        """Test database parameter."""
        config = SQLiteConnectionConfig(database="my.db")
        assert config.database == "my.db"

    def test_timeout_parameter(self):
        """Test timeout parameter."""
        config = SQLiteConnectionConfig(timeout=30.0)
        assert config.timeout == 30.0

    def test_detect_types_parameter(self):
        """Test detect_types parameter."""
        config = SQLiteConnectionConfig(detect_types=sqlite3.PARSE_DECLTYPES)
        assert config.detect_types == sqlite3.PARSE_DECLTYPES

    def test_isolation_level_parameter(self):
        """Test isolation_level parameter."""
        config = SQLiteConnectionConfig(isolation_level="DEFERRED")
        assert config.isolation_level == "DEFERRED"

    def test_check_same_thread_parameter(self):
        """Test check_same_thread parameter."""
        config = SQLiteConnectionConfig(check_same_thread=False)
        assert config.check_same_thread is False
        # Default should be True
        config_default = SQLiteConnectionConfig()
        assert config_default.check_same_thread is True

    def test_uri_parameter(self):
        """Test uri parameter."""
        config = SQLiteConnectionConfig(uri=True)
        assert config.uri is True

    def test_cached_statements_parameter(self):
        """Test cached_statements parameter."""
        config = SQLiteConnectionConfig(cached_statements=256)
        assert config.cached_statements == 256
        # Default should be 128
        config_default = SQLiteConnectionConfig()
        assert config_default.cached_statements == 128

    def test_autocommit_parameter(self):
        """Test autocommit parameter."""
        config = SQLiteConnectionConfig(autocommit=True)
        assert config.autocommit is True
        # Default should be False
        config_default = SQLiteConnectionConfig()
        assert config_default.autocommit is False


class TestSQLiteConnectionConfig:
    """Tests for SQLiteConnectionConfig class."""

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

    def test_to_dict_with_cached_statements(self):
        """Test to_dict includes cached_statements when non-default."""
        config = SQLiteConnectionConfig(database="test.db", cached_statements=256)
        config_dict = config.to_dict()
        assert config_dict['options']['cached_statements'] == 256

    def test_to_dict_default_cached_statements_not_included(self):
        """Test to_dict does not include cached_statements when default."""
        config = SQLiteConnectionConfig(database="test.db")
        config_dict = config.to_dict()
        assert 'cached_statements' not in config_dict.get('options', {})

    def test_to_dict_with_autocommit(self):
        """Test to_dict includes autocommit when True."""
        config = SQLiteConnectionConfig(database="test.db", autocommit=True)
        config_dict = config.to_dict()
        assert config_dict['options']['autocommit'] is True

    def test_to_dict_default_autocommit_not_included(self):
        """Test to_dict does not include autocommit when default."""
        config = SQLiteConnectionConfig(database="test.db")
        config_dict = config.to_dict()
        assert 'autocommit' not in config_dict.get('options', {})

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

    @patch.dict(os.environ, {
        "SQLITE_CACHED_STATEMENTS": "512",
        "SQLITE_AUTOCOMMIT": "true",
    })
    def test_from_env_cached_statements(self):
        """Test from_env with cached_statements."""
        config = SQLiteConnectionConfig.from_env()
        assert config.cached_statements == 512

    @patch.dict(os.environ, {
        "SQLITE_CACHED_STATEMENTS": "invalid_int",
    })
    def test_from_env_invalid_cached_statements(self):
        """Test from_env with invalid cached_statements, should fall back to default."""
        config = SQLiteConnectionConfig.from_env()
        assert config.cached_statements == 128

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
