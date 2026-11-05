# tests/rhosocial/activerecord_test/feature/backend/sqlite4/test_cli_introspect_data_families.py
"""The CLI must be able to ask the three data families it declares.

A family the dialect can answer that the command cannot ask is half a feature,
and the way that shows up in practice is a type the user has to guess at: the
probe says yes, the API works, and ``--help`` never mentions it. These tests
drive the shipped ``main()`` so the type list, the capability gate and the
branches are all checked as one surface rather than as three assumptions.

The ``source`` column is asserted rather than assumed. SQLite's figures are
exact counts bought with a scan, not readings off a statistics catalogue, and a
consumer comparing them with a PostgreSQL estimate has to be able to tell the
two apart without knowing which engine it asked -- so the column has to survive
serialisation, not merely exist on the dataclass.
"""

import contextlib
import io
import json
import sqlite3

import pytest

from rhosocial.activerecord.backend.impl.sqlite.__main__ import main


@pytest.fixture()
def db_file(tmp_path):
    db = tmp_path / "families.sqlite"
    raw = sqlite3.connect(str(db))
    raw.executescript(
        "CREATE TABLE buyers (id INTEGER PRIMARY KEY, label TEXT NOT NULL);"
        "INSERT INTO buyers (id, label) VALUES (1, 'one'), (2, 'two'), (3, 'three');"
        "CREATE TABLE orders ("
        "  id INTEGER PRIMARY KEY,"
        "  buyer_id INTEGER,"
        "  status TEXT NOT NULL,"
        "  note TEXT"
        ");"
        "INSERT INTO orders (id, buyer_id, status, note) VALUES (1, 1, 'new', NULL);"
        "INSERT INTO orders (id, buyer_id, status, note) VALUES (2, 1, 'paid', 'x');"
        "INSERT INTO orders (id, buyer_id, status, note) VALUES (3, 2, 'new', NULL);"
        "INSERT INTO orders (id, buyer_id, status, note) VALUES (4, 9, 'new', NULL);"
    )
    raw.commit()
    raw.close()
    return db


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    code = 0
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            main(argv)
    except SystemExit as e:
        code = e.code or 0
    return code, out.getvalue().strip(), err.getvalue().strip()


class _Args:
    """The attributes the flag rules look at, and nothing else."""

    def __init__(self, type_, **flags):
        self.type = type_
        for name, value in flags.items():
            setattr(self, name, value)


# ---------------------------------------------------------------------------
# The type surface
# ---------------------------------------------------------------------------


class TestTheTypeSurface:
    def test_the_three_families_are_offered(self):
        from rhosocial.activerecord.backend.impl.sqlite.cli import introspect as cli

        for name in ("column-profiles", "value-samples", "join-coverage"):
            assert name in cli.INTROSPECT_TYPES, name

    def test_each_names_a_switch_the_dialect_declares(self):
        """A type cannot be offered without saying which switch answers it."""
        from rhosocial.activerecord.backend.impl.sqlite.cli import introspect as cli
        from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

        dialect = SQLiteDialect(version=(3, 45, 0))
        for name, switch in cli._TYPE_CAPABILITIES.items():
            assert hasattr(dialect, switch), (name, switch)
            assert getattr(dialect, switch)() is True, (name, switch)

    def test_the_three_take_the_table_name(self):
        from rhosocial.activerecord.backend.impl.sqlite.cli import introspect as cli

        for name in ("column-profiles", "value-samples", "join-coverage"):
            assert cli._NAME_RULE[name] == "required", name

    def test_a_flag_a_type_has_no_question_for_is_refused(self, capsys):
        from rhosocial.activerecord.backend.impl.sqlite.cli import introspect as cli

        with pytest.raises(SystemExit) as excinfo:
            cli._refuse_unused_arguments(_Args("column-profiles", column="status"))

        assert excinfo.value.code == 2
        assert "does not take --column" in capsys.readouterr().err

    def test_the_families_that_do_take_the_column_keep_it(self):
        from rhosocial.activerecord.backend.impl.sqlite.cli import introspect as cli

        cli._refuse_unused_arguments(_Args("value-samples", column="status"))
        cli._refuse_unused_arguments(
            _Args("join-coverage", column="buyer_id", right_table="buyers", right_column="id")
        )

    def test_the_right_hand_flags_belong_to_one_family(self, capsys):
        from rhosocial.activerecord.backend.impl.sqlite.cli import introspect as cli

        with pytest.raises(SystemExit) as excinfo:
            cli._refuse_unused_arguments(_Args("value-samples", column="status", right_table="t"))

        assert excinfo.value.code == 2
        assert "does not take --right-table" in capsys.readouterr().err

    def test_an_absent_flag_is_not_given(self):
        """The offline tests stand a stub namespace in for the parser."""
        from rhosocial.activerecord.backend.impl.sqlite.cli import introspect as cli

        cli._refuse_unused_arguments(_Args("tables"))


# ---------------------------------------------------------------------------
# The families, end to end
# ---------------------------------------------------------------------------


def test_column_profiles_reports_the_figures_and_their_provenance(db_file):
    code, out, _ = run(
        ["introspect", "column-profiles", "orders", "--db-file", str(db_file), "-o", "json"]
    )

    assert code == 0
    payload = json.loads(out)
    by_column = {row["column_name"]: row for row in payload}

    assert by_column["id"]["distinct_count"] == 4
    assert by_column["id"]["null_fraction"] == 0.0
    assert by_column["status"]["distinct_count"] == 2
    assert by_column["note"]["null_fraction"] == 0.75
    # The provenance has to survive serialisation, not merely exist.
    for row in payload:
        assert row["source"] == "aggregate"


def test_value_samples_reports_the_most_frequent_values(db_file):
    code, out, _ = run(
        [
            "introspect",
            "value-samples",
            "orders",
            "--column",
            "status",
            "--db-file",
            str(db_file),
            "-o",
            "json",
        ]
    )

    assert code == 0
    payload = json.loads(out)
    assert [(row["value"], row["count"]) for row in payload] == [("new", 3), ("paid", 1)]


def test_join_coverage_reports_both_directions(db_file):
    code, out, _ = run(
        [
            "introspect",
            "join-coverage",
            "orders",
            "--column",
            "buyer_id",
            "--right-table",
            "buyers",
            "--right-column",
            "id",
            "--db-file",
            str(db_file),
            "-o",
            "json",
        ]
    )

    assert code == 0
    payload = json.loads(out)
    assert len(payload) == 1
    # Three distinct buyer_ids (1, 2, 9) and three buyers; the overlap is 1
    # and 2, so both directions read two of three.
    assert payload[0]["left_coverage"] == pytest.approx(2 / 3)
    assert payload[0]["right_coverage"] == pytest.approx(2 / 3)


def test_the_families_render_as_a_table_too(db_file):
    """The table output is the default, and it has to reach the provider."""
    for argv_tail in (
        ("column-profiles", "orders"),
        ("value-samples", "orders", "--column", "status"),
        (
            "join-coverage",
            "orders",
            "--column",
            "buyer_id",
            "--right-table",
            "buyers",
            "--right-column",
            "id",
        ),
    ):
        code, out, _ = run(["introspect", *argv_tail, "--db-file", str(db_file)])
        assert code == 0, argv_tail
        assert out, argv_tail


# ---------------------------------------------------------------------------
# Incomplete invocations are refused, not silently narrowed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "argv_tail, message",
    [
        (("column-profiles",), "Table name is required"),
        (("value-samples", "orders"), "--column is required"),
        (("join-coverage", "orders"), "--column is required"),
        (("join-coverage", "orders", "--column", "buyer_id"), "--right-table and --right-column"),
    ],
)
def test_an_incomplete_question_exits_one(db_file, argv_tail, message):
    code, _, err = run(["introspect", *argv_tail, "--db-file", str(db_file)])

    assert code == 1, (argv_tail, err)
    assert message in err, err


def test_the_cli_refuses_a_family_the_dialect_cannot_answer(db_file, monkeypatch):
    """The advertised list and the capability gate have to agree.

    The gate reads the switch through ``create_backend``'s adapted dialect, so
    the refusal has to survive a run that starts from a real file.
    """
    from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

    monkeypatch.setattr(SQLiteDialect, "supports_join_coverage", lambda self: False)
    code, _, err = run(
        [
            "introspect",
            "join-coverage",
            "orders",
            "--column",
            "buyer_id",
            "--right-table",
            "buyers",
            "--right-column",
            "id",
            "--db-file",
            str(db_file),
        ]
    )

    assert code == 2
    assert "not supported by this server" in err
