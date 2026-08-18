# tests/rhosocial/activerecord_test/feature/backend/cli/test_named_series_deep.py
"""Deep integration test for the named series (progressive design goal).

The named series is progressive:
    named-connection (access) -> named-expression (single query)
    -> named-procedure (orchestration) -> named-procedure-graph (DAG)
    -> named-migration (schema).

This test drives the real CLI (in-process main(argv)) against a real
SQLite db file and verifies each layer reaches its documented design goal:

  - named-connection: describe/list/show connection configs
  - named-migration:  up/down create/drop tables with dependency + dry-run
  - named-expression: describe/list/dry-run/execute with params + async
  - named-procedure:  describe/list/dry-run/execute orchestration + async
  - named-procedure-graph: describe/waves/validate/dry-run/execute DAG + params
"""

import io
import json
import os
import sqlite3
from contextlib import redirect_stderr, redirect_stdout

import pytest

from rhosocial.activerecord.backend.impl.sqlite.__main__ import main

NS = "rhosocial.activerecord_test.feature.backend.cli.named_series"


def run_cli(argv):
    """Run the CLI in-process; return (stdout, stderr, exc)."""
    out, err = io.StringIO(), io.StringIO()
    exc = None
    with redirect_stdout(out), redirect_stderr(err):
        try:
            main(argv)
        except SystemExit as e:
            exc = e
    return out.getvalue(), err.getvalue(), exc


def db_has_table(db_path, table):
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        return row[0] > 0
    finally:
        conn.close()


@pytest.fixture(scope="module")
def db_path(tmp_path_factory):
    """A fresh db file; migrations are NOT pre-applied here."""
    return str(tmp_path_factory.mktemp("named_series") / "test.db")


# ---------------------------------------------------------------------------
# Phase 0: named-connection
# ---------------------------------------------------------------------------


class TestNamedConnection:
    def test_list_connections(self):
        out, _, exc = run_cli(
            ["named-connection", "--list", f"{NS}.connections"]
        )
        assert exc is None, out
        assert "mem_db" in out
        assert "file_db" in out

    def test_show_connection(self):
        out, _, exc = run_cli(
            ["named-connection", "--show", f"{NS}.connections.file_db"]
        )
        assert exc is None, out
        assert "file_db" in out
        assert "database" in out

    def test_describe_connection_with_override(self):
        out, _, exc = run_cli(
            [
                "named-connection", "--describe", f"{NS}.connections.file_db_override",
                "--param", "database=/tmp/named_series_overridden.db",
            ]
        )
        assert exc is None, out
        assert "/tmp/named_series_overridden.db" in out


# ---------------------------------------------------------------------------
# Phase 1: named-migration
# ---------------------------------------------------------------------------


class TestNamedMigration:
    def test_dry_run_up_creates_no_table(self, db_path):
        out, err, exc = run_cli(
            [
                "named-migration", f"{NS}.migrations.V001CreateUsers",
                "--db-file", db_path, "--direction", "up", "--dry-run",
            ]
        )
        assert exc is None, err
        assert not db_has_table(db_path, "users")

    def test_apply_up_creates_users(self, db_path):
        out, err, exc = run_cli(
            [
                "named-migration", f"{NS}.migrations.V001CreateUsers",
                "--db-file", db_path, "--direction", "up",
                "--record-store", db_path + ".record.json",
            ]
        )
        assert exc is None, err
        assert db_has_table(db_path, "users")

    def test_dependency_ordered_apply(self, db_path):
        # V002 depends on v001 which is already applied; a fresh record store
        # for posts must still succeed because dependency is satisfied.
        out, err, exc = run_cli(
            [
                "named-migration", f"{NS}.migrations.V002CreatePosts",
                "--db-file", db_path, "--direction", "up",
                "--record-store", db_path + ".record.json",
            ]
        )
        assert exc is None, err
        assert db_has_table(db_path, "posts")

    def test_dry_run_down(self, db_path):
        out, err, exc = run_cli(
            [
                "named-migration", f"{NS}.migrations.V002CreatePosts",
                "--db-file", db_path, "--direction", "down", "--dry-run",
            ]
        )
        assert exc is None, err
        assert db_has_table(db_path, "posts")  # unchanged by dry-run

    def test_apply_down(self, db_path):
        out, err, exc = run_cli(
            [
                "named-migration", f"{NS}.migrations.V002CreatePosts",
                "--db-file", db_path, "--direction", "down",
                "--record-store", db_path + ".record.json",
            ]
        )
        assert exc is None, err
        assert not db_has_table(db_path, "posts")

    def test_async_up(self, tmp_path):
        db = str(tmp_path / "async_up.db")
        record = db + ".record.json"
        out, err, exc = run_cli(
            [
                "named-migration", f"{NS}.migrations.AsyncV001CreateUsers",
                "--db-file", db, "--direction", "up", "--async",
                "--record-store", record,
            ]
        )
        assert exc is None, err
        assert db_has_table(db, "users")
        # clean up so the db reflects a known state
        out, err, exc = run_cli(
            [
                "named-migration", f"{NS}.migrations.AsyncV001CreateUsers",
                "--db-file", db, "--direction", "down", "--async",
                "--record-store", record,
            ]
        )
        assert exc is None, err
        assert not db_has_table(db, "users")


# ---------------------------------------------------------------------------
# Phase 2: named-expression
# ---------------------------------------------------------------------------


@pytest.fixture(scope="class")
def seeded_db(db_path, tmp_path_factory):
    """db with users+posts tables, seeded via the CLI (named-expression)."""
    db = str(tmp_path_factory.mktemp("named_series_seed") / "seed.db")
    # migrate up
    for mig, rec in [
        ("V001CreateUsers", "rs_users"),
        ("V002CreatePosts", "rs_posts"),
    ]:
        out, err, exc = run_cli(
            [
                "named-migration", f"{NS}.migrations.{mig}",
                "--db-file", db, "--direction", "up",
                "--record-store", db + ".record.json",
            ]
        )
        assert exc is None, err
    return db


class TestNamedExpression:
    def test_list(self):
        out, _, exc = run_cli(["named-expression", "--list", f"{NS}.queries"])
        assert exc is None, out
        assert "list_users" in out
        assert "count_posts" in out

    def test_describe(self):
        out, _, exc = run_cli(
            ["named-expression", "--describe", f"{NS}.queries.user_by_id"]
        )
        assert exc is None, out
        assert "user_id" in out

    def test_dry_run(self):
        out, _, exc = run_cli(
            [
                "named-expression", f"{NS}.queries.user_by_id",
                "--param", "user_id=5", "--dry-run",
            ]
        )
        assert exc is None, out
        assert "DRY RUN" in out or "dry" in out.lower()

    def test_execute_empty(self, seeded_db):
        out, _, exc = run_cli(
            [
                "named-expression", f"{NS}.queries.list_users",
                "--db-file", seeded_db, "-o", "json",
            ]
        )
        assert exc is None, out
        data = json.loads(out)
        assert isinstance(data, list)

    def test_execute_insert_and_select(self, seeded_db):
        # insert a user
        out, _, exc = run_cli(
            [
                "named-expression", f"{NS}.queries.insert_user",
                "--db-file", seeded_db,
                "--param", "name=alice", "--param", "email=alice@ex.com",
                "--force",
            ]
        )
        assert exc is None, out
        # read it back
        out, _, exc = run_cli(
            [
                "named-expression", f"{NS}.queries.list_users",
                "--db-file", seeded_db, "-o", "json",
            ]
        )
        assert exc is None, out
        data = json.loads(out)
        names = {row.get("name") for row in data}
        assert "alice" in names

    def test_execute_parameterized(self, seeded_db):
        out, _, exc = run_cli(
            [
                "named-expression", f"{NS}.queries.user_by_id",
                "--db-file", seeded_db, "--param", "user_id=1",
            ]
        )
        assert exc is None, out

    def test_execute_async(self, seeded_db):
        out, _, exc = run_cli(
            [
                "named-expression", f"{NS}.queries.list_users",
                "--db-file", seeded_db, "--async", "-o", "json",
            ]
        )
        assert exc is None, out


# ---------------------------------------------------------------------------
# Phase 3: named-procedure
# ---------------------------------------------------------------------------


class TestNamedProcedure:
    def test_describe(self):
        out, _, exc = run_cli(
            ["named-procedure", "--describe", f"{NS}.procedures.SeedUsersProcedure"]
        )
        assert exc is None, out
        assert "user_count" in out

    def test_list(self):
        out, _, exc = run_cli(
            ["named-procedure", "--list", f"{NS}.procedures"]
        )
        assert exc is None, out
        assert "SeedUsersProcedure" in out

    def test_dry_run(self):
        out, _, exc = run_cli(
            [
                "named-procedure", f"{NS}.procedures.SeedUsersProcedure",
                "--db-file", "/tmp/unused.db", "--dry-run",
            ]
        )
        assert exc is None, out

    def test_execute_sync(self, seeded_db):
        out, err, exc = run_cli(
            [
                "named-procedure", f"{NS}.procedures.SeedUsersProcedure",
                "--db-file", seeded_db, "--param", "user_count=3",
            ]
        )
        assert exc is None, err
        # verify via a named-expression select
        out, _, exc = run_cli(
            ["named-expression", f"{NS}.queries.list_users", "--db-file", seeded_db, "-o", "json"]
        )
        assert exc is None, out
        data = json.loads(out)
        assert len(data) >= 3

    def test_execute_parallel_async(self, seeded_db):
        out, err, exc = run_cli(
            [
                "named-procedure", f"{NS}.procedures.AsyncSeedUsersProcedure",
                "--db-file", seeded_db,
                "--param", "user_count=2",
                "--async",
            ]
        )
        assert exc is None, err


# ---------------------------------------------------------------------------
# Phase 4: named-procedure-graph
# ---------------------------------------------------------------------------


class TestNamedProcedureGraph:
    def test_list(self):
        out, _, exc = run_cli(
            ["named-procedure-graph", "--list", f"{NS}.graphs"]
        )
        assert exc is None, out
        assert "seed_and_report_graph" in out
        assert "conditional_graph" in out

    def test_waves(self):
        out, _, exc = run_cli(
            ["named-procedure-graph", "--waves", f"{NS}.graphs.seed_and_report_graph"]
        )
        assert exc is None, out
        assert "wave" in out.lower() or "Wave" in out or "step" in out.lower()

    def test_validate(self):
        out, _, exc = run_cli(
            ["named-procedure-graph", "--validate", f"{NS}.graphs.seed_and_report_graph"]
        )
        assert exc is None, out

    def test_dry_run(self):
        out, _, exc = run_cli(
            [
                "named-procedure-graph", f"{NS}.graphs.seed_and_report_graph",
                "--db-file", "/tmp/unused.db", "--dry-run",
                "--params", '{"user_name": "bob"}',
            ]
        )
        assert exc is None, out

    def test_execute(self, seeded_db):
        out, err, exc = run_cli(
            [
                "named-procedure-graph", f"{NS}.graphs.seed_and_report_graph",
                "--db-file", seeded_db,
                "--params", '{"user_name": "graphuser", "user_email": "gu@ex.com"}',
            ]
        )
        assert exc is None, err

    def test_execute_conditional(self, seeded_db):
        out, err, exc = run_cli(
            [
                "named-procedure-graph", f"{NS}.graphs.conditional_graph",
                "--db-file", seeded_db, "--params", '{"threshold": 1}',
            ]
        )
        assert exc is None, err

    def test_execute_async(self, seeded_db):
        out, err, exc = run_cli(
            [
                "named-procedure-graph", f"{NS}.graphs.seed_and_report_graph",
                "--db-file", seeded_db, "--async",
                "--params", '{"user_name": "asyncuser"}',
            ]
        )
        assert exc is None, err


# ---------------------------------------------------------------------------
# Phase 5: progression — the whole chain works end to end
# ---------------------------------------------------------------------------


class TestProgression:
    def test_full_chain(self, tmp_path):
        """migration -> expression -> procedure -> graph on one db."""
        db = str(tmp_path / "chain.db")

        # 1. migration up creates tables
        for mig, rec in [
            ("V001CreateUsers", "rs_users"),
            ("V002CreatePosts", "rs_posts"),
        ]:
            out, err, exc = run_cli(
                [
                    "named-migration", f"{NS}.migrations.{mig}",
                    "--db-file", db, "--direction", "up",
                    "--record-store", db + ".record.json",
                ]
            )
            assert exc is None, err
        assert db_has_table(db, "users") and db_has_table(db, "posts")

        # 2. named-expression seeds a user
        out, _, exc = run_cli(
            [
                "named-expression", f"{NS}.queries.insert_user",
                "--db-file", db,
                "--param", "name=carol", "--param", "email=carol@ex.com",
                "--force",
            ]
        )
        assert exc is None, out

        # 3. named-procedure seeds more users (orchestration over expressions)
        out, err, exc = run_cli(
            [
                "named-procedure", f"{NS}.procedures.SeedUsersProcedure",
                "--db-file", db, "--param", "user_count=2",
            ]
        )
        assert exc is None, err

        # 4. named-procedure-graph reports over the same db
        out, err, exc = run_cli(
            [
                "named-procedure-graph", f"{NS}.graphs.seed_and_report_graph",
                "--db-file", db, "--params", '{"user_name": "dave"}',
            ]
        )
        assert exc is None, err

        # 5. verify final state through named-expression
        out, _, exc = run_cli(
            ["named-expression", f"{NS}.queries.list_users", "--db-file", db, "-o", "json"]
        )
        assert exc is None, out
        data = json.loads(out)
        names = {row.get("name") for row in data}
        assert {"carol", "dave"} <= names

        # 6. clean up: migration down drops everything
        for mig, rec in [
            ("V002CreatePosts", "rs_posts"),
            ("V001CreateUsers", "rs_users"),
        ]:
            out, err, exc = run_cli(
                [
                    "named-migration", f"{NS}.migrations.{mig}",
                    "--db-file", db, "--direction", "down",
                    "--record-store", db + ".record.json",
                ]
            )
            assert exc is None, err
        assert not db_has_table(db, "users") and not db_has_table(db, "posts")
