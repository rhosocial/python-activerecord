# tests/rhosocial/activerecord_test/feature/backend/sqlite4/test_introspect_surface.py
"""What the SQLite introspect command offers, and what it actually asks.

Three defects are pinned here, and none of them is visible to a test that only
asks "did the command print something":

* a generated column was missing from ``columns`` altogether, because the
  question was ``PRAGMA table_info``, which the engine does not answer for
  generated columns -- the parser downstream of it had been written for
  ``table_xinfo`` all along;
* a ``NAME`` the type could not use was accepted and ignored, so
  ``introspect tables users`` printed the whole catalogue and read as though it
  had been narrowed;
* the advertised types were a hand-written list that no test compared against
  the dialect switches, so a family could be offered with nothing behind it.
"""

import contextlib
import io
import json
import sqlite3

import pytest

from rhosocial.activerecord.backend.impl.sqlite.cli import introspect as introspect_cli
from rhosocial.activerecord.backend.impl.sqlite.__main__ import main
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


@pytest.fixture()
def db_file(tmp_path):
    db = tmp_path / "surface.sqlite"
    raw = sqlite3.connect(str(db))
    raw.executescript(
        "CREATE TABLE gen ("
        "  a INTEGER,"
        "  b INTEGER GENERATED ALWAYS AS (a * 2) VIRTUAL,"
        "  c INTEGER GENERATED ALWAYS AS (a + 1) STORED"
        ");"
        "CREATE VIEW v_gen AS SELECT a, b FROM gen;"
        "CREATE TRIGGER trg_gen AFTER INSERT ON gen BEGIN SELECT 1; END;"
    )
    raw.commit()
    raw.close()
    return db


def run(argv):
    """Run main() and return (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    code = 0
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            main(argv)
    except SystemExit as e:
        code = e.code or 0
    return code, out.getvalue().strip(), err.getvalue()


class _Args:
    """The two attributes the rules look at, and nothing else."""

    def __init__(self, type_, name=None):
        self.type = type_
        self.name = name


class TestTheTypeSurface:
    def test_the_type_list_is_the_capability_table(self):
        assert list(introspect_cli._TYPE_CAPABILITIES) == introspect_cli.INTROSPECT_TYPES

    def test_no_removed_aggregate_is_offered(self):
        assert "table" not in introspect_cli.INTROSPECT_TYPES

    def test_every_switch_exists_on_the_dialect(self):
        dialect = SQLiteDialect(version=(3, 45, 0))
        missing = [
            (name, switch)
            for name, switch in introspect_cli._TYPE_CAPABILITIES.items()
            if not hasattr(dialect, switch)
        ]
        assert missing == []

    def test_every_name_rule_covers_a_declared_type(self):
        assert set(introspect_cli._NAME_RULE) == set(introspect_cli.INTROSPECT_TYPES)

    def test_help_lists_every_type(self, capsys):
        code, out, _ = run(["introspect", "--help"])
        assert code == 0
        for name in introspect_cli.INTROSPECT_TYPES:
            assert name in out

    def test_every_type_has_a_branch(self):
        """A type with no branch prints nothing and exits 0 -- the worst shape."""
        import inspect

        source = inspect.getsource(introspect_cli.handle)
        for name in introspect_cli.INTROSPECT_TYPES:
            assert f'args.type == "{name}"' in source, name


class TestGeneratedColumns:
    """``columns`` asks the pragma that can see generated columns.

    The introspector's half is pinned in ``test_introspection_columns.py``;
    this is the same fact through the shipped command, because the command is
    where the omission was noticed.
    """

    def test_the_command_reports_them(self, db_file):
        code, out, _ = run(
            ["introspect", "columns", "gen", "--db-file", str(db_file), "-o", "json"]
        )

        assert code == 0
        payload = json.loads(out)
        assert [row["name"] for row in payload] == ["a", "b", "c"]
        assert [row["is_generated"] for row in payload] == [False, True, True]


class TestOneView:
    def test_a_named_view_is_described(self, db_file):
        code, out, _ = run(
            ["introspect", "views", "v_gen", "--db-file", str(db_file), "-o", "json"]
        )

        assert code == 0
        payload = json.loads(out)
        assert len(payload) == 1
        assert payload[0]["name"] == "v_gen"
        assert payload[0]["definition"]

    def test_without_a_name_the_family_is_listed(self, db_file):
        code, out, _ = run(["introspect", "views", "--db-file", str(db_file), "-o", "json"])

        assert code == 0
        assert [row["name"] for row in json.loads(out)] == ["v_gen"]

    def test_an_unknown_view_exits_one(self, db_file):
        code, _, err = run(["introspect", "views", "nope", "--db-file", str(db_file)])

        assert code == 1
        assert "not found" in err


class TestTheNameRule:
    @pytest.mark.parametrize("type_", ["tables", "database"])
    def test_a_name_the_type_answers_whole_is_refused(self, type_, capsys):
        with pytest.raises(SystemExit) as excinfo:
            introspect_cli._validate_name(_Args(type_, "users"))

        assert excinfo.value.code == 2
        assert "takes no name" in capsys.readouterr().err

    @pytest.mark.parametrize("type_", ["columns", "indexes", "foreign-keys"])
    def test_a_required_name_must_be_given(self, type_, capsys):
        """A missing NAME is an incomplete invocation, like a missing connection."""
        with pytest.raises(SystemExit) as excinfo:
            introspect_cli._validate_name(_Args(type_))

        assert excinfo.value.code == 1
        assert "required" in capsys.readouterr().err

    @pytest.mark.parametrize("type_", ["views", "triggers"])
    def test_an_optional_name_may_be_given_or_not(self, type_):
        introspect_cli._validate_name(_Args(type_))
        introspect_cli._validate_name(_Args(type_, "x"))

    def test_the_command_refuses_it_too(self, db_file):
        """The rule is applied by the command, not only by the helper."""
        code, _, err = run(["introspect", "tables", "gen", "--db-file", str(db_file)])

        assert code == 2
        assert "takes no name" in err


class TestTheCapabilityGate:
    def test_a_refused_family_exits_two(self, capsys):
        class _Dialect:
            @staticmethod
            def supports_trigger_introspection():
                return False

        class _Backend:
            dialect = _Dialect()

        with pytest.raises(SystemExit) as excinfo:
            introspect_cli._require_capability(_Args("triggers"), _Backend())

        assert excinfo.value.code == 2
        assert "not supported by this server" in capsys.readouterr().err

    def test_a_stub_without_a_dialect_is_not_refused(self):
        """The offline CLI tests stand a stub in for the backend."""
        introspect_cli._require_capability(_Args("triggers"), object())
