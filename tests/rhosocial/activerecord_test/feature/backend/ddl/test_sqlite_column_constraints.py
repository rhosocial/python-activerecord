# tests/rhosocial/activerecord_test/feature/backend/ddl/test_sqlite_column_constraints.py
"""What SQLite's column-constraint grammar actually accepts.

Everything here was measured against a live SQLite rather than read off the
syntax diagrams, because the two disagree in both directions: the grammar shows
``AUTOINCREMENT`` on a table constraint that the parser rejects, and shows
``MATCH`` on a foreign key that is parsed and then ignored.
"""
import sqlite3

import pytest
from rhosocial.activerecord.backend.expression.statements import (
    ColumnForeignKeyConstraint,
    ColumnNotNullConstraint,
    ColumnPrimaryKeyConstraint,
    ColumnUniqueConstraint,
    TablePrimaryKeyConstraint,
    TableUniqueConstraint,
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.expression.types import IntegerType, TextType
from rhosocial.activerecord.backend.expression.statements import (
    ColumnConstraint,
    ColumnDefinition,
    TableConstraint,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError



def probed(**answers):
    namespace = {
        name: (lambda self, answer=answer: answer)
        for name, answer in answers.items()
    }
    return type("ProbedDialect", (SQLiteDialect,), namespace)


def accepts(ddl: str) -> bool:
    """Whether this SQLite build accepts the statement."""
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute("CREATE TABLE p (id INTEGER PRIMARY KEY)")
        conn.execute(ddl)
        return True
    except sqlite3.Error:
        return False
    finally:
        conn.close()


class TestColumnConstraintNames:
    """``CONSTRAINT name`` is a column constraint in SQLite, not only a table one."""

    def test_sqlite_build_accepts_a_named_column_constraint(self):
        assert accepts(
            "CREATE TABLE t (id INTEGER PRIMARY KEY, "
            "e TEXT CONSTRAINT uq_e UNIQUE)"
        )

    def test_the_renderer_spells_the_name(self):
        """The column path renders ``CONSTRAINT <name>`` like the table path.

        The renderer used to read ``name`` on the table path only, which
        silently unnamed every named column constraint. The SQL-92 grammar
        opens both constraint productions with ``[CONSTRAINT <name>]``, so
        both render it, gated by ``supports_constraint_naming`` (default
        True; SQLite measured accepting it on 3.50.4).
        """
        dialect = SQLiteDialect()
        constraint = ColumnConstraint(dialect, branch=ColumnUniqueConstraint(dialect), name="uq_e")

        assert constraint.name == "uq_e"
        assert constraint.to_sql()[0] == ' CONSTRAINT "uq_e" UNIQUE'

    def test_the_table_path_already_renders_names(self):
        dialect = SQLiteDialect()
        constraint = TableConstraint(dialect, branch=TableUniqueConstraint(dialect, ["e"]), name="uq_e")

        assert constraint.to_sql()[0].startswith('CONSTRAINT "uq_e"')


class TestDeferralIsEnforced:
    """``DEFERRABLE INITIALLY DEFERRED`` defers to COMMIT; it is not a no-op."""

    @staticmethod
    def _probe(ddl: str):
        conn = sqlite3.connect(":memory:")
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("CREATE TABLE p (id INTEGER PRIMARY KEY)")
            conn.execute(ddl)
            conn.execute("BEGIN")
            try:
                conn.execute("INSERT INTO t (pid) VALUES (999)")
                inserted = True
            except sqlite3.IntegrityError:
                inserted = False
            try:
                conn.execute("COMMIT")
                committed = True
            except sqlite3.IntegrityError:
                committed = False
            return inserted, committed
        finally:
            conn.close()

    def test_deferred_rejects_at_commit_not_at_insert(self):
        inserted, committed = self._probe(
            "CREATE TABLE t (id INTEGER PRIMARY KEY, "
            "pid INTEGER REFERENCES p(id) DEFERRABLE INITIALLY DEFERRED)"
        )

        assert inserted is True
        assert committed is False

    def test_not_deferrable_rejects_at_insert(self):
        inserted, _ = self._probe(
            "CREATE TABLE t (id INTEGER PRIMARY KEY, "
            "pid INTEGER REFERENCES p(id) NOT DEFERRABLE)"
        )

        assert inserted is False

    def test_sqlite_declares_the_capability(self):
        assert SQLiteDialect().supports_deferrable_constraint() is True

    def test_a_deferred_column_foreign_key_renders(self):
        dialect = SQLiteDialect()
        constraint = ColumnConstraint(dialect, branch=ColumnForeignKeyConstraint(dialect, (Table(dialect, "p"), ["id"])), deferrable=True, initially_deferred=True)

        sql = constraint.to_sql()[0]

        assert "DEFERRABLE" in sql and "INITIALLY DEFERRED" in sql
        assert accepts(f"CREATE TABLE t ({sql.strip().join(['id INTEGER ', ', pid INTEGER '])})")


class TestMatchIsParsedAndIgnored:
    """SQLite parses ``MATCH`` and never enforces it, so it is refused."""

    def test_the_syntax_is_accepted(self):
        assert accepts(
            "CREATE TABLE t (id INTEGER PRIMARY KEY, "
            "pid INTEGER REFERENCES p(id) MATCH FULL)"
        )

    def test_the_dialect_refuses_it_by_name(self):
        dialect = SQLiteDialect()
        constraint = ColumnConstraint(dialect, branch=ColumnForeignKeyConstraint(dialect, (Table(dialect, "p"), ["id"]), match_type="FULL"))

        with pytest.raises(UnsupportedFeatureError, match="MATCH"):
            constraint.to_sql()


class TestAutoIncrementHasTwoForms:
    """AUTOINCREMENT belongs to the primary key, not to a column definition.

    It has two spellings and both are valid::

        id INTEGER PRIMARY KEY AUTOINCREMENT            -- column level
        PRIMARY KEY (id AUTOINCREMENT)                   -- table level

    The keyword sits *inside* the parentheses in the second form. Reading the
    syntax diagram as ``PRIMARY KEY (id) AUTOINCREMENT`` -- outside -- yields a
    syntax error, which is what an earlier reading of that diagram concluded.
    """

    def test_column_level_form_is_accepted(self):
        assert accepts("CREATE TABLE t (id INTEGER PRIMARY KEY AUTOINCREMENT)")

    def test_table_level_form_is_accepted(self):
        assert accepts("CREATE TABLE t (id INTEGER, PRIMARY KEY (id AUTOINCREMENT))")

    def test_the_two_forms_are_not_interchangeable(self):
        """Outside the parentheses it is a syntax error, not a spelling variant."""
        assert not accepts(
            "CREATE TABLE t (id INTEGER, PRIMARY KEY (id) AUTOINCREMENT)"
        )

    def test_the_table_level_form_autoincrements(self):
        conn = sqlite3.connect(":memory:")
        try:
            conn.execute(
                "CREATE TABLE t (id INTEGER, name TEXT, PRIMARY KEY (id AUTOINCREMENT))"
            )
            conn.execute("INSERT INTO t (name) VALUES ('a')")
            conn.execute("INSERT INTO t (name) VALUES ('b')")
            conn.execute("DELETE FROM t WHERE id = 2")
            conn.execute("INSERT INTO t (name) VALUES ('c')")

            ids = [r[0] for r in conn.execute("SELECT id FROM t ORDER BY id")]
            # The last insert must not reuse the deleted ROWID.
            assert ids == [1, 3]
            assert conn.execute(
                "SELECT seq FROM sqlite_sequence WHERE name = 't'"
            ).fetchone() == (3,)
        finally:
            conn.close()

    @pytest.mark.parametrize(
        "ddl",
        (
            "CREATE TABLE t (id TEXT, PRIMARY KEY (id AUTOINCREMENT))",
            "CREATE TABLE t (id INTEGER, j INTEGER, PRIMARY KEY (id, j AUTOINCREMENT))",
        ),
    )
    def test_both_levels_require_a_single_integer_column(self, ddl):
        """Same rule at both levels: a lone INTEGER primary key."""
        assert not accepts(ddl)

    def test_direction_cannot_combine_with_autoincrement(self):
        assert not accepts(
            "CREATE TABLE t (id INTEGER, PRIMARY KEY (id AUTOINCREMENT DESC))"
        )

    def test_direction_alone_is_fine_at_both_levels(self):
        assert accepts("CREATE TABLE t (id INTEGER PRIMARY KEY DESC)")
        assert accepts("CREATE TABLE t (id INTEGER, PRIMARY KEY (id DESC))")

    def test_the_table_level_form_cannot_be_requested(self):
        """The gap: ``TableConstraint`` has no field for it.

        SQLite accepts the form and we cannot express it. The assertion records
        the missing field rather than pretending the form does not exist.
        """
        constraint = TableConstraint(SQLiteDialect(), branch=TablePrimaryKeyConstraint(SQLiteDialect(), ["id"]))

        assert not hasattr(constraint, "is_auto_increment")
        assert "AUTOINCREMENT" not in constraint.to_sql()[0]


class TestConflictClauseIsMissingFromTheExpressionLayer:
    """SQLite accepts a conflict clause on three column constraints.

    There is no expression for it anywhere in the tree, so this cannot be
    written at all. Recorded here so the gap has a failing test rather than a
    note in a plan.
    """

    @pytest.mark.parametrize(
        "ddl",
        (
            "CREATE TABLE t (id INTEGER PRIMARY KEY, e TEXT UNIQUE ON CONFLICT IGNORE)",
            "CREATE TABLE t (id INTEGER PRIMARY KEY, e TEXT NOT NULL ON CONFLICT FAIL)",
        ),
    )
    def test_sqlite_build_accepts_them(self, ddl):
        assert accepts(ddl)

    @pytest.mark.parametrize(
        "branch_cls", (ColumnUniqueConstraint, ColumnNotNullConstraint)
    )
    def test_but_the_expression_cannot_carry_one(self, branch_cls):
        dialect = SQLiteDialect()
        constraint = ColumnConstraint(dialect, branch=branch_cls(dialect))

        assert not hasattr(constraint, "on_conflict")
        assert "ON CONFLICT" not in constraint.to_sql()[0]


class TestPrimaryKeyDirection:
    """SQLite lets the primary key carry a sort direction; nothing models it."""

    def test_sqlite_build_accepts_desc(self):
        assert accepts("CREATE TABLE t (id INTEGER PRIMARY KEY DESC)")

    def test_but_the_expression_has_no_field_for_it(self):
        constraint = ColumnConstraint(SQLiteDialect(), branch=ColumnPrimaryKeyConstraint(SQLiteDialect()))

        assert not hasattr(constraint, "direction")
        assert "DESC" not in constraint.to_sql()[0]


class TestColumnDefinitionPathMatchesTheGrammar:
    """Sanity: what we render for the common case is what SQLite accepts."""

    def test_integer_primary_key(self):
        dialect = SQLiteDialect()
        column = ColumnDefinition(
            dialect,
            "id",
            IntegerType(dialect),
            constraints=[ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect))],
        )

        assert accepts(f"CREATE TABLE t ({column.to_sql()[0]})")

    def test_not_null_and_unique(self):
        dialect = SQLiteDialect()
        column = ColumnDefinition(
            dialect,
            "e",
            TextType(dialect),
            constraints=[
                ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
                ColumnConstraint(dialect, branch=ColumnUniqueConstraint(dialect)),
            ],
        )

        assert accepts(f"CREATE TABLE t ({column.to_sql()[0]})")
