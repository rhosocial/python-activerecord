# tests/rhosocial/activerecord_test/feature/backend/sqlite4/test_cli_introspect_e2e.py
"""The CLI's introspection must work end to end, through the dialect.

Two things are pinned here, and the second is the reason this file exists.

First: every introspect subcommand produces real output for a real database.
A CLI that exits zero and prints nothing would pass a smoke test and be useless.

Second, and more importantly: the CLI *reaches the dialect formatters*. An
earlier trace concluded it did not -- that trace built its own parser and never
went through ``cli.get_handler``, so it observed nothing and reported nothing as
a finding. A trace that observes nothing is indistinguishable from one that
observed the wrong thing. This test goes through the shipped ``main()``, so the
claim is checked rather than assumed.
"""

import contextlib
import io
import sqlite3

import pytest

from rhosocial.activerecord.backend.impl.sqlite import cli as sqlite_cli
from rhosocial.activerecord.backend.impl.sqlite.__main__ import main


@pytest.fixture(scope="module")
def db_file(tmp_path_factory):
    db = tmp_path_factory.mktemp("cli_introspect") / "probe.sqlite"
    raw = sqlite3.connect(str(db))
    raw.executescript(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT);"
        "CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id),"
        " total NUMERIC);"
        "CREATE VIEW active_users AS SELECT id, name FROM users;"
        "CREATE INDEX idx_users_email ON users(email);"
        "CREATE UNIQUE INDEX idx_users_name ON users(name);"
        "CREATE TRIGGER trg_users AFTER INSERT ON users BEGIN SELECT 1; END;"
    )
    raw.commit()
    raw.close()
    return db


def run(argv):
    """Run main() and return (exit code, stripped stdout)."""
    out, err = io.StringIO(), io.StringIO()
    code = 0
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            main(argv)
    except SystemExit as e:
        code = e.code or 0
    return code, out.getvalue().strip()


# ---------------------------------------------------------------------------
# Every advertised subcommand produces real output
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "argv_tail",
    [
        ("tables",),
        ("views",),
        ("triggers",),
        ("database",),
    ],
)
def test_introspect_subcommand_returns_data(db_file, argv_tail):
    code, out = run(["introspect", *argv_tail, "--db-file", str(db_file)])
    assert code == 0, out
    assert out, "exited 0 with no output -- the CLI printed nothing"
    assert out not in ("[]", "None"), out


@pytest.mark.parametrize(
    "argv_tail",
    [
        ("columns", "users"),
        ("indexes", "users"),
        ("foreign-keys", "orders"),
    ],
)
def test_introspect_named_subcommands(db_file, argv_tail):
    """Subcommands that take a target name."""
    code, out = run(["introspect", *argv_tail, "--db-file", str(db_file)])
    assert code == 0, (argv_tail, out)
    assert out, argv_tail


def test_introspect_tables_include_system_branch(db_file):
    """``--include-system`` takes the PRAGMA branch, not the sqlite_master tree.

    Both branches have to work; this is the one the tree rewrite does not touch.
    """
    code, out = run(["introspect", "tables", "--include-system", "--db-file", str(db_file)])
    assert code == 0, out
    assert out, "no output from the include-system branch"


def test_introspect_accepts_json_output(db_file):
    code, out = run(["introspect", "views", "-o", "json", "--db-file", str(db_file)])
    assert code == 0, out
    assert out, "no output from the json formatter"


# ---------------------------------------------------------------------------
# The CLI reaches the dialect -- the claim the earlier trace got wrong
# ---------------------------------------------------------------------------


def test_cli_dispatches_through_get_handler(monkeypatch):
    """``main()`` resolves the handler via ``get_handler``.

    The wrong trace built its own parser and called ``args.func``, which does
    not exist; it therefore ran no handler at all. Pinning the dispatch shape
    makes that specific mistake impossible to repeat.
    """
    seen = []
    original = sqlite_cli.get_handler

    def spy(command):
        handler = original(command)
        seen.append(command)
        return handler

    monkeypatch.setattr(sqlite_cli, "get_handler", spy)
    run(["introspect", "views", "--db-file", ":memory:"])
    assert "introspect" in seen, "get_handler was never consulted"


def test_cli_views_reach_the_dialect_formatter(db_file, monkeypatch):
    """``introspect views`` must call the SQLite view-list formatter.

    This is the assertion whose absence let the wrong conclusion stand: the
    trace saw no ``format_*`` calls and reported the CLI as bypassing the
    dialect, when in fact it had not run a handler at all.
    """
    from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

    calls = []
    original = SQLiteDialect.format_view_list_query_statement

    def spy(self, expr):
        calls.append(expr)
        return original(self, expr)

    monkeypatch.setattr(SQLiteDialect, "format_view_list_query_statement", spy)
    code, out = run(["introspect", "views", "--db-file", str(db_file)])
    assert code == 0, out
    assert calls, "format_view_list_query_statement was never called by the CLI"


# ---------------------------------------------------------------------------
# Each invocation is a fresh look, so a schema change is seen immediately
# ---------------------------------------------------------------------------


def test_a_schema_change_between_runs_is_visible(db_file):
    """Two CLI runs in one process must not share an answer.

    This is the property that lets the CLI skip reasoning about the
    introspection cache. A command is one process in normal use, but a
    script -- or this test -- can drive ``main()`` more than once, and if
    two runs reached the same cached metadata a table created between
    them would be invisible. Nothing in the CLI invalidates anything, so
    the guarantee has to come from each run building its own manager.

    The DDL is committed by a separate connection, the way any external
    tool would do it: the CLI must observe a change it did not make.

    Asked for JSON rather than the default table on purpose. The rendered
    table wraps every cell to five characters, so a name like
    ``added_later`` never appears as one contiguous string -- asserting on
    that text would test the renderer's wrapping, not the answer.
    """
    code, before = run(["introspect", "tables", "--db-file", str(db_file), "-o", "json"])
    assert code == 0, before
    assert "added_later" not in before

    raw = sqlite3.connect(str(db_file))
    with raw:
        raw.execute("CREATE TABLE added_later (id INTEGER PRIMARY KEY, note TEXT)")
    raw.close()

    code, after = run(["introspect", "tables", "--db-file", str(db_file), "-o", "json"])
    assert code == 0, after
    assert "added_later" in after, (
        "a table created between two runs in the same process was not "
        "reported -- the second run answered from the first run's metadata"
    )
