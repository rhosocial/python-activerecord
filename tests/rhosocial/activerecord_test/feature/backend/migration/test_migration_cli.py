# tests/rhosocial/activerecord_test/feature/backend/migration/test_cli.py
"""
Tests for the named-migration CLI integration.

Covers:
    - list_named_migrations_in_module()
    - create_named_migration_parser() argument setup
    - handle_named_migration() with --list, --describe, --dry-run
    - handle_named_migration() execution with SQLite backend
    - _resolve_record_store helper
"""

import argparse
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import pytest

from rhosocial.activerecord.backend.migration.cli import (
    _resolve_record_store,
    list_named_migrations_in_module,
)
from rhosocial.activerecord.backend.migration import (
    JSONFileMigrationRecordStore,
    MigrationDialectError,
    MigrationDirection,
)
# ══════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════

def _make_temp_json_store():
    """Create a temporary JSONFileMigrationRecordStore with valid initial content."""
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    # Write valid initial JSON so the store loads without error
    with open(path, "w") as f:
        f.write("[]")
    store = JSONFileMigrationRecordStore(path)
    return store, path


@pytest.fixture
def cli_args():
    """Create a minimal argparse Namespace mimicking CLI arguments."""
    args = argparse.Namespace()
    args.qualified_name = (
        "rhosocial.activerecord.backend.impl.sqlite.examples"
        ".named_migrations.migrations.V001CreateUsers"
    )
    args.direction = "up"
    args.dry_run = False
    args.describe = False
    args.list_migrations = False
    args.all_migrations = False
    args.record_store = None
    args.params = []
    args.db_file = None
    args.named_connection = None
    args.connection_params = []
    args.output = "table"
    args.rich_ascii = True
    return args


# ══════════════════════════════════════════════════════════════════════
# list_named_migrations_in_module
# ══════════════════════════════════════════════════════════════════════

class TestListMigrations:
    def test_list_via_example_module(self):
        """List migrations from the example migration module."""
        results = list_named_migrations_in_module(
            "rhosocial.activerecord.backend.impl.sqlite.examples"
            ".named_migrations.migrations"
        )
        versions = {r["version"] for r in results}
        assert "v001_create_users" in versions
        assert "v002_create_posts" in versions

    def test_list_empty_module(self):
        """A module with no NamedMigration subclasses returns empty list."""
        import types
        mod = types.ModuleType("_test_empty_mig_module")
        mod.foo = lambda: None
        sys.modules["_test_empty_mig_module"] = mod
        try:
            results = list_named_migrations_in_module("_test_empty_mig_module")
            assert results == []
        finally:
            del sys.modules["_test_empty_mig_module"]


# ══════════════════════════════════════════════════════════════════════
# _resolve_record_store
# ══════════════════════════════════════════════════════════════════════

class TestResolveRecordStore:
    def test_none(self):
        assert _resolve_record_store(None) is None
        assert _resolve_record_store("") is None

    def test_json_file_path(self):
        store = _resolve_record_store("/tmp/test_mig_store.json")
        assert isinstance(store, JSONFileMigrationRecordStore)

    def test_with_dots_looks_like_fqn(self):
        # A string containing dots but not ending in .json and no slash
        # will be treated as FQN, which will fail import — expect sys.exit
        with pytest.raises(SystemExit):
            _resolve_record_store("nonexistent.module.ClassName")


# ══════════════════════════════════════════════════════════════════════
# Parser creation
# ══════════════════════════════════════════════════════════════════════

class TestCreateParser:
    def test_parser_has_expected_arguments(self):
        from rhosocial.activerecord.backend.migration.cli import (
            create_named_migration_parser,
        )

        parent = argparse.ArgumentParser(add_help=False)
        parent.add_argument("--db-file")
        parent.add_argument("-o", "--output")

        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers()
        create_named_migration_parser(subparsers, parent)

        # Parse known arguments (must prefix with subcommand name)
        args = main_parser.parse_args(
            [
                "named-migration",
                "myapp.migrations.v001.CreateUsersTable",
                "--db-file",
                "test.db",
                "--direction",
                "down",
                "--dry-run",
            ]
        )
        assert args.qualified_name == "myapp.migrations.v001.CreateUsersTable"
        assert args.direction == "down"
        assert args.dry_run is True

    def test_parser_defaults(self):
        from rhosocial.activerecord.backend.migration.cli import (
            create_named_migration_parser,
        )

        parent = argparse.ArgumentParser(add_help=False)
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers()
        create_named_migration_parser(subparsers, parent)

        args = main_parser.parse_args(["named-migration", "some.fqn"])
        assert args.direction == "up"
        assert args.dry_run is False
        assert args.describe is False
        assert args.list_migrations is False
        assert args.all_migrations is False
        assert args.record_store is None
        assert args.params == []

    def test_parser_all_flag(self):
        from rhosocial.activerecord.backend.migration.cli import (
            create_named_migration_parser,
        )

        parent = argparse.ArgumentParser(add_help=False)
        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers()
        create_named_migration_parser(subparsers, parent)

        args = main_parser.parse_args(
            ["named-migration", "myapp.migrations", "--all", "--record-store", "./mig.json"]
        )
        assert args.all_migrations is True
        assert args.record_store == "./mig.json"


# ══════════════════════════════════════════════════════════════════════
# handle_named_migration — describe mode
# ══════════════════════════════════════════════════════════════════════

class TestHandleDescribe:
    def test_describe_example_migration(self, capsys, cli_args):
        from rhosocial.activerecord.backend.migration.cli import (
            handle_named_migration,
        )

        provider = MagicMock()
        cli_args.describe = True

        handle_named_migration(cli_args, provider, backend_factory=None)

        captured = capsys.readouterr()
        assert "v001_create_users" in captured.out
        assert "Dependencies: none" in captured.out
        assert "Parameters:" in captured.out

    def test_describe_with_dependencies(self, capsys, cli_args):
        from rhosocial.activerecord.backend.migration.cli import (
            handle_named_migration,
        )

        provider = MagicMock()
        cli_args.describe = True
        cli_args.qualified_name = (
            "rhosocial.activerecord.backend.impl.sqlite.examples"
            ".named_migrations.migrations.V002CreatePosts"
        )

        handle_named_migration(cli_args, provider, backend_factory=None)

        captured = capsys.readouterr()
        assert "v002_create_posts" in captured.out
        assert "Dependencies:" in captured.out

    def test_describe_nonexistent_fqn(self, capsys, cli_args):
        from rhosocial.activerecord.backend.migration.cli import (
            handle_named_migration,
        )

        provider = MagicMock()
        cli_args.describe = True
        cli_args.qualified_name = "nonexistent.module.ClassName"

        with pytest.raises(SystemExit):
            handle_named_migration(cli_args, provider, backend_factory=None)


# ══════════════════════════════════════════════════════════════════════
# handle_named_migration — dry-run mode
# ══════════════════════════════════════════════════════════════════════

class TestHandleDryRun:
    def test_dry_run_output(self, capsys, cli_args, sqlite_backend):
        from rhosocial.activerecord.backend.migration.cli import (
            handle_named_migration,
        )

        provider = MagicMock()
        cli_args.dry_run = True

        def backend_factory():
            return sqlite_backend

        handle_named_migration(cli_args, provider, backend_factory=backend_factory)

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "v001_create_users" in captured.out
        assert "direction: up" in captured.out.lower() or "Direction: up" in captured.out

    def test_dry_run_with_record_store(self, capsys, cli_args, sqlite_backend):
        from rhosocial.activerecord.backend.migration.cli import (
            handle_named_migration,
        )

        provider = MagicMock()
        cli_args.dry_run = True
        cli_args.record_store = "/tmp/_test_dry_run_record.json"

        def backend_factory():
            return sqlite_backend

        handle_named_migration(cli_args, provider, backend_factory=backend_factory)

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "Record store" in captured.out


# ══════════════════════════════════════════════════════════════════════
# handle_named_migration — list mode
# ══════════════════════════════════════════════════════════════════════

class TestHandleList:
    def test_list_migrations(self, cli_args):
        from rhosocial.activerecord.backend.migration.cli import (
            handle_named_migration,
        )

        provider = MagicMock()
        cli_args.list_migrations = True
        cli_args.qualified_name = (
            "rhosocial.activerecord.backend.impl.sqlite.examples"
            ".named_migrations.migrations"
        )

        handle_named_migration(cli_args, provider, backend_factory=None)

        # The provider.print_table should have been called
        provider.print_table.assert_called_once()
        call_args = provider.print_table.call_args
        rows = call_args[0][0]  # first positional arg: rows list
        names = {r["Name"] for r in rows}
        assert "V001CreateUsers" in names
        assert "V002CreatePosts" in names

    def test_list_nonexistent_module(self, capsys, cli_args):
        from rhosocial.activerecord.backend.migration.cli import (
            handle_named_migration,
        )

        provider = MagicMock()
        cli_args.list_migrations = True
        cli_args.qualified_name = "nonexistent.module"

        with pytest.raises(SystemExit):
            handle_named_migration(cli_args, provider, backend_factory=None)


# ══════════════════════════════════════════════════════════════════════
# handle_named_migration — actual execution (SQLite integration)
# ══════════════════════════════════════════════════════════════════════

class TestHandleExecute:
    def test_execute_up_and_down(self, capsys, sqlite_backend):
        """Run a migration UP then DOWN through the CLI handler."""
        from rhosocial.activerecord.backend.migration.cli import (
            handle_named_migration,
        )

        provider = MagicMock()
        args = argparse.Namespace()
        args.qualified_name = (
            "rhosocial.activerecord.backend.impl.sqlite.examples"
            ".named_migrations.migrations.V001CreateUsers"
        )
        args.direction = "up"
        args.dry_run = False
        args.describe = False
        args.list_migrations = False
        args.record_store = None
        args.params = []
        args.output = "table"
        args.rich_ascii = True

        backend = sqlite_backend

        def backend_factory():
            return backend

        def disconnect():
            pass

        # Execute UP
        handle_named_migration(
            args, provider, backend_factory=backend_factory,
            disconnect=disconnect,
        )
        captured = capsys.readouterr()
        assert "v001_create_users" in captured.out
        assert "up" in captured.out

        # Verify table exists
        cursor = backend.connection.cursor()
        cursor.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='users'"
        )
        assert cursor.fetchone()[0] == 1

        # Execute DOWN
        args.direction = "down"
        handle_named_migration(
            args, provider, backend_factory=backend_factory,
            disconnect=disconnect,
        )
        captured = capsys.readouterr()
        assert "v001_create_users" in captured.out
        assert "down" in captured.out.lower() or "down" in captured.out

        # Verify table dropped
        cursor.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='users'"
        )
        assert cursor.fetchone()[0] == 0

    def test_execute_with_record_store(self, capsys, sqlite_backend):
        """Record store enables duplicate protection via CLI."""
        from rhosocial.activerecord.backend.migration.cli import (
            handle_named_migration,
        )

        provider = MagicMock()
        store, store_path = _make_temp_json_store()

        args = argparse.Namespace()
        args.qualified_name = (
            "rhosocial.activerecord.backend.impl.sqlite.examples"
            ".named_migrations.migrations.V001CreateUsers"
        )
        args.direction = "up"
        args.dry_run = False
        args.describe = False
        args.list_migrations = False
        args.record_store = store_path
        args.params = []
        args.output = "table"
        args.rich_ascii = True

        backend = sqlite_backend

        def backend_factory():
            return backend

        def disconnect():
            pass

        # First execution should succeed
        handle_named_migration(
            args, provider, backend_factory=backend_factory,
            disconnect=disconnect,
        )

        # Second execution should fail (duplicate protection)
        with pytest.raises(SystemExit):
            handle_named_migration(
                args, provider, backend_factory=backend_factory,
                disconnect=disconnect,
            )
        captured = capsys.readouterr()
        assert "already been applied" in captured.err.lower() or "already" in captured.err

        # Cleanup
        if os.path.exists(store_path):
            os.unlink(store_path)

# ══════════════════════════════════════════════════════════════════════
# handle_named_migration — --all mode
# ══════════════════════════════════════════════════════════════════════

class TestHandleAll:
    def test_all_without_record_store_errors(self, capsys, sqlite_backend):
        from rhosocial.activerecord.backend.migration.cli import (
            handle_named_migration,
        )

        provider = MagicMock()
        args = argparse.Namespace()
        args.qualified_name = (
            "rhosocial.activerecord.backend.impl.sqlite.examples"
            ".named_migrations.migrations"
        )
        args.all_migrations = True
        args.direction = "up"
        args.dry_run = False
        args.describe = False
        args.list_migrations = False
        args.record_store = None
        args.params = []
        args.output = "table"
        args.rich_ascii = True

        def backend_factory():
            return sqlite_backend

        def disconnect():
            pass

        with pytest.raises(SystemExit):
            handle_named_migration(
                args, provider, backend_factory=backend_factory, disconnect=disconnect,
            )
        captured = capsys.readouterr()
        assert "record-store" in captured.err.lower()

    def test_all_up_applies_pending(self, capsys, sqlite_backend):
        from rhosocial.activerecord.backend.migration.cli import (
            handle_named_migration,
        )

        provider = MagicMock()
        store, store_path = _make_temp_json_store()

        args = argparse.Namespace()
        args.qualified_name = (
            "rhosocial.activerecord.backend.impl.sqlite.examples"
            ".named_migrations.migrations"
        )
        args.all_migrations = True
        args.direction = "up"
        args.dry_run = False
        args.describe = False
        args.list_migrations = False
        args.record_store = store_path
        args.params = []
        args.output = "table"
        args.rich_ascii = True

        backend = sqlite_backend

        def backend_factory():
            return backend

        def disconnect():
            pass

        handle_named_migration(
            args, provider, backend_factory=backend_factory, disconnect=disconnect,
        )
        captured = capsys.readouterr()
        assert "applied" in captured.out
        assert "v001_create_users" in captured.out
        assert "v002_create_posts" in captured.out

        # Verify both are recorded
        from rhosocial.activerecord.backend.migration import JSONFileMigrationRecordStore
        store2 = JSONFileMigrationRecordStore(store_path)
        assert store2.is_applied("v001_create_users") is True
        assert store2.is_applied("v002_create_posts") is True

        if os.path.exists(store_path):
            os.unlink(store_path)

    def test_all_dry_run(self, capsys, sqlite_backend):
        from rhosocial.activerecord.backend.migration.cli import (
            handle_named_migration,
        )

        provider = MagicMock()
        store, store_path = _make_temp_json_store()

        args = argparse.Namespace()
        args.qualified_name = (
            "rhosocial.activerecord.backend.impl.sqlite.examples"
            ".named_migrations.migrations"
        )
        args.all_migrations = True
        args.direction = "up"
        args.dry_run = True
        args.describe = False
        args.list_migrations = False
        args.record_store = store_path
        args.params = []
        args.output = "table"
        args.rich_ascii = True

        backend = sqlite_backend

        def backend_factory():
            return backend

        def disconnect():
            pass

        handle_named_migration(
            args, provider, backend_factory=backend_factory, disconnect=disconnect,
        )
        captured = capsys.readouterr()
        assert "DRY RUN" in captured.out
        assert "2" in captured.out

        # Dry-run should not create tables
        cursor = backend.connection.cursor()
        cursor.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='users'"
        )
        assert cursor.fetchone()[0] == 0

        if os.path.exists(store_path):
            os.unlink(store_path)

    def test_all_down_rolls_back(self, capsys, sqlite_backend):
        from rhosocial.activerecord.backend.migration.cli import (
            handle_named_migration,
        )

        provider = MagicMock()
        store, store_path = _make_temp_json_store()

        args = argparse.Namespace()
        args.qualified_name = (
            "rhosocial.activerecord.backend.impl.sqlite.examples"
            ".named_migrations.migrations"
        )
        args.all_migrations = True
        args.direction = "up"
        args.dry_run = False
        args.describe = False
        args.list_migrations = False
        args.record_store = store_path
        args.params = []
        args.output = "table"
        args.rich_ascii = True

        backend = sqlite_backend

        def backend_factory():
            return backend

        def disconnect():
            pass

        handle_named_migration(
            args, provider, backend_factory=backend_factory, disconnect=disconnect,
        )

        args.direction = "down"
        handle_named_migration(
            args, provider, backend_factory=backend_factory, disconnect=disconnect,
        )
        captured = capsys.readouterr()
        assert "applied" in captured.out
        assert "v001_create_users" in captured.out
        assert "v002_create_posts" in captured.out

        from rhosocial.activerecord.backend.migration import JSONFileMigrationRecordStore
        store2 = JSONFileMigrationRecordStore(store_path)
        assert store2.is_applied("v001_create_users") is False
        assert store2.is_applied("v002_create_posts") is False

        if os.path.exists(store_path):
            os.unlink(store_path)
