# tests/rhosocial/activerecord_test/feature/backend/named_connection/test_resolver.py
"""
Tests for named connection resolver.

This test module covers:
- NamedConnectionResolver class
- validate_connection_config function
- resolve_named_connection function
- list_named_connections_in_module function
- SQLite-specific: memory vs file connections
"""
import types
from unittest.mock import MagicMock, patch
import pytest

from rhosocial.activerecord.backend.named_connection.resolver import (
    NamedConnectionResolver,
    resolve_named_connection,
    list_named_connections_in_module,
)
from rhosocial.activerecord.backend.named_connection.exceptions import (
    NamedConnectionNotFoundError,
    NamedConnectionModuleNotFoundError,
    NamedConnectionInvalidReturnTypeError,
    NamedConnectionNotCallableError,
    NamedConnectionMissingParameterError,
    NamedConnectionInvalidParameterError,
)
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import (
    SQLiteConnectionConfig,
    SQLiteInMemoryConfig,
)


class TestNamedConnectionResolverInit:
    """Tests for NamedConnectionResolver.__init__."""

    def test_valid_qualified_name(self):
        """Test initialization with valid qualified name."""
        resolver = NamedConnectionResolver("myapp.connections.prod_db")
        assert resolver.qualified_name == "myapp.connections.prod_db"

    def test_invalid_qualified_name_no_dot(self):
        """Test initialization fails without dot."""
        with pytest.raises(NamedConnectionNotFoundError) as exc:
            NamedConnectionResolver("nodot")
        assert "must be in the format" in str(exc.value)

    def test_valid_qualified_name_nested_module(self):
        """Test initialization with nested module (3 parts)."""
        resolver = NamedConnectionResolver("my.app.connections.prod_db")
        assert resolver.qualified_name == "my.app.connections.prod_db"

    def test_empty_qualified_name(self):
        """Test initialization fails with empty name."""
        with pytest.raises(NamedConnectionNotFoundError):
            NamedConnectionResolver("")


class TestNamedConnectionResolverLoad:
    """Tests for NamedConnectionResolver.load()."""

    def test_load_function_success(self):
        """Test loading a function successfully."""
        module = types.ModuleType("test_connections")

        def test_func(pool_size: int = 5):
            return SQLiteInMemoryConfig()

        module.test_func = test_func
        with patch("importlib.import_module", return_value=module):
            resolver = NamedConnectionResolver("test_connections.test_func").load()
            assert resolver._callable is not None
            assert resolver._target_callable is not None

    def test_load_class_success(self):
        """Test loading a class successfully."""
        module = types.ModuleType("test_connection_classes")

        class ConnectionFactory:
            def __call__(self):
                return SQLiteInMemoryConfig()

        module.ConnectionFactory = ConnectionFactory
        with patch("importlib.import_module", return_value=module):
            resolver = NamedConnectionResolver("test_connection_classes.ConnectionFactory").load()
            assert resolver._is_class is True
            assert resolver._instance is not None

    def test_load_module_not_found(self):
        """Test loading fails when module doesn't exist."""
        with pytest.raises(NamedConnectionModuleNotFoundError):
            NamedConnectionResolver("nonexistent.module.func").load()

    def test_load_attribute_not_found(self):
        """Test loading fails when attribute doesn't exist."""
        module = types.ModuleType("test_connections")
        module.__all__ = []
        with patch("importlib.import_module", return_value=module):
            with pytest.raises(NamedConnectionNotFoundError) as exc:
                NamedConnectionResolver("test_connections.nonexistent").load()
            assert "not found" in str(exc.value)

    def test_load_not_callable(self):
        """Test loading fails when attribute is not callable."""
        module = types.ModuleType("test_non_callable")
        module.not_callable = "just a string"

        with patch("importlib.import_module", return_value=module):
            with pytest.raises(NamedConnectionNotCallableError):
                NamedConnectionResolver("test_non_callable.not_callable").load()


class TestNamedConnectionResolverResolve:
    """Tests for NamedConnectionResolver.resolve()."""

    def test_resolve_memory_connection(self):
        """Test resolving an in-memory SQLite connection."""
        module = types.ModuleType("test_connections")

        def memory_db():
            return SQLiteInMemoryConfig()

        module.memory_db = memory_db
        with patch("importlib.import_module", return_value=module):
            config = NamedConnectionResolver("test_connections.memory_db").load().resolve({})
            assert isinstance(config, SQLiteInMemoryConfig)

    def test_resolve_file_connection(self):
        """Test resolving a file-based SQLite connection."""
        module = types.ModuleType("test_connections")

        def file_db(path: str = "/tmp/test.sqlite"):
            return SQLiteConnectionConfig(database=path)

        module.file_db = file_db
        with patch("importlib.import_module", return_value=module):
            config = NamedConnectionResolver("test_connections.file_db").load().resolve({})
            assert isinstance(config, SQLiteConnectionConfig)
            assert config.database == "/tmp/test.sqlite"

    def test_resolve_with_user_params(self):
        """Test resolving with user-provided parameters."""
        module = types.ModuleType("test_connections")

        def file_db(path: str = "/tmp/default.sqlite"):
            return SQLiteConnectionConfig(database=path)

        module.file_db = file_db
        with patch("importlib.import_module", return_value=module):
            config = NamedConnectionResolver("test_connections.file_db").load().resolve(
                {"path": "/tmp/custom.sqlite"}
            )
            assert isinstance(config, SQLiteConnectionConfig)
            assert config.database == "/tmp/custom.sqlite"

    def test_resolve_missing_required_param(self):
        """Test resolve fails when required parameter is missing."""
        module = types.ModuleType("test_connections")

        def file_db(path: str):
            return SQLiteConnectionConfig(database=path)

        module.file_db = file_db
        with patch("importlib.import_module", return_value=module):
            resolver = NamedConnectionResolver("test_connections.file_db").load()
            with pytest.raises(NamedConnectionMissingParameterError):
                resolver.resolve({})

    def test_resolve_unknown_param(self):
        """Test resolve fails with unknown parameter."""
        module = types.ModuleType("test_connections")

        def memory_db():
            return SQLiteInMemoryConfig()

        module.memory_db = memory_db
        with patch("importlib.import_module", return_value=module):
            resolver = NamedConnectionResolver("test_connections.memory_db").load()
            with pytest.raises(NamedConnectionInvalidParameterError):
                resolver.resolve({"unknown_param": "value"})

    def test_resolve_invalid_return_type(self):
        """Test resolve fails when callable returns non-BaseConfig."""
        module = types.ModuleType("test_connections")

        def bad_connection():
            return "not a config"

        module.bad_connection = bad_connection
        with patch("importlib.import_module", return_value=module):
            resolver = NamedConnectionResolver("test_connections.bad_connection").load()
            with pytest.raises(NamedConnectionInvalidReturnTypeError):
                resolver.resolve({})

    def test_resolve_before_load(self):
        """Test resolve before loading fails."""
        resolver = NamedConnectionResolver("myapp.connections.prod_db")
        with pytest.raises(NamedConnectionNotCallableError):
            resolver.resolve({})


class TestNamedConnectionResolverDescribe:
    """Tests for NamedConnectionResolver.describe()."""

    def test_describe_function(self):
        """Test describing a function."""
        module = types.ModuleType("test_connections")

        def memory_db():
            """In-memory SQLite database connection."""
            return SQLiteInMemoryConfig()

        module.memory_db = memory_db
        with patch("importlib.import_module", return_value=module):
            resolver = NamedConnectionResolver("test_connections.memory_db").load()
            info = resolver.describe()
            assert info["qualified_name"] == "test_connections.memory_db"
            assert info["is_class"] is False
            assert "docstring" in info
            assert "signature" in info
            assert "parameters" in info

    def test_describe_class(self):
        """Test describing a class."""
        module = types.ModuleType("test_connection_classes")

        class ConnectionFactory:
            def __call__(self):
                return SQLiteInMemoryConfig()

        module.ConnectionFactory = ConnectionFactory
        with patch("importlib.import_module", return_value=module):
            resolver = NamedConnectionResolver("test_connection_classes.ConnectionFactory").load()
            info = resolver.describe()
            assert info["is_class"] is True

    def test_describe_before_load(self):
        """Test describe before loading fails."""
        resolver = NamedConnectionResolver("myapp.connections.prod_db")
        with pytest.raises(NamedConnectionNotCallableError):
            resolver.describe()


class TestResolveNamedConnection:
    """Tests for the resolve_named_connection convenience function."""

    def test_resolve_named_connection(self):
        """Test one-step resolve."""
        module = types.ModuleType("test_connections")

        def memory_db():
            return SQLiteInMemoryConfig()

        module.memory_db = memory_db
        with patch("importlib.import_module", return_value=module):
            config = resolve_named_connection(
                "test_connections.memory_db", {}
            )
            assert isinstance(config, SQLiteInMemoryConfig)


class TestListNamedConnectionsInModule:
    """Tests for list_named_connections_in_module function."""

    def test_list_module_not_found(self):
        """Test listing from non-existent module."""
        with pytest.raises(NamedConnectionModuleNotFoundError):
            list_named_connections_in_module("nonexistent.module")

    def test_list_with_valid_functions(self):
        """Test listing with valid callables."""
        module = types.ModuleType("test_connections")

        def memory_db(backend_cls):
            return SQLiteInMemoryConfig()

        def file_db(backend_cls, path: str = "/tmp/test.sqlite"):
            return SQLiteConnectionConfig(database=path)

        module.memory_db = memory_db
        module.file_db = file_db

        with patch("importlib.import_module", return_value=module):
            connections = list_named_connections_in_module("test_connections")
            names = [c["name"] for c in connections]
            assert "memory_db" in names
            assert "file_db" in names

    def test_list_includes_all_callables(self):
        """Test that all callable functions are included (no backend_cls required)."""
        module = types.ModuleType("test_connections")

        def with_params(pool_size: int = 5):
            return SQLiteInMemoryConfig()

        def no_params():
            return SQLiteInMemoryConfig()

        module.with_params = with_params
        module.no_params = no_params

        with patch("importlib.import_module", return_value=module):
            connections = list_named_connections_in_module("test_connections")
            names = [c["name"] for c in connections]
            assert "with_params" in names
            assert "no_params" in names


class TestSqliteNamedConnectionsIntegration:
    """Integration tests using actual example_connections module."""

    def test_memory_db_connection(self):
        """Test resolving the memory_db named connection."""
        config = resolve_named_connection(
            "tests.rhosocial.activerecord_test.feature.backend.named_connection.example_connections.memory_db",
            {},
        )
        assert isinstance(config, SQLiteInMemoryConfig)

    def test_file_db_connection(self):
        """Test resolving the file_db named connection."""
        config = resolve_named_connection(
            "tests.rhosocial.activerecord_test.feature.backend.named_connection.example_connections.file_db",
            {},
        )
        assert isinstance(config, SQLiteConnectionConfig)
        assert config.database != ":memory:"
        assert config.delete_on_close is True

    def test_file_db_with_custom_delete(self):
        """Test resolving file_db with custom delete_on_close parameter."""
        config = resolve_named_connection(
            "tests.rhosocial.activerecord_test.feature.backend.named_connection.example_connections.file_db",
            {"delete_on_close": "false"},
        )
        assert isinstance(config, SQLiteConnectionConfig)
        assert config.delete_on_close is False

    def test_file_db_with_pragmas(self):
        """Test resolving file_db_with_pragmas named connection."""
        config = resolve_named_connection(
            "tests.rhosocial.activerecord_test.feature.backend.named_connection.example_connections.file_db_with_pragmas",
            {},
        )
        assert isinstance(config, SQLiteConnectionConfig)
        assert config.pragmas["journal_mode"] == "WAL"

    def test_file_db_with_custom_journal_mode(self):
        """Test resolving file_db_with_pragmas with custom journal_mode."""
        config = resolve_named_connection(
            "tests.rhosocial.activerecord_test.feature.backend.named_connection.example_connections.file_db_with_pragmas",
            {"journal_mode": "DELETE"},
        )
        assert isinstance(config, SQLiteConnectionConfig)
        assert config.pragmas["journal_mode"] == "DELETE"

    def test_file_db_with_timeout(self):
        """Test resolving file_db_with_timeout named connection."""
        config = resolve_named_connection(
            "tests.rhosocial.activerecord_test.feature.backend.named_connection.example_connections.file_db_with_timeout",
            {},
        )
        assert isinstance(config, SQLiteConnectionConfig)
        assert config.timeout == 5.0

    def test_file_db_with_custom_timeout(self):
        """Test resolving file_db_with_timeout with custom timeout."""
        config = resolve_named_connection(
            "tests.rhosocial.activerecord_test.feature.backend.named_connection.example_connections.file_db_with_timeout",
            {"timeout": "10.0"},
        )
        assert isinstance(config, SQLiteConnectionConfig)
        assert config.timeout == 10.0

    def test_memory_db_creates_working_backend(self):
        """Test that memory_db connection creates a connectable backend."""
        config = resolve_named_connection(
            "tests.rhosocial.activerecord_test.feature.backend.named_connection.example_connections.memory_db",
            {},
        )
        backend = SQLiteBackend(connection_config=config)
        backend.connect()
        assert backend._connection is not None
        backend.disconnect()

    def test_file_db_creates_working_backend(self):
        """Test that file_db connection creates a connectable backend."""
        config = resolve_named_connection(
            "tests.rhosocial.activerecord_test.feature.backend.named_connection.example_connections.file_db",
            {},
        )
        backend = SQLiteBackend(connection_config=config)
        backend.connect()
        assert backend._connection is not None
        backend.disconnect()

    def test_list_example_connections(self):
        """Test listing connections in example_connections module."""
        connections = list_named_connections_in_module(
            "tests.rhosocial.activerecord_test.feature.backend.named_connection.example_connections"
        )
        names = [c["name"] for c in connections]
        assert "memory_db" in names
        assert "file_db" in names
        assert "file_db_with_pragmas" in names
        assert "file_db_with_timeout" in names

    def test_describe_memory_db(self):
        """Test describing the memory_db connection."""
        resolver = NamedConnectionResolver(
            "tests.rhosocial.activerecord_test.feature.backend.named_connection.example_connections.memory_db"
        ).load()
        info = resolver.describe()
        assert info["is_class"] is False
        assert "In-memory" in info["docstring"]

    def test_describe_file_db(self):
        """Test describing the file_db connection."""
        resolver = NamedConnectionResolver(
            "tests.rhosocial.activerecord_test.feature.backend.named_connection.example_connections.file_db"
        ).load()
        info = resolver.describe()
        assert info["is_class"] is False
        assert "File-based" in info["docstring"]
        assert "delete_on_close" in info["parameters"]
