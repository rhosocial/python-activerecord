import pytest
import os
from unittest.mock import patch

from src.rhosocial.activerecord.backend.typing import ConnectionConfig, QueryResult


class TestConnectionConfig:
    def test_to_dict_basic(self):
        # Test basic config to dict conversion
        config = ConnectionConfig(
            host="testhost",
            port=3306,
            database="testdb",
            username="testuser",
            password="testpass"
        )
        result = config.to_dict()

        assert result["host"] == "testhost"
        assert result["port"] == 3306
        assert result["database"] == "testdb"
        assert result["username"] == "testuser"
        assert result["password"] == "testpass"

    def test_to_dict_none_values(self):
        # Test that None values are excluded
        config = ConnectionConfig(
            host="testhost",
            port=None,
            database="testdb",
            username=None
        )
        result = config.to_dict()

        assert result["host"] == "testhost"
        assert "port" not in result
        assert result["database"] == "testdb"
        assert "username" not in result

    def test_to_dict_with_options(self):
        # Test with options
        config = ConnectionConfig(
            host="testhost",
            options={"connect_timeout": 10, "compress": True}
        )
        result = config.to_dict()

        assert result["host"] == "testhost"
        assert result["connect_timeout"] == 10
        assert result["compress"] is True

    def test_from_env_basic(self):
        # Test basic environment variables
        with patch.dict(os.environ, {
            "TEST_HOST": "envhost",
            "TEST_PORT": "1234",
            "TEST_DATABASE": "envdb",
            "TEST_USER": "envuser",
            "TEST_PASSWORD": "envpass",
            "TEST_CHARSET": "utf8",
            "TEST_TIMEZONE": "UTC",
            "TEST_POOL_SIZE": "10",
            "TEST_POOL_TIMEOUT": "60",
            "TEST_POOL_NAME": "testpool"
        }):
            config = ConnectionConfig.from_env(prefix="TEST_")

            assert config.host == "envhost"
            assert config.port == 1234
            assert config.database == "envdb"
            assert config.username == "envuser"
            assert config.password == "envpass"
            assert config.charset == "utf8"
            assert config.timezone == "UTC"
            assert config.pool_size == 10
            assert config.pool_timeout == 60
            assert config.pool_name == "testpool"

    def test_from_env_ssl_and_auth(self):
        # Test SSL and authentication options
        with patch.dict(os.environ, {
            "DB_SSL_CA": "/path/to/ca",
            "DB_SSL_CERT": "/path/to/cert",
            "DB_SSL_KEY": "/path/to/key",
            "DB_SSL_MODE": "verify_ca",
            "DB_AUTH_PLUGIN": "mysql_native_password"
        }):
            config = ConnectionConfig.from_env(prefix="DB_")

            assert config.ssl_ca == "/path/to/ca"
            assert config.ssl_cert == "/path/to/cert"
            assert config.ssl_key == "/path/to/key"
            assert config.ssl_mode == "verify_ca"
            assert config.auth_plugin == "mysql_native_password"

    def test_from_env_defaults(self):
        # Test default values when env vars not present
        with patch.dict(os.environ, {}, clear=True):
            config = ConnectionConfig.from_env(prefix="TEST_")

            assert config.host == "localhost"
            assert config.port is None
            assert config.database is None
            assert config.username is None
            assert config.password is None
            assert config.charset == "utf8mb4"
            assert config.timezone is None
            assert config.pool_size == 5
            assert config.pool_timeout == 30

    def test_from_env_invalid_integer(self):
        # Test handling of invalid integer values
        with patch.dict(os.environ, {
            "TEST_PORT": "invalid",
            "TEST_POOL_SIZE": "not_a_number"
        }):
            # Should not raise an exception, but return None for these fields
            with pytest.raises(ValueError):
                ConnectionConfig.from_env(prefix="TEST_")

    def test_clone(self):
        # Test cloning configuration with updates
        config = ConnectionConfig(
            host="original",
            port=3306,
            database="original_db",
            username="original_user"
        )

        cloned = config.clone(host="updated", database="updated_db")

        # Original should be unchanged
        assert config.host == "original"
        assert config.database == "original_db"

        # Cloned should have updated values
        assert cloned.host == "updated"
        assert cloned.port == 3306  # Unchanged value
        assert cloned.database == "updated_db"
        assert cloned.username == "original_user"  # Unchanged value


class TestQueryResult:
    def test_query_result_creation(self):
        # Test creating QueryResult with data
        result = QueryResult(
            data=[{"id": 1, "name": "Test"}],
            affected_rows=1,
            last_insert_id=1,
            duration=0.1
        )

        assert result.data == [{"id": 1, "name": "Test"}]
        assert result.affected_rows == 1
        assert result.last_insert_id == 1
        assert result.duration == 0.1

    def test_query_result_defaults(self):
        # Test QueryResult with default values
        result = QueryResult()

        assert result.data is None
        assert result.affected_rows == 0
        assert result.last_insert_id is None
        assert result.duration == 0.0