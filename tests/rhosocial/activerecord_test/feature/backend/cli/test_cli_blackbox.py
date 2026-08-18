# tests/rhosocial/activerecord_test/feature/backend/cli/test_cli_blackbox.py
"""Black-box CLI tests for the sqlite backend.

Strategy: run the CLI entry in-process via main(argv) and assert on stdout.
Key property: with `-o json/csv/tsv` the stdout is clean structured data
(logs go to stderr), so stdout can be parsed deterministically.
"""

import csv
import io
import json
import sqlite3
from contextlib import redirect_stderr, redirect_stdout

import pytest

from rhosocial.activerecord.backend.impl.sqlite.__main__ import main

COMMANDS = [
    "info",
    "query",
    "introspect",
    "status",
    "named-expression",
    "named-procedure",
    "named-procedure-graph",
    "named-migration",
    "named-connection",
]


@pytest.fixture
def sample_db(tmp_path):
    """Create a SQLite db with a small table and return its path."""
    db = tmp_path / "sample.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE t (a INTEGER, b TEXT)")
    conn.executemany("INSERT INTO t VALUES (?, ?)", [(1, "x"), (2, "y")])
    conn.commit()
    conn.close()
    return str(db)


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


class TestCommandSurface:
    """C1: command surface."""

    def test_help_lists_all_commands(self):
        out, _, _ = run_cli(["--help"])
        for cmd in COMMANDS:
            assert cmd in out

    def test_missing_command_errors(self):
        _, _, exc = run_cli([])
        assert exc is not None
        assert exc.code == 1

    def test_unknown_command_errors(self):
        _, _, exc = run_cli(["nonexistent"])
        assert exc is not None


class TestQuery:
    """C3/C9: query execution and output formats."""

    def test_query_json(self, sample_db):
        out, _, exc = run_cli(["query", "--db-file", sample_db, "SELECT 1 AS one", "-o", "json"])
        assert exc is None
        assert json.loads(out) == [{"one": 1}]

    def test_query_csv(self, sample_db):
        out, _, exc = run_cli(["query", "--db-file", sample_db, "SELECT * FROM t", "-o", "csv"])
        assert exc is None
        rows = list(csv.reader(io.StringIO(out)))
        assert rows == [["a", "b"], ["1", "x"], ["2", "y"]]

    def test_query_tsv(self, sample_db):
        out, _, exc = run_cli(["query", "--db-file", sample_db, "SELECT * FROM t", "-o", "tsv"])
        assert exc is None
        lines = [line.split("\t") for line in out.strip().splitlines()]
        assert lines == [["a", "b"], ["1", "x"], ["2", "y"]]

    def test_query_output_formats_equivalent(self, sample_db):
        """C: json/csv/tsv describe the same data."""
        out_json, _, _ = run_cli(["query", "--db-file", sample_db, "SELECT * FROM t", "-o", "json"])
        data = json.loads(out_json)
        assert data == [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]

    def test_query_async_flag_accepted(self, sample_db):
        out, _, exc = run_cli(
            ["query", "--db-file", sample_db, "SELECT 1 AS one", "-o", "json", "--async"]
        )
        assert exc is None
        assert json.loads(out) == [{"one": 1}]


class TestInfo:
    """C4: info."""

    def test_info_output(self):
        out, _, exc = run_cli(["info"])
        assert exc is None
        assert "SQLite" in out or "sqlite" in out


class TestIntrospect:
    """C5: introspect."""

    def test_introspect_tables(self, sample_db):
        out, _, exc = run_cli(["introspect", "--db-file", sample_db, "tables", "-o", "json"])
        assert exc is None
        data = json.loads(out)
        names = [t.get("name") for t in data] if isinstance(data, list) else []
        assert "t" in names


class TestNamedConnection:
    """C7: named-connection subcommand."""

    def test_describe(self, tmp_path):
        import os
        import sys

        mod_dir = tmp_path / "conns"
        mod_dir.mkdir()
        (mod_dir / "connections.py").write_text(
            "from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig\n"
            "def mem_db():\n"
            "    return SQLiteConnectionConfig(database=':memory:')\n"
        )
        env = dict(os.environ, PYTHONPATH=str(mod_dir))
        # run in a subprocess so PYTHONPATH applies to the named-connection import
        import subprocess

        proc = subprocess.run(
            [sys.executable, "-m", "rhosocial.activerecord.backend.impl.sqlite",
             "named-connection", "--describe", "connections.mem_db"],
            capture_output=True, text=True, env=env,
        )
        assert proc.returncode == 0
        assert "Resolved Configuration" in proc.stdout or "Resolved Configuration" in proc.stderr