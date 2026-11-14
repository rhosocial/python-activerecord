# tests/rhosocial/activerecord_test/feature/backend/migration/test_migration_functions.py
"""Function migrations: decorator, resolver, and the migrate CLI command."""

try:  # Python 3.8 has no typing.Annotated
    from typing import Annotated, Optional
except ImportError:  # pragma: no cover - only on 3.8
    from typing import Optional

    from typing_extensions import Annotated

import pytest

from rhosocial.activerecord.backend.expression.types import IntegerType, VarCharType
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.migration import (
    NamedMigration,
    resolve_migration_function,
)
from rhosocial.activerecord.backend.migration.core import MigrationDirection
from rhosocial.activerecord.backend.migration.functions import (
    MigrationFunctionError,
    migration,
)
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.base import (
    IdentityAttribute,
    UseColumnAttributes,
    UseSqlType,
)
from rhosocial.activerecord.cli import main
from rhosocial.activerecord.model import ActiveRecord


class MigUser(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "mig_function_users"

    id: Annotated[
        Optional[int],
        UseSqlType(IntegerType()),
        UseColumnAttributes(IdentityAttribute()),
    ] = None
    name: Annotated[str, UseSqlType(VarCharType(length=64))]

    def plain(self, ctx):  # pragma: no cover - only used for rejection
        pass

    @classmethod
    @migration("v001_create_users")
    def create_users(cls, ctx):
        if ctx.direction == MigrationDirection.UP:
            ctx.apply(cls.create_table_statement(backend=ctx.backend))
        else:
            ctx.apply(cls.drop_table_statement(backend=ctx.backend, if_exists=True))


class MigPost(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "mig_function_posts"

    id: Annotated[
        Optional[int],
        UseSqlType(IntegerType()),
        UseColumnAttributes(IdentityAttribute()),
    ] = None
    title: Annotated[str, UseSqlType(VarCharType(length=128))]

    @classmethod
    @migration("v002_create_posts", dependencies=("v001_create_users",))
    def create_posts(cls, ctx):
        if ctx.direction == MigrationDirection.UP:
            ctx.apply(cls.create_table_statement(backend=ctx.backend))
        else:
            ctx.apply(cls.drop_table_statement(backend=ctx.backend, if_exists=True))

    @staticmethod
    @migration("v003_add_post_index")
    def add_post_index(ctx):
        ctx.apply(MigPost.create_index_statements(backend=ctx.backend))

    @classmethod
    @migration("v004_bad_dependency", dependencies=("v001_create_users",))
    def bad_dependency(cls, ctx):
        pass


@migration("v999_not_a_method")
def plain_migration(ctx):  # pragma: no cover - only used for rejection
    pass


def undecorated(ctx):  # pragma: no cover - only used for rejection
    pass


class NotAModel:
    @classmethod
    @migration("v998_wrong_owner")
    def bad(cls, ctx):  # pragma: no cover - only used for rejection
        pass


class LegacyMigration(NamedMigration):
    version = "v997_legacy"

    def up(self, ctx):
        pass

    def down(self, ctx):
        pass


@migration("v005_module_function")
def module_function(ctx):
    ctx.apply(
        MigUser.create_table_statement(backend=ctx.backend),
    )


class MigDirectUser(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "mig_function_direct"

    id: Annotated[
        Optional[int],
        UseSqlType(IntegerType()),
        UseColumnAttributes(IdentityAttribute()),
    ] = None
    name: Annotated[str, UseSqlType(VarCharType(length=64))]

    @classmethod
    @migration("v006_direct_create")
    def create(cls, ctx):
        if ctx.direction == MigrationDirection.UP:
            cls.create_table(backend=ctx.backend)
        else:
            cls.drop_table(backend=ctx.backend, if_exists=True)


def _configure(database):
    for model in (MigUser, MigPost, MigDirectUser):
        model.configure(SQLiteConnectionConfig(database=str(database)), SQLiteBackend)


def _fqn(name: str) -> str:
    return f"{__name__}:{name}"


def _tables(database):
    backend = SQLiteBackend(SQLiteConnectionConfig(database=str(database)))
    backend.connect()
    try:
        rows = (
            backend.execute(
                "SELECT type, name FROM sqlite_master",
                options=ExecutionOptions(stmt_type=StatementType.SELECT, process_result_set=True),
            ).data
            or []
        )
        return {row["name"] for row in rows if row["type"] == "table"}
    finally:
        backend.disconnect()


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "migrate.sqlite"
    _configure(path)
    yield path


def test_decorator_attaches_metadata_before_classmethod():
    function = MigUser.create_users.__func__
    info = function.__migration__
    assert info.version == "v001_create_users"
    assert info.dependencies == ()


def test_migration_decorator_accepts_outer_classmethod():
    class Outer(ActiveRecord):
        @classmethod
        def table_name(cls):
            return "outer_migrations"

        @migration("v100_outer")
        @classmethod
        def run(cls, ctx):
            pass

    assert Outer.run.__func__.__migration__.version == "v100_outer"


def test_resolver_accepts_classmethod_and_staticmethod():
    class_ref = resolve_migration_function(_fqn("MigUser.create_users"))
    assert class_ref.owner is MigUser
    assert class_ref.info.version == "v001_create_users"

    static_ref = resolve_migration_function(_fqn("MigPost.add_post_index"))
    assert static_ref.function.__name__ == "add_post_index"


def test_resolver_accepts_module_level_function():
    ref = resolve_migration_function(_fqn("module_function"))
    assert ref.owner is None
    assert ref.info.version == "v005_module_function"


def test_resolver_rejects_undecorated_function():
    with pytest.raises(MigrationFunctionError, match="not decorated"):
        resolve_migration_function(_fqn("undecorated"))


def test_resolver_rejects_plain_class_method():
    with pytest.raises(MigrationFunctionError, match="classmethod"):
        resolve_migration_function(_fqn("MigUser.plain"))


def test_resolver_rejects_non_model_owner():
    with pytest.raises(MigrationFunctionError, match="not an ActiveRecord model"):
        resolve_migration_function(_fqn("NotAModel.bad"))


def test_resolver_rejects_named_migration_class():
    with pytest.raises(MigrationFunctionError, match="NamedMigration"):
        resolve_migration_function(_fqn("LegacyMigration"))


def test_cli_migrate_up_records_versions(database, tmp_path, capsys):
    store = tmp_path / "records.json"
    code = main(
        [
            "migrate",
            _fqn("MigUser.create_users"),
            _fqn("MigPost.create_posts"),
            "--model",
            _fqn("MigUser"),
            "--record-store",
            str(store),
        ]
    )
    assert code == 0
    assert "mig_function_users" in _tables(database)
    assert "mig_function_posts" in _tables(database)

    import json

    records = json.loads(store.read_text())
    assert [record["version"] for record in records] == [
        "v001_create_users",
        "v002_create_posts",
    ]
    assert all(record["success"] for record in records)


def test_cli_migrate_down_reverses_order_and_rolls_back(database, tmp_path):
    store = tmp_path / "records.json"
    assert (
        main(
            [
                "migrate",
                _fqn("MigUser.create_users"),
                _fqn("MigPost.create_posts"),
                "--model",
                _fqn("MigUser"),
                "--record-store",
                str(store),
            ]
        )
        == 0
    )

    assert (
        main(
            [
                "migrate",
                _fqn("MigUser.create_users"),
                _fqn("MigPost.create_posts"),
                "--direction",
                "down",
                "--model",
                _fqn("MigUser"),
                "--record-store",
                str(store),
            ]
        )
        == 0
    )

    names = _tables(database)
    assert "mig_function_users" not in names
    assert "mig_function_posts" not in names

    import json

    records = json.loads(store.read_text())
    down_versions = [record["version"] for record in records if record["direction"] == "down"]
    assert down_versions == ["v002_create_posts", "v001_create_users"]


def test_cli_migrate_dry_run_writes_nothing(database, tmp_path, capsys):
    store = tmp_path / "records.json"
    code = main(
        [
            "migrate",
            _fqn("MigUser.create_users"),
            "--model",
            _fqn("MigUser"),
            "--record-store",
            str(store),
            "--dry-run",
        ]
    )
    assert code == 0
    captured = capsys.readouterr().out
    assert "CREATE TABLE" in captured
    assert "would run" in captured
    assert "mig_function_users" not in _tables(database)
    assert not store.exists()


def test_cli_migrate_requires_dependency_first(database):
    code = main(
        [
            "migrate",
            _fqn("MigPost.create_posts"),
            "--model",
            _fqn("MigPost"),
        ]
    )
    assert code != 0


def test_cli_migrate_rejects_duplicate_version(database):
    code = main(
        [
            "migrate",
            _fqn("MigUser.create_users"),
            _fqn("MigUser.create_users"),
            "--model",
            _fqn("MigUser"),
        ]
    )
    assert code != 0


def test_cli_migrate_module_function_requires_model(database, tmp_path):
    code = main(
        [
            "migrate",
            _fqn("module_function"),
            "--model",
            _fqn("MigUser"),
        ]
    )
    assert code == 0
    assert "mig_function_users" in _tables(database)


def test_cli_migrate_module_function_without_model_fails(database):
    code = main(["migrate", _fqn("module_function")])
    assert code != 0


def test_cli_migrate_dry_run_blocks_model_mixin_writes(database):
    code = main(
        [
            "migrate",
            _fqn("MigDirectUser.create"),
            "--model",
            _fqn("MigDirectUser"),
            "--dry-run",
        ]
    )
    assert code == 0
    assert "mig_function_direct" not in _tables(database)
