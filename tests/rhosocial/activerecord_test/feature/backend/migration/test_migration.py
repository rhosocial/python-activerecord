# tests/rhosocial/activerecord_test/feature/backend/migration/test_migration.py
"""
Tests for named migration functionality.

This test module covers:
- MigrationDirection enum
- NamedMigration base class (version, dependencies, up/down dispatch)
- MigrationContext (fields, defaults, inheritance from ProcedureContext)
- Migration exception hierarchy
- MigrationRecord, MigrationRecordStore, JSONFileMigrationRecordStore
- NamedMigrationResolver
- MigrationRunner (unit tests + SQLite integration)
"""

import sys
import types
from unittest.mock import MagicMock

import pytest


def register_temp_module(name: str, functions: dict):
    """Register a temporary module in sys.modules for testing."""
    mod = types.ModuleType(name)
    for func_name, func in functions.items():
        setattr(mod, func_name, func)
    mod.__all__ = list(functions.keys())
    sys.modules[name] = mod
    return mod


def unregister_temp_module(name: str):
    """Remove a previously registered temporary module."""
    if name in sys.modules:
        del sys.modules[name]

from rhosocial.activerecord.backend.migration import (
    MigrationDirection,
    NamedMigration,
    MigrationContext,
    MigrationError,
    MigrationDependencyError,
    MigrationAlreadyAppliedError,
    MigrationNotAppliedError,
    MigrationVersionConflictError,
    MigrationDialectError,
    MigrationRecord,
    MigrationRecordStore,
    JSONFileMigrationRecordStore,
    MigrationResult,
    NamedMigrationResolver,
    MigrationRunner,
)
from rhosocial.activerecord.backend.named_expression.procedure import (
    Procedure,
    ProcedureContext,
)
from rhosocial.activerecord.backend.named_expression.exceptions import (
    ProcedureError,
)


class TestMigrationDirection:
    """Tests for MigrationDirection enum."""

    def test_up_value(self):
        assert MigrationDirection.UP == "up"
        assert MigrationDirection.UP.value == "up"

    def test_down_value(self):
        assert MigrationDirection.DOWN == "down"
        assert MigrationDirection.DOWN.value == "down"

    def test_is_str_enum(self):
        """MigrationDirection should be a str enum for JSON serialization."""
        assert isinstance(MigrationDirection.UP, str)

    def test_from_string(self):
        assert MigrationDirection("up") == MigrationDirection.UP
        assert MigrationDirection("down") == MigrationDirection.DOWN

    def test_invalid_direction(self):
        with pytest.raises(ValueError):
            MigrationDirection("sideways")


class TestNamedMigrationClass:
    """Tests for NamedMigration class hierarchy and behavior."""

    def test_is_procedure_subclass(self):
        """NamedMigration should inherit from Procedure."""
        assert issubclass(NamedMigration, Procedure)

    def test_default_version(self):
        migration = NamedMigration()
        assert migration.version == ""

    def test_default_dependencies(self):
        migration = NamedMigration()
        assert migration.dependencies == []

    def test_up_not_implemented(self):
        """up() should raise NotImplementedError by default."""
        migration = NamedMigration()
        ctx = MagicMock()
        with pytest.raises(NotImplementedError):
            migration.up(ctx)

    def test_down_not_implemented(self):
        """down() should raise NotImplementedError by default."""
        migration = NamedMigration()
        ctx = MagicMock()
        with pytest.raises(NotImplementedError):
            migration.down(ctx)

    def test_run_dispatches_to_up(self):
        class AddTable(NamedMigration):
            version = "v001"
            def up(self, ctx):
                ctx.called_up = True
            def down(self, ctx):
                ctx.called_down = True

        migration = AddTable()
        ctx = MagicMock()
        ctx.direction = MigrationDirection.UP
        migration.run(ctx)
        assert ctx.called_up is True

    def test_run_dispatches_to_down(self):
        class AddTable(NamedMigration):
            version = "v001"
            def up(self, ctx):
                ctx.called_up = True
            def down(self, ctx):
                ctx.called_down = True

        migration = AddTable()
        ctx = MagicMock()
        ctx.direction = MigrationDirection.DOWN
        migration.run(ctx)
        assert ctx.called_down is True

    def test_custom_version_and_dependencies(self):
        class MyMigration(NamedMigration):
            version = "v003_add_index"
            dependencies = ["v001_create_users", "v002_add_email"]

        migration = MyMigration()
        assert migration.version == "v003_add_index"
        assert migration.dependencies == ["v001_create_users", "v002_add_email"]

    def test_get_parameters_inherited(self):
        """get_parameters() should work via Procedure inheritance."""
        class MyMigration(NamedMigration):
            version = "v001"
            some_param: str
            another_param: int = 42

        params = MyMigration.get_parameters()
        assert "some_param" in params
        assert "another_param" in params

    def test_get_parameters_excludes_run(self):
        """run() should be excluded from get_parameters()."""
        class MyMigration(NamedMigration):
            version = "v001"

        params = MyMigration.get_parameters()
        assert "run" not in params


class TestMigrationContext:
    """Tests for MigrationContext class."""

    def test_is_procedure_context_subclass(self):
        """MigrationContext should be a subclass of ProcedureContext."""
        assert issubclass(MigrationContext, ProcedureContext)

    def test_default_values(self, mock_dialect):
        ctx = MigrationContext(mock_dialect, lambda *a: None)
        assert ctx.direction is None
        assert ctx.dry_run is False
        assert ctx.record_store is None

    def test_set_direction(self, mock_dialect):
        ctx = MigrationContext(mock_dialect, lambda *a: None)
        ctx.direction = MigrationDirection.UP
        assert ctx.direction == MigrationDirection.UP
        ctx.direction = MigrationDirection.DOWN
        assert ctx.direction == MigrationDirection.DOWN

    def test_set_dry_run(self, mock_dialect):
        ctx = MigrationContext(mock_dialect, lambda *a: None)
        ctx.dry_run = True
        assert ctx.dry_run is True

    def test_set_record_store(self, mock_dialect):
        ctx = MigrationContext(mock_dialect, lambda *a: None)
        fake_store = MagicMock()
        ctx.record_store = fake_store
        assert ctx.record_store is fake_store

    def test_inherited_bindings(self, mock_dialect):
        """MigrationContext should inherit bindings from ProcedureContext."""
        ctx = MigrationContext(mock_dialect, lambda *a: None)
        assert ctx.bindings == {}

    def test_inherited_dialect(self, mock_dialect):
        """MigrationContext should inherit dialect from ProcedureContext."""
        ctx = MigrationContext(mock_dialect, lambda *a: None)
        assert ctx.dialect is mock_dialect


class TestMigrationExceptionHierarchy:
    """Tests for migration exception class hierarchy."""

    def test_migration_error_is_procedure_error(self):
        assert issubclass(MigrationError, ProcedureError)

    def test_dependency_error_hierarchy(self):
        assert issubclass(MigrationDependencyError, MigrationError)

    def test_already_applied_error_hierarchy(self):
        assert issubclass(MigrationAlreadyAppliedError, MigrationError)

    def test_not_applied_error_hierarchy(self):
        assert issubclass(MigrationNotAppliedError, MigrationError)

    def test_version_conflict_error_hierarchy(self):
        assert issubclass(MigrationVersionConflictError, MigrationError)

    def test_dialect_error_hierarchy(self):
        assert issubclass(MigrationDialectError, MigrationError)

    def test_raise_and_catch_migration_error(self):
        with pytest.raises(MigrationError):
            raise MigrationError("test error")

    def test_raise_and_catch_dependency_error(self):
        with pytest.raises(MigrationDependencyError):
            raise MigrationDependencyError("dependency missing")

    def test_catch_as_procedure_error(self):
        """Migration errors should be catchable as ProcedureError."""
        with pytest.raises(ProcedureError):
            raise MigrationAlreadyAppliedError("already applied")


class TestMigrationRecord:
    """Tests for MigrationRecord dataclass."""

    def test_create(self):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        rec = MigrationRecord(
            version="v001",
            migration_fqn="myapp.migrations.v001.MyMig",
            direction="up",
            applied_at=now,
            success=True,
        )
        assert rec.version == "v001"
        assert rec.migration_fqn == "myapp.migrations.v001.MyMig"
        assert rec.direction == "up"
        assert rec.applied_at is now
        assert rec.success is True
        assert rec.error_message is None
        assert rec.snapshot_before is None
        assert rec.snapshot_after is None

    def test_create_with_all_fields(self):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        rec = MigrationRecord(
            version="v002",
            migration_fqn="myapp.migrations.v002.MyMig",
            direction="down",
            applied_at=now,
            success=False,
            error_message="oops",
            snapshot_before={"tables": {}},
            snapshot_after={"tables": {"users": {}}},
        )
        assert rec.success is False
        assert rec.error_message == "oops"
        assert rec.snapshot_before == {"tables": {}}


class TestMigrationResult:
    """Tests for MigrationResult dataclass."""

    def test_create(self):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        result = MigrationResult(version="v001", applied_at=now, success=True)
        assert result.version == "v001"
        assert result.applied_at is now
        assert result.success is True
        assert result.snapshot_diff is None


class TestMigrationRecordStoreABC:
    """Tests for MigrationRecordStore abstract base class."""

    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            MigrationRecordStore()


class TestJSONFileMigrationRecordStore:
    """Tests for JSONFileMigrationRecordStore."""

    def test_empty_store(self, tmp_path):
        store = JSONFileMigrationRecordStore(tmp_path / "migrations.json")
        assert store.get_applied() == []

    def test_not_applied_returns_false(self, tmp_path):
        store = JSONFileMigrationRecordStore(tmp_path / "migrations.json")
        assert store.is_applied("v001") is False

    def test_record_and_is_applied(self, tmp_path):
        from datetime import datetime, timezone
        store = JSONFileMigrationRecordStore(tmp_path / "migrations.json")
        rec = MigrationRecord(
            version="v001",
            migration_fqn="test.MyMig",
            direction="up",
            applied_at=datetime.now(timezone.utc),
            success=True,
        )
        store.record(rec)
        assert store.is_applied("v001") is True

    def test_get_applied_excludes_failed(self, tmp_path):
        from datetime import datetime, timezone
        store = JSONFileMigrationRecordStore(tmp_path / "migrations.json")
        now = datetime.now(timezone.utc)
        store.record(MigrationRecord("v001", "t.M1", "up", now, success=True))
        store.record(MigrationRecord("v002", "t.M2", "up", now, success=False))
        applied = store.get_applied()
        versions = [r.version for r in applied]
        assert "v001" in versions
        assert "v002" not in versions

    def test_get_applied_excludes_rolled_back(self, tmp_path):
        from datetime import datetime, timezone
        store = JSONFileMigrationRecordStore(tmp_path / "migrations.json")
        now = datetime.now(timezone.utc)
        store.record(MigrationRecord("v001", "t.M1", "up", now, success=True))
        store.record(MigrationRecord("v001", "t.M1", "down", now, success=True))
        applied = store.get_applied()
        assert len(applied) == 0

    def test_record_persists_to_disk(self, tmp_path):
        from datetime import datetime, timezone
        path = tmp_path / "migrations.json"
        store1 = JSONFileMigrationRecordStore(path)
        store1.record(MigrationRecord(
            "v001", "test.M1", "up", datetime.now(timezone.utc), success=True,
        ))
        store2 = JSONFileMigrationRecordStore(path)
        assert store2.is_applied("v001") is True

    def test_get_applied_returns_up_records_without_down(self, tmp_path):
        from datetime import datetime, timezone
        store = JSONFileMigrationRecordStore(tmp_path / "migrations.json")
        now = datetime.now(timezone.utc)
        store.record(MigrationRecord("v001", "t.M1", "up", now, success=True))
        store.record(MigrationRecord("v002", "t.M2", "up", now, success=True))
        store.record(MigrationRecord("v001", "t.M1", "down", now, success=True))
        applied = store.get_applied()
        assert [r.version for r in applied] == ["v002"]


class TestNamedMigrationResolver:
    """Tests for NamedMigrationResolver."""

    def test_resolve(self):
        class TestMig(NamedMigration):
            version = "v001"

        register_temp_module("test_mig_resolver", {"TestMig": TestMig})
        try:
            cls = NamedMigrationResolver.resolve("test_mig_resolver.TestMig")
            assert cls is TestMig
        finally:
            unregister_temp_module("test_mig_resolver")

    def test_resolve_not_a_subclass(self):
        class NotAMigration:
            pass

        register_temp_module("test_mig_bad", {"NotAMigration": NotAMigration})
        try:
            with pytest.raises(TypeError, match="not a NamedMigration subclass"):
                NamedMigrationResolver.resolve("test_mig_bad.NotAMigration")
        finally:
            unregister_temp_module("test_mig_bad")

    def test_resolve_module_not_found(self):
        with pytest.raises(ModuleNotFoundError):
            NamedMigrationResolver.resolve("nonexistent.module.ClassName")

    def test_resolve_class_not_found(self):
        register_temp_module("test_mig_empty", {})
        try:
            with pytest.raises(AttributeError):
                NamedMigrationResolver.resolve("test_mig_empty.NonExistent")
        finally:
            unregister_temp_module("test_mig_empty")


class TestMigrationRunner:
    """Tests for MigrationRunner with mocked backend."""

    def test_init(self):
        class TestMig(NamedMigration):
            version = "v001"

        register_temp_module("test_runner_init", {"TestMig": TestMig})
        try:
            runner = MigrationRunner("test_runner_init.TestMig")
            assert runner.migration.version == "v001"
        finally:
            unregister_temp_module("test_runner_init")

    def test_dependency_check_fails(self):
        class TestMig(NamedMigration):
            version = "v002"
            dependencies = ["v001"]

        register_temp_module("test_runner_dep", {"TestMig": TestMig})
        try:
            runner = MigrationRunner("test_runner_dep.TestMig")
            backend = MagicMock()
            backend.dialect = MagicMock()
            record_store = MagicMock()
            record_store.is_applied.return_value = False

            with pytest.raises(MigrationDependencyError):
                runner.run(backend, MigrationDirection.UP, record_store=record_store)
        finally:
            unregister_temp_module("test_runner_dep")

    def test_duplicate_up_fails(self):
        class TestMig(NamedMigration):
            version = "v001"

        register_temp_module("test_runner_dup", {"TestMig": TestMig})
        try:
            runner = MigrationRunner("test_runner_dup.TestMig")
            backend = MagicMock()
            backend.dialect = MagicMock()
            record_store = MagicMock()
            record_store.is_applied.return_value = True

            with pytest.raises(MigrationAlreadyAppliedError):
                runner.run(backend, MigrationDirection.UP, record_store=record_store)
        finally:
            unregister_temp_module("test_runner_dup")

    def test_duplicate_down_fails(self):
        class TestMig(NamedMigration):
            version = "v001"

        register_temp_module("test_runner_down", {"TestMig": TestMig})
        try:
            runner = MigrationRunner("test_runner_down.TestMig")
            backend = MagicMock()
            backend.dialect = MagicMock()
            record_store = MagicMock()
            record_store.is_applied.return_value = False

            with pytest.raises(MigrationNotAppliedError):
                runner.run(backend, MigrationDirection.DOWN, record_store=record_store)
        finally:
            unregister_temp_module("test_runner_down")

    def test_dry_run_skips_execution(self):
        """dry_run=True runs the migration but skips backend.execute()."""
        executed = False
        sql_collected = []

        class TestMig(NamedMigration):
            version = "v001"
            def up(self, ctx):
                nonlocal executed
                executed = True

        register_temp_module("test_runner_dry", {"TestMig": TestMig})
        try:
            runner = MigrationRunner("test_runner_dry.TestMig")
            backend = MagicMock()
            backend.dialect = MagicMock()
            result = runner.run(backend, MigrationDirection.UP, dry_run=True)
            assert executed is True  # migration.run() is called during dry_run
            assert result.dry_run is True
            # dry_run_sql is a list even for no-op migrations
            assert result.dry_run_sql is not None
            assert isinstance(result.dry_run_sql, list)
        finally:
            unregister_temp_module("test_runner_dry")

    def test_dry_run_unsupported_feature(self):
        """dry_run=True should catch dialect incompatibility and wrap as MigrationDialectError."""
        # Register a named expression that produces an expression not supported
        # by SQLite — a table with PARTITION BY clause
        from rhosocial.activerecord.backend.expression.statements.ddl_table import (
            CreateTableExpression,
            ColumnDefinition,
            ColumnConstraint,
            ColumnConstraintType,
        )
        from rhosocial.activerecord.backend.expression.statements.ddl_partition import (
            PartitionClause,
            PartitionStrategy,
        )
        from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
            SQLiteIntegerType,
        )
        from rhosocial.activerecord.backend.expression.core import Column as ColExpr

        def unsupported_expr(dialect):
            col_def = ColumnDefinition(
                "id",
                SQLiteIntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)],
            )
            col_expr = ColExpr(dialect, "id")
            return CreateTableExpression(
                dialect,
                table="test_unsupported",
                columns=[col_def],
                partition=PartitionClause(
                    dialect,
                    method=PartitionStrategy.RANGE,
                    keys=[col_expr],
                ),
            )

        register_temp_module("dry_unsupported.expressions", {
            "unsupported_expr": unsupported_expr,
        })

        class TestUnsupported(NamedMigration):
            version = "v001"
            def up(self, ctx):
                ctx.execute("dry_unsupported.expressions.unsupported_expr")

        register_temp_module("dry_unsupported.migrations", {
            "TestUnsupported": TestUnsupported,
        })
        try:
            from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
            backend = SQLiteBackend(database=":memory:")
            backend.connect()
            try:
                runner = MigrationRunner("dry_unsupported.migrations.TestUnsupported")
                with pytest.raises(MigrationDialectError, match="PartitionSupport"):
                    runner.run(backend, MigrationDirection.UP, dry_run=True)
            finally:
                backend.disconnect()
        finally:
            unregister_temp_module("dry_unsupported.expressions")
            unregister_temp_module("dry_unsupported.migrations")




class TestMigrationRunnerIntegration:
    """Integration tests for MigrationRunner with a real SQLite backend."""

    @pytest.fixture(autouse=True)
    def _cleanup(self, request):
        """Ensure temp modules are cleaned up even on failure."""
        self._temp_modules = []
        yield
        for name in self._temp_modules:
            unregister_temp_module(name)
        self._temp_modules.clear()

    def _register(self, name, functions):
        mod = register_temp_module(name, functions)
        self._temp_modules.append(name)
        return mod

    def _make_create_users_expr(self, dialect):
        from rhosocial.activerecord.backend.expression.statements.ddl_table import (
            CreateTableExpression,
            ColumnDefinition,
            ColumnConstraint,
            ColumnConstraintType,
        )
        from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
            SQLiteIntegerType,
            SQLiteTextType,
        )

        return CreateTableExpression(
            dialect,
            table="users",
            columns=[
                ColumnDefinition(
                    "id",
                    SQLiteIntegerType(),
                    constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)],
                ),
                ColumnDefinition("name", SQLiteTextType()),
                ColumnDefinition("email", SQLiteTextType()),
            ],
        )

    def _make_drop_users_expr(self, dialect):
        from rhosocial.activerecord.backend.expression.statements.ddl_table import (
            DropTableExpression,
        )

        return DropTableExpression(dialect, table="users", if_exists=True)

    def test_up_creates_table(self, sqlite_backend):
        """Running a UP migration should create the expected table."""
        self._register("mig_sqlite_test.expressions", {
            "create_users_table": self._make_create_users_expr,
            "drop_users_table": self._make_drop_users_expr,
        })

        class V001CreateUsers(NamedMigration):
            version = "v001_create_users"
            def up(self, ctx):
                ctx.execute("mig_sqlite_test.expressions.create_users_table")
            def down(self, ctx):
                ctx.execute("mig_sqlite_test.expressions.drop_users_table")

        self._register("mig_sqlite_test.migrations", {"V001CreateUsers": V001CreateUsers})

        runner = MigrationRunner("mig_sqlite_test.migrations.V001CreateUsers")
        result = runner.run(sqlite_backend, MigrationDirection.UP)

        assert result.success is True
        assert result.version == "v001_create_users"
        cursor = sqlite_backend.connection.cursor()
        cursor.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='users'"
        )
        assert cursor.fetchone()[0] == 1

    def test_down_drops_table(self, sqlite_backend):
        """Running DOWN after UP should drop the table."""
        self._register("mig_sqlite_test2.expressions", {
            "create_users_table": self._make_create_users_expr,
            "drop_users_table": self._make_drop_users_expr,
        })

        class V001CreateUsers(NamedMigration):
            version = "v001_create_users"
            def up(self, ctx):
                ctx.execute("mig_sqlite_test2.expressions.create_users_table")
            def down(self, ctx):
                ctx.execute("mig_sqlite_test2.expressions.drop_users_table")

        self._register("mig_sqlite_test2.migrations", {"V001CreateUsers": V001CreateUsers})

        runner = MigrationRunner("mig_sqlite_test2.migrations.V001CreateUsers")
        runner.run(sqlite_backend, MigrationDirection.UP)
        result = runner.run(sqlite_backend, MigrationDirection.DOWN)

        assert result.success is True
        cursor = sqlite_backend.connection.cursor()
        cursor.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='users'"
        )
        assert cursor.fetchone()[0] == 0

    def test_record_store_records_up(self, sqlite_backend, tmp_path):
        """Running UP with a record store should write a record."""
        from rhosocial.activerecord.backend.migration import JSONFileMigrationRecordStore

        self._register("mig_sqlite_test3.expressions", {
            "create_users_table": self._make_create_users_expr,
            "drop_users_table": self._make_drop_users_expr,
        })

        class V001CreateUsers(NamedMigration):
            version = "v001_create_users"
            def up(self, ctx):
                ctx.execute("mig_sqlite_test3.expressions.create_users_table")
            def down(self, ctx):
                ctx.execute("mig_sqlite_test3.expressions.drop_users_table")

        self._register("mig_sqlite_test3.migrations", {"V001CreateUsers": V001CreateUsers})

        store = JSONFileMigrationRecordStore(tmp_path / "mig3.json")
        runner = MigrationRunner("mig_sqlite_test3.migrations.V001CreateUsers")
        result = runner.run(sqlite_backend, MigrationDirection.UP, record_store=store)

        assert result.success is True
        assert store.is_applied("v001_create_users") is True

    def test_record_store_tracks_down(self, sqlite_backend, tmp_path):
        """After DOWN, the record store should report the migration as not applied."""
        from rhosocial.activerecord.backend.migration import JSONFileMigrationRecordStore

        self._register("mig_sqlite_test4.expressions", {
            "create_users_table": self._make_create_users_expr,
            "drop_users_table": self._make_drop_users_expr,
        })

        class V001CreateUsers(NamedMigration):
            version = "v001_create_users"
            def up(self, ctx):
                ctx.execute("mig_sqlite_test4.expressions.create_users_table")
            def down(self, ctx):
                ctx.execute("mig_sqlite_test4.expressions.drop_users_table")

        self._register("mig_sqlite_test4.migrations", {"V001CreateUsers": V001CreateUsers})

        store = JSONFileMigrationRecordStore(tmp_path / "mig4.json")
        runner = MigrationRunner("mig_sqlite_test4.migrations.V001CreateUsers")
        runner.run(sqlite_backend, MigrationDirection.UP, record_store=store)
        runner.run(sqlite_backend, MigrationDirection.DOWN, record_store=store)

        assert store.is_applied("v001_create_users") is False

    def test_dry_run_with_real_backend(self, sqlite_backend):
        """dry_run should not create the table."""
        self._register("mig_sqlite_test5.expressions", {
            "create_users_table": self._make_create_users_expr,
            "drop_users_table": self._make_drop_users_expr,
        })

        class V001CreateUsers(NamedMigration):
            version = "v001_create_users"
            def up(self, ctx):
                ctx.execute("mig_sqlite_test5.expressions.create_users_table")
            def down(self, ctx):
                ctx.execute("mig_sqlite_test5.expressions.drop_users_table")

        self._register("mig_sqlite_test5.migrations", {"V001CreateUsers": V001CreateUsers})

        runner = MigrationRunner("mig_sqlite_test5.migrations.V001CreateUsers")
        result = runner.run(sqlite_backend, MigrationDirection.UP, dry_run=True)

        assert result.success is True
        assert result.dry_run is True
        # Verify SQL was collected and table was NOT created
        assert result.dry_run_sql is not None
        assert len(result.dry_run_sql) >= 1
        fqn, sql, params_sql = result.dry_run_sql[0]
        assert "CREATE TABLE" in sql.upper()
        cursor = sqlite_backend.connection.cursor()
        cursor.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='users'"
        )
        assert cursor.fetchone()[0] == 0

    def test_error_records_as_failure(self, sqlite_backend, tmp_path):
        """When up() raises, the record should show success=False."""
        from rhosocial.activerecord.backend.migration import JSONFileMigrationRecordStore

        self._register("mig_sqlite_test6.expressions", {
            "create_users_table": self._make_create_users_expr,
        })

        class V001Broken(NamedMigration):
            version = "v001_broken"
            def up(self, ctx):
                ctx.execute("mig_sqlite_test6.expressions.create_users_table")
                raise RuntimeError("something went wrong")
            def down(self, ctx):
                pass

        self._register("mig_sqlite_test6.migrations", {"V001Broken": V001Broken})

        store = JSONFileMigrationRecordStore(tmp_path / "mig6.json")
        runner = MigrationRunner("mig_sqlite_test6.migrations.V001Broken")

        with pytest.raises(RuntimeError, match="something went wrong"):
            runner.run(sqlite_backend, MigrationDirection.UP, record_store=store)

        records = store._records
        assert len(records) == 1
        assert records[0].success is False
        assert "something went wrong" in records[0].error_message

    def test_multiple_migrations(self, sqlite_backend, tmp_path):
        """Run two sequential migrations."""
        from rhosocial.activerecord.backend.migration import JSONFileMigrationRecordStore

        self._register("mig_sqlite_test7.expressions", {
            "create_users_table": self._make_create_users_expr,
            "drop_users_table": self._make_drop_users_expr,
        })

        class V001CreateUsers(NamedMigration):
            version = "v001"
            def up(self, ctx):
                ctx.execute("mig_sqlite_test7.expressions.create_users_table")
            def down(self, ctx):
                ctx.execute("mig_sqlite_test7.expressions.drop_users_table")

        class V002CreatePosts(NamedMigration):
            version = "v002"
            dependencies = ["v001"]
            def up(self, ctx):
                from rhosocial.activerecord.backend.expression.statements.ddl_table import (
                    CreateTableExpression,
                    ColumnDefinition,
                    ColumnConstraint,
                    ColumnConstraintType,
                )
                from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
                    SQLiteIntegerType,
                    SQLiteTextType,
                )
                expr = CreateTableExpression(
                    sqlite_backend.dialect,
                    table="posts",
                    columns=[
                        ColumnDefinition(
                            "id",
                            SQLiteIntegerType(),
                            constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)],
                        ),
                        ColumnDefinition("title", SQLiteTextType()),
                    ],
                )
                sqlite_backend.execute(*expr.to_sql())
            def down(self, ctx):
                from rhosocial.activerecord.backend.expression.statements.ddl_table import (
                    DropTableExpression,
                )
                expr = DropTableExpression(sqlite_backend.dialect, table="posts", if_exists=True)
                sqlite_backend.execute(*expr.to_sql())

        self._register("mig_sqlite_test7.migrations", {
            "V001CreateUsers": V001CreateUsers,
            "V002CreatePosts": V002CreatePosts,
        })

        store = JSONFileMigrationRecordStore(tmp_path / "mig7.json")

        r1 = MigrationRunner("mig_sqlite_test7.migrations.V001CreateUsers")
        result1 = r1.run(sqlite_backend, MigrationDirection.UP, record_store=store)
        assert result1.success is True

        r2 = MigrationRunner("mig_sqlite_test7.migrations.V002CreatePosts")
        result2 = r2.run(sqlite_backend, MigrationDirection.UP, record_store=store)
        assert result2.success is True

        assert store.is_applied("v001") is True
        assert store.is_applied("v002") is True

    def test_dependency_check_passes(self, sqlite_backend, tmp_path):
        """When dependency is applied, the migration should run successfully."""
        from rhosocial.activerecord.backend.migration import JSONFileMigrationRecordStore

        self._register("mig_sqlite_test8.expressions", {
            "create_users_table": self._make_create_users_expr,
            "drop_users_table": self._make_drop_users_expr,
        })

        class V001CreateUsers(NamedMigration):
            version = "v001"
            def up(self, ctx):
                ctx.execute("mig_sqlite_test8.expressions.create_users_table")
            def down(self, ctx):
                ctx.execute("mig_sqlite_test8.expressions.drop_users_table")

        class V002Depends(NamedMigration):
            version = "v002"
            dependencies = ["v001"]
            def up(self, ctx):
                pass
            def down(self, ctx):
                pass

        self._register("mig_sqlite_test8.migrations", {
            "V001CreateUsers": V001CreateUsers,
            "V002Depends": V002Depends,
        })

        store = JSONFileMigrationRecordStore(tmp_path / "mig8.json")
        runner1 = MigrationRunner("mig_sqlite_test8.migrations.V001CreateUsers")
        runner1.run(sqlite_backend, MigrationDirection.UP, record_store=store)

        runner2 = MigrationRunner("mig_sqlite_test8.migrations.V002Depends")
        result = runner2.run(sqlite_backend, MigrationDirection.UP, record_store=store)
        assert result.success is True


class TestUserParams:
    """Tests that user_params are properly applied to migration instances."""

    def test_user_params_applied_to_migration(self, sqlite_backend):
        class V001ParamMig(NamedMigration):
            version = "v001"
            table_name: str = "default_table"
            def up(self, ctx):
                from rhosocial.activerecord.backend.expression.statements.ddl_table import (
                    CreateTableExpression,
                    ColumnDefinition,
                    ColumnConstraint,
                    ColumnConstraintType,
                )
                from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
                    SQLiteIntegerType,
                    SQLiteTextType,
                )
                expr = CreateTableExpression(
                    ctx.dialect,
                    table=self.table_name,
                    columns=[
                        ColumnDefinition(
                            "id",
                            SQLiteIntegerType(),
                            constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)],
                        ),
                        ColumnDefinition("value", SQLiteTextType()),
                    ],
                )
                sqlite_backend.execute(*expr.to_sql())
            def down(self, ctx):
                from rhosocial.activerecord.backend.expression.statements.ddl_table import (
                    DropTableExpression,
                )
                expr = DropTableExpression(ctx.dialect, table=self.table_name, if_exists=True)
                sqlite_backend.execute(*expr.to_sql())

        register_temp_module("test_user_params.migrations", {"V001ParamMig": V001ParamMig})
        try:
            runner = MigrationRunner("test_user_params.migrations.V001ParamMig")
            result = runner.run(
                sqlite_backend,
                MigrationDirection.UP,
                user_params={"table_name": "custom_table"},
            )
            assert result.success is True
            cursor = sqlite_backend.connection.cursor()
            cursor.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='custom_table'"
            )
            assert cursor.fetchone()[0] == 1
            # clean up
            cursor.execute("DROP TABLE IF EXISTS custom_table")
            sqlite_backend.connection.commit()
        finally:
            unregister_temp_module("test_user_params.migrations")



@pytest.mark.asyncio
class TestAsyncMigrationRunnerIntegration:
    """Async integration tests for AsyncMigrationRunner."""

    @pytest.fixture(autouse=True)
    def _cleanup(self, request):
        self._temp_modules = []
        yield
        for name in self._temp_modules:
            unregister_temp_module(name)
        self._temp_modules.clear()

    def _register(self, name, functions):
        mod = register_temp_module(name, functions)
        self._temp_modules.append(name)
        return mod

    async def test_async_up_creates_table(self):
        from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
        from rhosocial.activerecord.backend.migration.async_runner import AsyncMigrationRunner

        backend = AsyncSQLiteBackend(database=":memory:")
        await backend.connect()
        try:
            self._register("async_mig_test.expressions", {
                "create_users_table": lambda dialect: _make_create_users_expr_static(dialect),
                "drop_users_table": lambda dialect: _make_drop_users_expr_static(dialect),
            })

            class V001CreateUsers(NamedMigration):
                version = "v001_create_users"
                async def run(self, ctx):
                    if ctx.direction == MigrationDirection.UP:
                        await ctx.execute("async_mig_test.expressions.create_users_table")
                    else:
                        await ctx.execute("async_mig_test.expressions.drop_users_table")

            self._register("async_mig_test.migrations", {"V001CreateUsers": V001CreateUsers})

            runner = AsyncMigrationRunner("async_mig_test.migrations.V001CreateUsers")
            result = await runner.run(backend, MigrationDirection.UP)

            assert result.success is True
            assert result.version == "v001_create_users"
            cursor = await backend._get_cursor()
            await cursor.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='users'"
            )
            row = await cursor.fetchone()
            assert row[0] == 1
            await cursor.close()
        finally:
            await backend.disconnect()

    async def test_async_up_then_down(self):
        from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
        from rhosocial.activerecord.backend.migration.async_runner import AsyncMigrationRunner

        backend = AsyncSQLiteBackend(database=":memory:")
        await backend.connect()
        try:
            self._register("async_mig_test2.expressions", {
                "create_users_table": lambda dialect: _make_create_users_expr_static(dialect),
                "drop_users_table": lambda dialect: _make_drop_users_expr_static(dialect),
            })

            class V001CreateUsers(NamedMigration):
                version = "v001"
                async def run(self, ctx):
                    if ctx.direction == MigrationDirection.UP:
                        await ctx.execute("async_mig_test2.expressions.create_users_table")
                    else:
                        await ctx.execute("async_mig_test2.expressions.drop_users_table")

            self._register("async_mig_test2.migrations", {"V001CreateUsers": V001CreateUsers})

            runner = AsyncMigrationRunner("async_mig_test2.migrations.V001CreateUsers")
            await runner.run(backend, MigrationDirection.UP)
            result = await runner.run(backend, MigrationDirection.DOWN)

            assert result.success is True
            cursor = await backend._get_cursor()
            await cursor.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='users'"
            )
            row = await cursor.fetchone()
            assert row[0] == 0
            await cursor.close()
        finally:
            await backend.disconnect()

    async def test_async_dry_run_skips_execution(self):
        from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
        from rhosocial.activerecord.backend.migration.async_runner import AsyncMigrationRunner

        backend = AsyncSQLiteBackend(database=":memory:")
        await backend.connect()
        try:
            self._register("async_mig_test3.expressions", {
                "create_users_table": lambda dialect: _make_create_users_expr_static(dialect),
                "drop_users_table": lambda dialect: _make_drop_users_expr_static(dialect),
            })

            class V001CreateUsers(NamedMigration):
                version = "v001"
                async def run(self, ctx):
                    await ctx.execute("async_mig_test3.expressions.create_users_table")

            self._register("async_mig_test3.migrations", {"V001CreateUsers": V001CreateUsers})

            runner = AsyncMigrationRunner("async_mig_test3.migrations.V001CreateUsers")
            result = await runner.run(backend, MigrationDirection.UP, dry_run=True)

            assert result.success is True
            assert result.dry_run is True
            # Verify SQL was collected and table was NOT created
            assert result.dry_run_sql is not None
            assert len(result.dry_run_sql) >= 1
            fqn, sql, params_sql = result.dry_run_sql[0]
            assert "CREATE TABLE" in sql.upper()
            cursor = await backend._get_cursor()
            await cursor.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='users'"
            )
            row = await cursor.fetchone()
            assert row[0] == 0
            await cursor.close()
        finally:
            await backend.disconnect()

    async def test_async_record_store(self, tmp_path):
        from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
        from rhosocial.activerecord.backend.migration.async_runner import AsyncMigrationRunner
        from rhosocial.activerecord.backend.migration import JSONFileMigrationRecordStore

        backend = AsyncSQLiteBackend(database=":memory:")
        await backend.connect()
        try:
            self._register("async_mig_test4.expressions", {
                "create_users_table": lambda dialect: _make_create_users_expr_static(dialect),
                "drop_users_table": lambda dialect: _make_drop_users_expr_static(dialect),
            })

            class V001CreateUsers(NamedMigration):
                version = "v001"
                async def run(self, ctx):
                    if ctx.direction == MigrationDirection.UP:
                        await ctx.execute("async_mig_test4.expressions.create_users_table")
                    else:
                        await ctx.execute("async_mig_test4.expressions.drop_users_table")

            self._register("async_mig_test4.migrations", {"V001CreateUsers": V001CreateUsers})

            store = JSONFileMigrationRecordStore(tmp_path / "async_mig.json")
            runner = AsyncMigrationRunner("async_mig_test4.migrations.V001CreateUsers")
            result = await runner.run(backend, MigrationDirection.UP, record_store=store)

            assert result.success is True
            assert store.is_applied("v001") is True
        finally:
            await backend.disconnect()

    async def test_async_user_params(self):
        from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
        from rhosocial.activerecord.backend.migration.async_runner import AsyncMigrationRunner

        backend = AsyncSQLiteBackend(database=":memory:")
        await backend.connect()
        try:
            class V001ParamMig(NamedMigration):
                version = "v001"
                table_name: str = "default_table"
                async def run(self, ctx):
                    from rhosocial.activerecord.backend.expression.statements.ddl_table import (
                        CreateTableExpression,
                        ColumnDefinition,
                        ColumnConstraint,
                        ColumnConstraintType,
                    )
                    from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
                        SQLiteIntegerType,
                        SQLiteTextType,
                    )
                    expr = CreateTableExpression(
                        ctx.dialect,
                        table=self.table_name,
                        columns=[
                            ColumnDefinition(
                                "id",
                                SQLiteIntegerType(),
                                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)],
                            ),
                            ColumnDefinition("value", SQLiteTextType()),
                        ],
                    )
                    await backend.execute(*expr.to_sql())

            self._register("async_mig_test5.migrations", {"V001ParamMig": V001ParamMig})

            runner = AsyncMigrationRunner("async_mig_test5.migrations.V001ParamMig")
            result = await runner.run(
                backend,
                MigrationDirection.UP,
                user_params={"table_name": "my_custom_table"},
            )
            assert result.success is True
            cursor = await backend._get_cursor()
            await cursor.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='my_custom_table'"
            )
            row = await cursor.fetchone()
            assert row[0] == 1
            await cursor.close()
        finally:
            await backend.disconnect()


def _make_create_users_expr_static(dialect):
    from rhosocial.activerecord.backend.expression.statements.ddl_table import (
        CreateTableExpression,
        ColumnDefinition,
        ColumnConstraint,
        ColumnConstraintType,
    )
    from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
        SQLiteIntegerType,
        SQLiteTextType,
    )
    return CreateTableExpression(
        dialect,
        table="users",
        columns=[
            ColumnDefinition(
                "id",
                SQLiteIntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)],
            ),
            ColumnDefinition("name", SQLiteTextType()),
            ColumnDefinition("email", SQLiteTextType()),
        ],
    )


def _make_drop_users_expr_static(dialect):
    from rhosocial.activerecord.backend.expression.statements.ddl_table import (
        DropTableExpression,
    )
    return DropTableExpression(dialect, table="users", if_exists=True)


class TestBatchMigrationRunner:
    """Tests for BatchMigrationRunner."""

    def test_discovers_migrations(self):
        from rhosocial.activerecord.backend.migration.batch_runner import BatchMigrationRunner

        register_temp_module("batch_discover.migrations", dict(
            V001CreateUsers=type("V001CreateUsers", (NamedMigration,), {
                "version": "v001",
                "dependencies": [],
            }),
            V002CreatePosts=type("V002CreatePosts", (NamedMigration,), {
                "version": "v002",
                "dependencies": ["v001"],
            }),
            NotAMigration=str,
        ))
        try:
            runner = BatchMigrationRunner("batch_discover.migrations")
            discovered = runner.discovered
            assert len(discovered) == 2
            versions = {d["version"] for d in discovered}
            assert versions == {"v001", "v002"}
        finally:
            unregister_temp_module("batch_discover.migrations")

    def test_topological_order(self):
        from rhosocial.activerecord.backend.migration.batch_runner import BatchMigrationRunner

        register_temp_module("batch_order.migrations", dict(
            V003=type("V003", (NamedMigration,), {
                "version": "v003",
                "dependencies": ["v002"],
            }),
            V001=type("V001", (NamedMigration,), {
                "version": "v001",
                "dependencies": [],
            }),
            V002=type("V002", (NamedMigration,), {
                "version": "v002",
                "dependencies": ["v001"],
            }),
        ))
        try:
            runner = BatchMigrationRunner("batch_order.migrations")
            ordered = runner._topological_order()
            versions_in_order = [v for v, _, _ in ordered]
            assert versions_in_order.index("v001") < versions_in_order.index("v002")
            assert versions_in_order.index("v002") < versions_in_order.index("v003")
        finally:
            unregister_temp_module("batch_order.migrations")

    def test_migrate_up_in_order(self, sqlite_backend, tmp_path):
        from rhosocial.activerecord.backend.migration.batch_runner import BatchMigrationRunner
        from rhosocial.activerecord.backend.migration import JSONFileMigrationRecordStore

        register_temp_module("batch_up.migrations", dict(
            V001=type("V001", (NamedMigration,), {
                "version": "v001",
                "dependencies": [],
                "up": lambda self, ctx: _run_create_users(sqlite_backend, ctx),
                "down": lambda self, ctx: _run_drop_users(sqlite_backend, ctx),
            }),
            V002=type("V002", (NamedMigration,), {
                "version": "v002",
                "dependencies": ["v001"],
                "up": lambda self, ctx: None,
                "down": lambda self, ctx: None,
            }),
        ))
        try:
            store = JSONFileMigrationRecordStore(tmp_path / "batch_up.json")
            runner = BatchMigrationRunner("batch_up.migrations")
            results = runner.migrate_up(sqlite_backend, record_store=store)
            assert len(results) == 2
            assert all(r.success for r in results)
            assert store.is_applied("v001") is True
            assert store.is_applied("v002") is True
        finally:
            unregister_temp_module("batch_up.migrations")

    def test_pending_versions(self, tmp_path):
        from rhosocial.activerecord.backend.migration.batch_runner import BatchMigrationRunner
        from rhosocial.activerecord.backend.migration import JSONFileMigrationRecordStore

        register_temp_module("batch_pending.migrations", dict(
            V001=type("V001", (NamedMigration,), {
                "version": "v001",
                "dependencies": [],
            }),
            V002=type("V002", (NamedMigration,), {
                "version": "v002",
                "dependencies": ["v001"],
            }),
        ))
        try:
            store = JSONFileMigrationRecordStore(tmp_path / "batch_pending.json")
            from rhosocial.activerecord.backend.migration.record import MigrationRecord
            from datetime import datetime, timezone
            store.record(MigrationRecord(
                version="v001",
                migration_fqn="batch_pending.migrations.V001",
                direction="up",
                applied_at=datetime.now(timezone.utc),
                success=True,
            ))
            runner = BatchMigrationRunner("batch_pending.migrations")
            pending = runner.pending_versions(store)
            assert pending == [("v002", "batch_pending.migrations.V002")]
        finally:
            unregister_temp_module("batch_pending.migrations")

    def test_status_report(self, tmp_path):
        from rhosocial.activerecord.backend.migration.batch_runner import BatchMigrationRunner
        from rhosocial.activerecord.backend.migration import JSONFileMigrationRecordStore

        register_temp_module("batch_status.migrations", dict(
            V001=type("V001", (NamedMigration,), {
                "version": "v001",
                "dependencies": [],
            }),
            V002=type("V002", (NamedMigration,), {
                "version": "v002",
                "dependencies": ["v001"],
            }),
        ))
        try:
            store = JSONFileMigrationRecordStore(tmp_path / "batch_status.json")
            from rhosocial.activerecord.backend.migration.record import MigrationRecord
            from datetime import datetime, timezone
            store.record(MigrationRecord(
                version="v001",
                migration_fqn="batch_status.migrations.V001",
                direction="up",
                applied_at=datetime.now(timezone.utc),
                success=True,
            ))
            runner = BatchMigrationRunner("batch_status.migrations")
            status_list = runner.status(store)
            assert len(status_list) == 2
            assert status_list[0]["applied"] is True
            assert status_list[1]["applied"] is False
        finally:
            unregister_temp_module("batch_status.migrations")

    def test_missing_dependency_raises(self):
        from rhosocial.activerecord.backend.migration.batch_runner import BatchMigrationRunner

        register_temp_module("batch_missing_dep.migrations", dict(
            V002=type("V002", (NamedMigration,), {
                "version": "v002",
                "dependencies": ["v001"],
            }),
        ))
        try:
            runner = BatchMigrationRunner("batch_missing_dep.migrations")
            with pytest.raises(MigrationDependencyError, match="v001"):
                runner._topological_order()
        finally:
            unregister_temp_module("batch_missing_dep.migrations")

    def test_migrate_down_in_reverse(self, sqlite_backend, tmp_path):
        from rhosocial.activerecord.backend.migration.batch_runner import BatchMigrationRunner
        from rhosocial.activerecord.backend.migration import JSONFileMigrationRecordStore

        register_temp_module("batch_down.migrations", dict(
            V001=type("V001", (NamedMigration,), {
                "version": "v001",
                "dependencies": [],
                "up": lambda self, ctx: _run_create_users(sqlite_backend, ctx),
                "down": lambda self, ctx: _run_drop_users(sqlite_backend, ctx),
            }),
            V002=type("V002", (NamedMigration,), {
                "version": "v002",
                "dependencies": ["v001"],
                "up": lambda self, ctx: _run_create_posts(sqlite_backend, ctx),
                "down": lambda self, ctx: _run_drop_posts(sqlite_backend, ctx),
            }),
        ))
        try:
            store = JSONFileMigrationRecordStore(tmp_path / "batch_down.json")
            runner = BatchMigrationRunner("batch_down.migrations")

            runner.migrate_up(sqlite_backend, record_store=store)
            assert store.is_applied("v001") is True
            assert store.is_applied("v002") is True

            results = runner.migrate_down(sqlite_backend, record_store=store)
            assert len(results) == 2
            assert all(r.success for r in results)
            assert store.is_applied("v002") is False
            assert store.is_applied("v001") is False
        finally:
            unregister_temp_module("batch_down.migrations")

    def test_single_transaction_rolls_back_on_failure(self, sqlite_backend, tmp_path):
        """single_transaction=True should roll back all migrations on failure."""
        from rhosocial.activerecord.backend.migration.batch_runner import BatchMigrationRunner
        from rhosocial.activerecord.backend.migration import JSONFileMigrationRecordStore

        register_temp_module("batch_txn.migrations", dict(
            V001=type("V001", (NamedMigration,), {
                "version": "v001",
                "dependencies": [],
                "up": lambda self, ctx: _run_create_users(sqlite_backend, ctx),
                "down": lambda self, ctx: _run_drop_users(sqlite_backend, ctx),
            }),
            V002=type("V002", (NamedMigration,), {
                "version": "v002",
                "dependencies": ["v001"],
                "up": lambda self, ctx: (_run_create_posts(sqlite_backend, ctx),
                                          exec("raise RuntimeError('batch txn fail')")),
                "down": lambda self, ctx: _run_drop_posts(sqlite_backend, ctx),
            }),
        ))
        try:
            store = JSONFileMigrationRecordStore(tmp_path / "batch_txn.json")
            runner = BatchMigrationRunner("batch_txn.migrations")
            with pytest.raises(RuntimeError, match="batch txn fail"):
                runner.migrate_up(
                    sqlite_backend, record_store=store, single_transaction=True,
                )
            # DB tables should not exist (outer txn rolled back)
            cursor = sqlite_backend.connection.cursor()
            cursor.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='users'"
            )
            assert cursor.fetchone()[0] == 0
        finally:
            unregister_temp_module("batch_txn.migrations")


def _run_create_users(backend, ctx):
    from rhosocial.activerecord.backend.expression.statements.ddl_table import (
        CreateTableExpression,
        ColumnDefinition,
        ColumnConstraint,
        ColumnConstraintType,
    )
    from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
        SQLiteIntegerType,
        SQLiteTextType,
    )
    expr = CreateTableExpression(
        backend.dialect,
        table="users",
        columns=[
            ColumnDefinition(
                "id",
                SQLiteIntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)],
            ),
            ColumnDefinition("name", SQLiteTextType()),
        ],
    )
    backend.execute(*expr.to_sql())


def _run_drop_users(backend, ctx):
    from rhosocial.activerecord.backend.expression.statements.ddl_table import DropTableExpression
    expr = DropTableExpression(backend.dialect, table="users", if_exists=True)
    backend.execute(*expr.to_sql())


def _run_create_posts(backend, ctx):
    from rhosocial.activerecord.backend.expression.statements.ddl_table import (
        CreateTableExpression,
        ColumnDefinition,
        ColumnConstraint,
        ColumnConstraintType,
    )
    from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
        SQLiteIntegerType,
        SQLiteTextType,
    )
    expr = CreateTableExpression(
        backend.dialect,
        table="posts",
        columns=[
            ColumnDefinition(
                "id",
                SQLiteIntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)],
            ),
            ColumnDefinition("title", SQLiteTextType()),
        ],
    )
    backend.execute(*expr.to_sql())


def _run_drop_posts(backend, ctx):
    from rhosocial.activerecord.backend.expression.statements.ddl_table import DropTableExpression
    expr = DropTableExpression(backend.dialect, table="posts", if_exists=True)
    backend.execute(*expr.to_sql())