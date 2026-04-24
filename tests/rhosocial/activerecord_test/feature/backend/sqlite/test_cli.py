# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_cli.py
"""
Tests for SQLite CLI functionality.

This module tests the CLI parameter resolution priority:
1. --db-file (highest priority)
2. --named-connection + --conn-param
3. Default: in-memory database
"""
import os
import tempfile
import types
from unittest.mock import MagicMock, patch
import pytest

from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig


class MockArgs:
    """Mock arguments for testing."""

    def __init__(self, db_file=None, named_connection=None, connection_params=None):
        self.db_file = db_file
        self.named_connection = named_connection
        self.connection_params = connection_params or []


class TestConnectionConfigPriority:
    """Test connection config resolution priority."""

    def test_default_is_memory(self):
        """Test that default database is :memory:."""
        args = MockArgs()
        from rhosocial.activerecord.backend.impl.sqlite.__main__ import _resolve_connection_config

        with patch("rhosocial.activerecord.backend.impl.sqlite.__main__.NamedConnectionResolver") as mock_resolver:
            config = _resolve_connection_config(args)

        assert config.database == ":memory:"

    def test_db_file_only(self):
        """Test --db-file without named connection."""
        args = MockArgs(db_file="/tmp/test.db")
        from rhosocial.activerecord.backend.impl.sqlite.__main__ import _resolve_connection_config

        with patch("rhosocial.activerecord.backend.impl.sqlite.__main__.NamedConnectionResolver"):
            config = _resolve_connection_config(args)

        assert config.database == "/tmp/test.db"

    def test_named_connection_only(self):
        """Test --named-connection without --db-file."""
        args = MockArgs(named_connection="myapp.connections.prod_db")
        from rhosocial.activerecord.backend.impl.sqlite.__main__ import _resolve_connection_config

        mock_resolver = MagicMock()
        mock_config = SQLiteConnectionConfig(database="/prod/path.db")
        mock_resolver.load.return_value = mock_resolver
        mock_resolver.resolve.return_value = mock_config

        with patch(
            "rhosocial.activerecord.backend.impl.sqlite.__main__.NamedConnectionResolver",
            return_value=mock_resolver,
        ):
            config = _resolve_connection_config(args)

        mock_resolver.load.assert_called_once()
        mock_resolver.resolve.assert_called_once_with({})
        assert config.database == "/prod/path.db"

    def test_named_connection_with_conn_params(self):
        """Test --named-connection with --conn-param overrides."""
        args = MockArgs(
            named_connection="myapp.connections.prod_db",
            connection_params=["database=/custom/path.db", "timeout=30"],
        )
        from rhosocial.activerecord.backend.impl.sqlite.__main__ import _resolve_connection_config

        mock_resolver = MagicMock()
        mock_config = SQLiteConnectionConfig(database="/prod/path.db", timeout=10.0)
        mock_resolver.load.return_value = mock_resolver
        mock_resolver.resolve.return_value = mock_config

        with patch(
            "rhosocial.activerecord.backend.impl.sqlite.__main__.NamedConnectionResolver",
            return_value=mock_resolver,
        ):
            config = _resolve_connection_config(args)

        mock_resolver.resolve.assert_called_once_with(
            {"database": "/custom/path.db", "timeout": "30"}
        )

    def test_named_connection_overridden_by_db_file(self):
        """Test that --db-file overrides named connection's database."""
        args = MockArgs(
            named_connection="myapp.connections.prod_db",
            db_file="/overridden/path.db",
        )
        from rhosocial.activerecord.backend.impl.sqlite.__main__ import _resolve_connection_config

        mock_resolver = MagicMock()
        mock_config = SQLiteConnectionConfig(database="/prod/path.db")
        mock_resolver.load.return_value = mock_resolver
        mock_resolver.resolve.return_value = mock_config

        with patch(
            "rhosocial.activerecord.backend.impl.sqlite.__main__.NamedConnectionResolver",
            return_value=mock_resolver,
        ):
            config = _resolve_connection_config(args)

        mock_resolver.resolve.assert_called_once_with({})
        assert config.database == "/overridden/path.db"

    def test_db_file_with_conn_params(self):
        """Test --db-file with --conn-param (db-file should win)."""
        args = MockArgs(
            db_file="/explicit/path.db",
            connection_params=["timeout=60"],
        )
        from rhosocial.activerecord.backend.impl.sqlite.__main__ import _resolve_connection_config

        with patch("rhosocial.activerecord.backend.impl.sqlite.__main__.NamedConnectionResolver"):
            config = _resolve_connection_config(args)

        assert config.database == "/explicit/path.db"


class TestSQLiteConnectionConfigDefaults:
    """Test SQLiteConnectionConfig default values."""

    def test_default_database_is_memory(self):
        """Test that default database is :memory:."""
        config = SQLiteConnectionConfig()
        assert config.database == ":memory:"

    def test_default_timeout(self):
        """Test that default timeout is 5.0."""
        config = SQLiteConnectionConfig()
        assert config.timeout == 5.0

    def test_default_cached_statements(self):
        """Test that default cached_statements is 128."""
        config = SQLiteConnectionConfig()
        assert config.cached_statements == 128

    def test_default_autocommit(self):
        """Test that default autocommit is False."""
        config = SQLiteConnectionConfig()
        assert config.autocommit is False

    def test_default_check_same_thread(self):
        """Test that default check_same_thread is True."""
        config = SQLiteConnectionConfig()
        assert config.check_same_thread is True