# tests/rhosocial/activerecord_test/feature/cli/test_cli_commands.py
"""Black-box tests for the model DML/DQL command-line interface.

The CLI is run in-process through ``main(argv)``. Machine formats are parsed
from stdout, while errors and logs are asserted on stderr. Each test gets a
fresh temporary module and SQLite database, so the model import cache and the
data never leak between cases.
"""

import csv
import io
import json
import sqlite3
import sys
import textwrap
import uuid
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace

import pytest

from rhosocial.activerecord.cli import main
from rhosocial.activerecord.cli import output as cli_output
from rhosocial.activerecord.cli.args import OUTPUT_FORMATS
from logging_isolation import preserve_logging

SQLITE_BACKEND = "rhosocial.activerecord.backend.impl.sqlite.backend:SQLiteBackend"
ASYNC_SQLITE_BACKEND = (
    "rhosocial.activerecord.backend.impl.sqlite.backend:AsyncSQLiteBackend"
)
SQLITE_CONFIG = (
    "rhosocial.activerecord.backend.impl.sqlite.config:SQLiteConnectionConfig"
)


def connection_args(database, backend=SQLITE_BACKEND):
    """Build the explicit backend, config class, and database arguments."""
    return [
        "--backend-class",
        backend,
        "--config-class",
        SQLITE_CONFIG,
        "--config",
        f"database={database}",
    ]


def run_cli(argv):
    """Run the CLI in-process and return (exit_code, stdout, stderr)."""
    with preserve_logging():
        out, err = io.StringIO(), io.StringIO()
        code = 0
        with redirect_stdout(out), redirect_stderr(err):
            try:
                code = main(argv)
            except SystemExit as exc:
                code = exc.code if exc.code is not None else 0
        return code, out.getvalue(), err.getvalue()


def write_module(path, module_name, body):
    (path / f"{module_name}.py").write_text(textwrap.dedent(body), encoding="utf-8")


def create_users_table(database, rows=(("1", "Alice", "alice@example.com", "30"),)):
    conn = sqlite3.connect(str(database))
    conn.execute(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, "
        "email TEXT, age INTEGER DEFAULT 0)"
    )
    conn.executemany(
        "INSERT INTO users (id, name, email, age) VALUES (?, ?, ?, ?)", rows
    )
    conn.commit()
    conn.close()


def create_order_items_table(database):
    conn = sqlite3.connect(str(database))
    conn.execute(
        "CREATE TABLE order_items (order_id INTEGER, product_id INTEGER, "
        "note TEXT DEFAULT '', PRIMARY KEY (order_id, product_id))"
    )
    conn.executemany(
        "INSERT INTO order_items (order_id, product_id, note) VALUES (?, ?, ?)",
        [(1, 101, "first"), (1, 102, "second"), (2, 101, "third")],
    )
    conn.commit()
    conn.close()


MODEL_BODY = """
from typing import Optional

from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord


class User(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "users"
    id: int
    name: str
    email: Optional[str] = None
    age: int = 0


class AsyncUser(AsyncActiveRecord):
    @classmethod
    def table_name(cls):
        return "users"
    id: int
    name: str
    email: Optional[str] = None
    age: int = 0


class OrderItem(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "order_items"
    @classmethod
    def primary_key(cls):
        return ("order_id", "product_id")
    order_id: int
    product_id: int
    note: str = ""


class NotAModel:
    pass
"""


@pytest.fixture
def cli_env(tmp_path):
    module_name = "cli_models_" + uuid.uuid4().hex
    database = tmp_path / "app.db"
    rows = (
        (1, "Alice", "alice@example.com", 30),
        (2, "Bob", "bob@example.com", 25),
        (3, "Alice", "alice2@example.com", 40),
    )
    create_users_table(database, rows=rows)
    create_order_items_table(database)
    write_module(tmp_path, module_name, MODEL_BODY)
    base = ["--path", str(tmp_path), *connection_args(database)]
    async_base = [
        "--path",
        str(tmp_path),
        *connection_args(database, backend=ASYNC_SQLITE_BACKEND),
    ]
    return SimpleNamespace(
        tmp_path=tmp_path,
        database=database,
        module_name=module_name,
        user_model=f"{module_name}:User",
        async_model=f"{module_name}:AsyncUser",
        order_model=f"{module_name}:OrderItem",
        base=base,
        async_base=async_base,
    )


@pytest.fixture
def configured_env(tmp_path):
    """A module that calls configure() at import time."""
    module_name = "cli_configured_" + uuid.uuid4().hex
    database = tmp_path / "configured.db"
    create_users_table(database, rows=((7, "Configured", "cfg@example.com", 41),))
    body = f"""
from typing import Optional

from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig


class User(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "users"
    id: int
    name: str
    email: Optional[str] = None
    age: int = 0


User.configure(SQLiteConnectionConfig(database=r"{database}"), SQLiteBackend)
"""
    write_module(tmp_path, module_name, body)
    return SimpleNamespace(
        tmp_path=tmp_path,
        database=database,
        model=f"{module_name}:User",
    )


@pytest.fixture
def named_connection_env(tmp_path):
    module_name = "cli_connections_" + uuid.uuid4().hex
    database = tmp_path / "named.db"
    create_users_table(database, rows=((8, "Named", "named@example.com", 33),))
    body = f"""
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig


def prod_db():
    return SQLiteConnectionConfig(database=r"{database}")
"""
    write_module(tmp_path, module_name, body)
    return SimpleNamespace(
        tmp_path=tmp_path,
        database=database,
        connection=f"{module_name}:prod_db",
    )


class TestCommandSurface:
    def test_console_script_is_declared(self):
        pyproject = Path(__file__).resolve().parents[5] / "pyproject.toml"
        text = pyproject.read_text(encoding="utf-8")
        assert (
            'rhosocial-activerecord = "rhosocial.activerecord.cli:main"' in text
        )

    def test_cli_extra_declares_rich(self):
        pyproject = Path(__file__).resolve().parents[5] / "pyproject.toml"
        text = pyproject.read_text(encoding="utf-8")
        assert 'cli = ["rich>=13.0"]' in text

    def test_output_formats_are_pinned(self):
        assert OUTPUT_FORMATS == ("table", "json", "jsonl", "csv", "tsv", "value")

    def test_root_help_lists_command_groups(self):
        code, out, _ = run_cli(["--help"])
        assert code == 0
        assert "dml" in out

    def test_dml_help_lists_all_commands(self):
        code, out, _ = run_cli(["dml", "--help"])
        assert code == 0
        for command in ("create", "update", "delete", "bulk"):
            assert command in out

    def test_dql_help_lists_all_commands(self):
        code, out, _ = run_cli(["dql", "--help"])
        assert code == 0
        for command in ("get", "list", "count", "exists", "aggregate", "run"):
            assert command in out

    def test_missing_command_returns_one(self):
        code, out, err = run_cli([])
        assert code == 1
        assert out == ""
        assert "dml" in err

    def test_missing_subcommand_returns_one(self):
        code, _, err = run_cli(["dml"])
        assert code == 1
        assert "DML" in err

    def test_unknown_command_is_usage_error(self):
        code, out, err = run_cli(["nonexistent"])
        assert code == 2
        assert "invalid choice" in err


class TestModelLoading:
    def test_loads_model(self, cli_env):
        code, out, _ = run_cli(
            ["dql", "list", *cli_env.base, "--model", cli_env.user_model, "-o", "json"]
        )
        assert code == 0
        assert json.loads(out)[0]["name"] == "Alice"

    def test_missing_module_returns_one(self, cli_env):
        code, out, err = run_cli(
            [
                "dql",
                "list",
                "--path",
                str(cli_env.tmp_path),
                "--model",
                f"no_such_module_{uuid.uuid4().hex}:User",
                *connection_args(cli_env.database),
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert out == ""
        assert "not found" in err

    def test_missing_class_returns_one(self, cli_env):
        code, _, err = run_cli(
            ["dql", "list", *cli_env.base, "--model", f"{cli_env.module_name}:Missing", "-o", "json"]
        )
        assert code == 1
        assert "has no class" in err

    def test_non_model_class_returns_one(self, cli_env):
        code, out, err = run_cli(
            ["dql", "list", *cli_env.base, "--model", f"{cli_env.module_name}:NotAModel", "-o", "json"]
        )
        assert code == 1
        assert out == ""
        assert "neither an IActiveRecord nor an IAsyncActiveRecord" in err

    def test_model_without_colon_returns_one(self, cli_env):
        code, _, err = run_cli(
            ["dql", "list", *cli_env.base, "--model", f"{cli_env.module_name}.User", "-o", "json"]
        )
        assert code == 1
        assert "module:Class" in err

    def test_missing_backend_and_config_returns_one(self, cli_env):
        code, _, err = run_cli(
            ["dql", "list", "--path", str(cli_env.tmp_path), "--model", cli_env.user_model, "-o", "json"]
        )
        assert code == 1
        assert "no backend class" in err

    def test_path_option_makes_import_work(self, cli_env):
        code, out, _ = run_cli(
            ["dql", "get", *cli_env.base, "--model", cli_env.user_model, "--pk", "1", "-o", "json"]
        )
        assert code == 0
        assert json.loads(out)["id"] == 1

    def test_cli_connection_overrides_module_configuration(self, configured_env, tmp_path):
        override_db = tmp_path / "override.db"
        create_users_table(override_db, rows=((99, "Override", "o@example.com", 50),))
        code, out, _ = run_cli(
            [
                "dql",
                "list",
                "--path",
                str(configured_env.tmp_path),
                "--model",
                configured_env.model,
                *connection_args(override_db),
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert [row["id"] for row in json.loads(out)] == [99]

    def test_module_configuration_is_used_without_flags(self, configured_env):
        code, out, _ = run_cli(
            ["dql", "list", "--path", str(configured_env.tmp_path), "--model", configured_env.model, "-o", "json"]
        )
        assert code == 0
        assert json.loads(out)[0]["id"] == 7


class TestConnectionResolution:
    def test_explicit_classes_connect(self, cli_env):
        code, out, _ = run_cli(
            ["dql", "list", *cli_env.base, "--model", cli_env.user_model, "-o", "json"]
        )
        assert code == 0
        assert len(json.loads(out)) == 3

    def test_dotted_class_references(self, cli_env):
        code, out, _ = run_cli(
            [
                "dql",
                "list",
                "--path",
                str(cli_env.tmp_path),
                "--model",
                cli_env.user_model,
                "--backend-class",
                "rhosocial.activerecord.backend.impl.sqlite.backend.SQLiteBackend",
                "--config-class",
                "rhosocial.activerecord.backend.impl.sqlite.config.SQLiteConnectionConfig",
                "--config",
                f"database={cli_env.database}",
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert len(json.loads(out)) == 3

    def test_invalid_config_pair_returns_one(self, cli_env):
        code, out, err = run_cli(
            [
                "dql",
                "list",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--config",
                "not-a-pair",
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert out == ""
        assert "expected KEY=VALUE" in err

    def test_named_connection_with_explicit_backend(self, cli_env, named_connection_env):
        code, out, _ = run_cli(
            [
                "dql",
                "list",
                "--path",
                str(named_connection_env.tmp_path),
                "--model",
                cli_env.user_model,
                "--backend-class",
                SQLITE_BACKEND,
                "--connection",
                named_connection_env.connection,
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert [row["id"] for row in json.loads(out)] == [8]

    def test_named_connection_uses_module_backend(self, configured_env, named_connection_env):
        code, out, _ = run_cli(
            [
                "dql",
                "list",
                "--path",
                str(configured_env.tmp_path),
                "--model",
                configured_env.model,
                "--connection",
                named_connection_env.connection,
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert [row["id"] for row in json.loads(out)] == [8]

    def test_named_connection_requires_backend_class(self, cli_env, named_connection_env):
        code, _, err = run_cli(
            [
                "dql",
                "list",
                "--path",
                str(named_connection_env.tmp_path),
                "--model",
                cli_env.user_model,
                "--connection",
                named_connection_env.connection,
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert "no backend class" in err

    def test_named_connection_conflicts_with_config_class(
        self, configured_env, named_connection_env
    ):
        code, _, err = run_cli(
            [
                "dql",
                "list",
                "--path",
                str(named_connection_env.tmp_path),
                "--model",
                configured_env.model,
                "--connection",
                named_connection_env.connection,
                "--config-class",
                SQLITE_CONFIG,
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert "not both" in err

    def test_missing_backend_module_returns_four(self, cli_env):
        code, out, err = run_cli(
            [
                "dql",
                "list",
                "--path",
                str(cli_env.tmp_path),
                "--model",
                cli_env.user_model,
                "--backend-class",
                f"no_such_backend_{uuid.uuid4().hex}:Backend",
                "-o",
                "json",
            ]
        )
        assert code == 4
        assert out == ""
        assert "Cannot import the backend class" in err

    def test_non_backend_class_returns_one(self, cli_env):
        code, out, err = run_cli(
            [
                "dql",
                "list",
                "--path",
                str(cli_env.tmp_path),
                "--model",
                cli_env.user_model,
                "--backend-class",
                "collections:OrderedDict",
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert out == ""
        assert "not a synchronous backend" in err

    def test_non_config_class_returns_one(self, cli_env):
        code, out, err = run_cli(
            [
                "dql",
                "list",
                "--path",
                str(cli_env.tmp_path),
                "--model",
                cli_env.user_model,
                "--backend-class",
                SQLITE_BACKEND,
                "--config-class",
                "collections:OrderedDict",
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert out == ""
        assert "not a ConnectionConfig subclass" in err

    def test_backend_without_config_returns_one(self, cli_env):
        code, _, err = run_cli(
            [
                "dql",
                "list",
                "--path",
                str(cli_env.tmp_path),
                "--model",
                cli_env.user_model,
                "--backend-class",
                SQLITE_BACKEND,
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert "--config-class" in err

    def test_config_sets_config_field(self, cli_env):
        code, out, _ = run_cli(
            [
                "dql",
                "list",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--config",
                "timeout=7",
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert len(json.loads(out)) == 3

    def test_unknown_config_key_goes_to_options(self, cli_env):
        code, out, _ = run_cli(
            [
                "dql",
                "list",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--config",
                "custom_flag=on",
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert len(json.loads(out)) == 3

    def test_classvar_is_not_a_config_field(self, cli_env):
        # DEFAULT_PRAGMAS is a ClassVar on SQLiteConnectionConfig. It must not be
        # forwarded to the constructor as a keyword argument.
        code, out, _ = run_cli(
            [
                "dql",
                "list",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--config",
                "DEFAULT_PRAGMAS=ignored",
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert len(json.loads(out)) == 3


class TestDmlDql:
    def test_get_by_pk(self, cli_env):
        code, out, _ = run_cli(
            ["dql", "get", *cli_env.base, "--model", cli_env.user_model, "--pk", "1", "-o", "json"]
        )
        assert code == 0
        assert json.loads(out)["name"] == "Alice"

    def test_get_missing_returns_three(self, cli_env):
        code, out, _ = run_cli(
            ["dql", "get", *cli_env.base, "--model", cli_env.user_model, "--pk", "999", "-o", "json"]
        )
        assert code == 3
        assert out == ""

    def test_create(self, cli_env):
        code, out, _ = run_cli(
            [
                "dml",
                "create",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--data",
                '{"id": 4, "name": "Carol", "age": 22}',
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert json.loads(out)["id"] == 4

    def test_create_invalid_json_returns_one(self, cli_env):
        code, out, err = run_cli(
            ["dml", "create", *cli_env.base, "--model", cli_env.user_model, "--data", "{", "-o", "json"]
        )
        assert code == 1
        assert out == ""
        assert "not valid JSON" in err

    def test_create_non_object_returns_one(self, cli_env):
        code, _, err = run_cli(
            ["dml", "create", *cli_env.base, "--model", cli_env.user_model, "--data", "[1, 2]", "-o", "json"]
        )
        assert code == 1
        assert "JSON object" in err

    def test_update_only_given_fields(self, cli_env):
        code, out, _ = run_cli(
            [
                "dml",
                "update",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--pk",
                "2",
                "--data",
                '{"name": "Bobby"}',
                "-o",
                "json",
            ]
        )
        assert code == 0
        data = json.loads(out)
        assert data["name"] == "Bobby"
        assert data["age"] == 25

    def test_update_rejects_primary_key(self, cli_env):
        code, out, err = run_cli(
            [
                "dml",
                "update",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--pk",
                "2",
                "--data",
                '{"id": 3, "name": "Bobby"}',
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert out == ""
        assert "primary key" in err

    def test_update_without_pk_returns_one(self, cli_env):
        code, _, err = run_cli(
            [
                "dml",
                "update",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--data",
                '{"name": "Bobby"}',
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert "--pk" in err

    def test_update_missing_record_returns_three(self, cli_env):
        code, out, _ = run_cli(
            [
                "dml",
                "update",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--pk",
                "999",
                "--data",
                '{"name": "Nobody"}',
                "-o",
                "json",
            ]
        )
        assert code == 3
        assert out == ""

    def test_delete(self, cli_env):
        code, out, _ = run_cli(
            ["dml", "delete", *cli_env.base, "--model", cli_env.user_model, "--pk", "2", "--yes", "-o", "json"]
        )
        assert code == 0
        assert json.loads(out) == {"action": "delete", "pk": 2, "affected": 1}

    def test_delete_missing_returns_three(self, cli_env):
        code, out, _ = run_cli(
            ["dml", "delete", *cli_env.base, "--model", cli_env.user_model, "--pk", "999", "-o", "json"]
        )
        assert code == 3
        assert out == ""

    def test_list_where_order_limit_offset(self, cli_env):
        code, out, _ = run_cli(
            [
                "dql",
                "list",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--where",
                "name=Alice",
                "--order-by",
                "id desc",
                "--limit",
                "1",
                "--offset",
                "1",
                "-o",
                "json",
            ]
        )
        assert code == 0
        rows = json.loads(out)
        assert len(rows) == 1
        assert rows[0]["id"] == 1

    def test_list_multiple_where_is_and(self, cli_env):
        code, out, _ = run_cli(
            [
                "dql",
                "list",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--where",
                "name=Alice",
                "--where",
                "age=40",
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert [row["id"] for row in json.loads(out)] == [3]

    def test_list_limit_zero_means_unlimited(self, cli_env):
        code, out, _ = run_cli(
            ["dql", "list", *cli_env.base, "--model", cli_env.user_model, "--limit", "0", "-o", "json"]
        )
        assert code == 0
        assert len(json.loads(out)) == 3

    def test_list_empty_returns_empty_array(self, cli_env):
        code, out, _ = run_cli(
            [
                "dql",
                "list",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--where",
                "name=Missing",
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert json.loads(out) == []

    def test_data_from_file(self, cli_env):
        data_file = cli_env.tmp_path / "user.json"
        data_file.write_text('{"id": 4, "name": "FromFile"}', encoding="utf-8")
        code, out, _ = run_cli(
            [
                "dml",
                "create",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--data",
                f"@{data_file}",
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert json.loads(out)["name"] == "FromFile"

    def test_data_from_stdin(self, cli_env, monkeypatch):
        monkeypatch.setattr(sys, "stdin", io.StringIO('{"id": 4, "name": "FromStdin"}'))
        code, out, _ = run_cli(
            [
                "dml",
                "create",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--data",
                "@-",
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert json.loads(out)["name"] == "FromStdin"

    def test_composite_pk_get(self, cli_env):
        code, out, _ = run_cli(
            [
                "dql",
                "get",
                *cli_env.base,
                "--model",
                cli_env.order_model,
                "--pk",
                '{"order_id": 1, "product_id": 101}',
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert json.loads(out)["note"] == "first"

    def test_composite_pk_update(self, cli_env):
        code, out, _ = run_cli(
            [
                "dml",
                "update",
                *cli_env.base,
                "--model",
                cli_env.order_model,
                "--pk",
                '{"order_id": 1, "product_id": 101}',
                "--data",
                '{"note": "changed"}',
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert json.loads(out)["note"] == "changed"

    def test_composite_pk_delete(self, cli_env):
        code, out, _ = run_cli(
            [
                "dml",
                "delete",
                *cli_env.base,
                "--model",
                cli_env.order_model,
                "--pk",
                '{"order_id": 1, "product_id": 101}',
                "--yes",
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert json.loads(out)["affected"] == 1

    def test_composite_pk_scalar_returns_one(self, cli_env):
        code, _, err = run_cli(
            ["dql", "get", *cli_env.base, "--model", cli_env.order_model, "--pk", "1", "-o", "json"]
        )
        assert code == 1
        assert "composite primary key" in err

    def test_composite_pk_wrong_keys_returns_one(self, cli_env):
        code, _, err = run_cli(
            [
                "dql",
                "get",
                *cli_env.base,
                "--model",
                cli_env.order_model,
                "--pk",
                '{"order_id": 1}',
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert "keys must be exactly" in err


class TestOutput:
    def test_json_list_is_array(self, cli_env):
        _, out, _ = run_cli(
            ["dql", "list", *cli_env.base, "--model", cli_env.user_model, "-o", "json"]
        )
        assert isinstance(json.loads(out), list)

    def test_json_get_is_object(self, cli_env):
        _, out, _ = run_cli(
            ["dql", "get", *cli_env.base, "--model", cli_env.user_model, "--pk", "1", "-o", "json"]
        )
        assert isinstance(json.loads(out), dict)

    def test_delete_summary_shape(self, cli_env):
        _, out, _ = run_cli(
            ["dml", "delete", *cli_env.base, "--model", cli_env.user_model, "--pk", "1", "--yes", "-o", "json"]
        )
        assert json.loads(out) == {"action": "delete", "pk": 1, "affected": 1}

    def test_csv_is_readable(self, cli_env):
        _, out, _ = run_cli(
            ["dql", "list", *cli_env.base, "--model", cli_env.user_model, "-o", "csv"]
        )
        rows = list(csv.reader(io.StringIO(out)))
        assert rows[0] == ["id", "name", "email", "age"]
        assert rows[1][0] == "1"

    def test_tsv_is_readable(self, cli_env):
        _, out, _ = run_cli(
            ["dql", "list", *cli_env.base, "--model", cli_env.user_model, "-o", "tsv"]
        )
        rows = list(csv.reader(io.StringIO(out), delimiter="\t"))
        assert rows[0] == ["id", "name", "email", "age"]
        assert rows[1][0] == "1"

    def test_fields_limits_json(self, cli_env):
        _, out, _ = run_cli(
            [
                "dql",
                "get",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--pk",
                "1",
                "--fields",
                "id,name",
                "-o",
                "json",
            ]
        )
        assert json.loads(out) == {"id": 1, "name": "Alice"}

    def test_fields_limits_csv_header(self, cli_env):
        _, out, _ = run_cli(
            [
                "dql",
                "list",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--fields",
                "id,name",
                "-o",
                "csv",
            ]
        )
        assert list(csv.reader(io.StringIO(out)))[0] == ["id", "name"]

    def test_unknown_field_returns_one(self, cli_env):
        code, _, err = run_cli(
            [
                "dql",
                "get",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--pk",
                "1",
                "--fields",
                "nope",
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert "Unknown field" in err

    def test_table_falls_back_to_json_without_rich(self, cli_env, monkeypatch):
        monkeypatch.setattr(cli_output, "RICH_AVAILABLE", False)
        _, out, _ = run_cli(
            ["dql", "get", *cli_env.base, "--model", cli_env.user_model, "--pk", "1", "-o", "table"]
        )
        assert json.loads(out)["id"] == 1

    def test_machine_output_stays_clean_with_debug_logs(self, cli_env):
        code, out, err = run_cli(
            [
                "dql",
                "get",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--pk",
                "1",
                "--log-level",
                "DEBUG",
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert json.loads(out)["id"] == 1
        assert "DEBUG" not in out


class TestAsync:
    def test_async_list(self, cli_env):
        code, out, _ = run_cli(
            ["dql", "list", *cli_env.async_base, "--model", cli_env.async_model, "-o", "json"]
        )
        assert code == 0
        assert len(json.loads(out)) == 3

    def test_async_get(self, cli_env):
        code, out, _ = run_cli(
            [
                "dql",
                "get",
                *cli_env.async_base,
                "--model",
                cli_env.async_model,
                "--pk",
                "1",
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert json.loads(out)["name"] == "Alice"

    def test_async_create_update_delete(self, cli_env):
        code, out, _ = run_cli(
            [
                "dml",
                "create",
                *cli_env.async_base,
                "--model",
                cli_env.async_model,
                "--data",
                '{"id": 4, "name": "AsyncCarol"}',
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert json.loads(out)["id"] == 4

        code, out, _ = run_cli(
            [
                "dml",
                "update",
                *cli_env.async_base,
                "--model",
                cli_env.async_model,
                "--pk",
                "4",
                "--data",
                '{"age": 23}',
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert json.loads(out)["age"] == 23

        code, out, _ = run_cli(
            [
                "dml",
                "delete",
                *cli_env.async_base,
                "--model",
                cli_env.async_model,
                "--pk",
                "4",
                "--yes",
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert json.loads(out)["affected"] == 1

    def test_async_not_found_returns_three(self, cli_env):
        code, out, _ = run_cli(
            [
                "dql",
                "get",
                *cli_env.async_base,
                "--model",
                cli_env.async_model,
                "--pk",
                "999",
                "-o",
                "json",
            ]
        )
        assert code == 3
        assert out == ""

    def test_async_model_rejects_sync_backend(self, cli_env):
        code, out, err = run_cli(
            ["dql", "list", *cli_env.base, "--model", cli_env.async_model, "-o", "json"]
        )
        assert code == 1
        assert out == ""
        assert "not an asynchronous backend" in err
