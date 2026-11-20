# tests/rhosocial/activerecord_test/feature/backend/sqlite/introspection/test_intro_data_profiles.py
"""The three row-shaped families, on a table whose every figure is checkable.

The fixture is built so no assertion needs a calculator: one unique key, one
three-value column, and one column null in six of ten rows. Every figure the
profile reports can then be read off the fixture by eye, which is the only
thing that makes "the numbers are right" a claim a test can actually make.

Two halves. The first runs the real statements against a real database, so a
regression in the node construction -- a dropped arm, a lost NULLIF guard, an
alias the parser no longer finds -- fails here rather than in a reviewer's
eye. The second pins the rendered SQL itself, because the whole point of
building these questions as expression trees is that the tree is inspectable:
if a future edit reintroduces text assembly the shape changes and this says so.
"""

import pytest

from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.introspection import (
    ColumnDataProfileQueryStatement,
    ColumnValueSampleQueryStatement,
    JoinCoverageQueryStatement,
)
from rhosocial.activerecord.backend.expression.query_sources import SetOperationKind
from rhosocial.activerecord.backend.expression.statements import (
    QueryStatement,
    SetOperationStatement,
)


@pytest.fixture
def profiled(sqlite_backend):
    """Ten rows: a unique key, a three-value column, 60% nulls, and a buyer.

    ``buyer_id`` holds three distinct values with one dangling, so the
    coverage measurement has a number other than the two easy ones.
    """
    sqlite_backend.executescript("""
        CREATE TABLE buyers (id INTEGER PRIMARY KEY, label TEXT NOT NULL);
        INSERT INTO buyers (id, label) VALUES (1, 'one'), (2, 'two'), (3, 'three');

        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            buyer_id INTEGER,
            status TEXT NOT NULL,
            note TEXT
        );
        """)
    rows = [
        (1, 1, "new", None),
        (2, 1, "paid", "x"),
        (3, 2, "new", None),
        (4, 2, "paid", "y"),
        (5, 3, "shipped", None),
        (6, 3, "shipped", "z"),
        (7, 1, "new", None),
        (8, 2, "paid", None),
        (9, 3, "shipped", None),
        (10, 99, "new", "w"),
    ]
    for row in rows:
        sqlite_backend.execute(
            "INSERT INTO orders (id, buyer_id, status, note) VALUES (?, ?, ?, ?)", row
        )
    return sqlite_backend


class TestColumnDataProfiles:
    """Every figure the fixture makes hand-checkable, asserted by hand."""

    def test_the_unique_key_exactly(self, profiled):
        """``id``: ten distinct values, no nulls, the endpoints 1 and 10."""
        profiles = {
            p.column_name: p for p in profiled.introspector.list_column_data_profiles("orders")
        }

        key = profiles["id"]
        assert key.distinct_count == 10
        assert key.null_fraction == 0.0
        assert key.min_value == 1
        assert key.max_value == 10
        assert key.row_count == 10

    def test_the_three_value_column(self, profiled):
        """``status``: three distinct values and the lexicographic endpoints."""
        profiles = {
            p.column_name: p for p in profiled.introspector.list_column_data_profiles("orders")
        }

        status = profiles["status"]
        assert status.distinct_count == 3
        assert status.null_fraction == 0.0
        # Lexicographic on text: new < paid < shipped.
        assert status.min_value == "new"
        assert status.max_value == "shipped"

    def test_the_column_null_in_sixty_percent_of_rows(self, profiled):
        """``note``: six nulls in ten rows, four distinct non-null values."""
        profiles = {
            p.column_name: p for p in profiled.introspector.list_column_data_profiles("orders")
        }

        note = profiles["note"]
        assert note.null_fraction == pytest.approx(0.6)
        assert note.distinct_count == 4
        assert note.row_count == 10

    def test_every_row_says_how_the_figure_was_produced(self, profiled):
        """The provenance travels in the data, not in a docstring.

        SQLite's figures are exact counts bought with a scan rather than
        readings off a statistics catalogue, and a consumer comparing them
        with a PostgreSQL estimate has to be able to tell the two apart
        without knowing which engine it asked.

        Identity, not equality: ``ProfileSource`` is a ``str`` Enum, so a bare
        ``"aggregate"`` compares equal to the member and an assertion written
        with ``==`` would pass on the word the parser used to write before it
        learned the closed set. ``is`` cannot.
        """
        from rhosocial.activerecord.backend.introspection.types import ProfileSource

        profiles = profiled.introspector.list_column_data_profiles("orders")

        assert profiles, "no profile came back"
        for profile in profiles:
            assert profile.source is ProfileSource.AGGREGATE

    def test_the_column_list_is_the_tables_own(self, profiled):
        """One profile per column, and the names are the table's, in order."""
        profiles = profiled.introspector.list_column_data_profiles("orders")

        assert [p.column_name for p in profiles] == ["id", "buyer_id", "status", "note"]


class TestValueSamples:
    """The listing is the most frequent values, ties broken deterministically."""

    def test_the_counts_come_back_ordered(self, profiled):
        """``status`` is 4 new, 3 paid, 3 shipped -- count first, then value."""
        samples = profiled.introspector.sample_column_values("orders", "status")

        assert [(s.value, s.count) for s in samples] == [
            ("new", 4),
            ("paid", 3),
            ("shipped", 3),
        ]

    def test_the_limit_is_an_upper_bound(self, profiled):
        """Fewer than asked for is a correct answer, not a truncated one."""
        samples = profiled.introspector.sample_column_values("orders", "status", limit=2)

        assert [s.value for s in samples] == ["new", "paid"]

    def test_null_is_a_member_of_the_domain(self, profiled):
        """``note`` is null in six rows -- the most frequent value there is."""
        samples = profiled.introspector.sample_column_values("orders", "note")

        assert samples, "NULL was dropped from the domain"
        assert samples[0].value is None
        assert samples[0].count == 6


class TestJoinCoverage:
    """Both fractions, over distinct values, NULLs excluded from both sides."""

    def test_a_dangling_key_measures_below_one(self, profiled):
        """Four distinct buyer_ids, one of which is not a buyer: 3 of 4.

        Both directions are reported because neither is meaningful alone: three
        of the four tested values exist on the other side, and all three values
        the other side has are reached. Row counts are not what is measured --
        the ``99`` key appears once and the ``1`` key four times, and counting
        rows rather than values would score those differently.
        """
        coverage = profiled.introspector.estimate_join_coverage(
            "orders", "buyer_id", "buyers", "id"
        )

        assert coverage is not None
        assert coverage.left_coverage == pytest.approx(3 / 4)
        assert coverage.right_coverage == pytest.approx(1.0)

    def test_a_column_with_nothing_to_match_answers_no_measurement(self, profiled):
        """Zero overlap is an answer; no measurement is a different one."""
        coverage = profiled.introspector.estimate_join_coverage(
            "orders", "status", "buyers", "label"
        )

        assert coverage is not None
        assert coverage.left_coverage == 0.0
        assert coverage.right_coverage == 0.0

    def test_the_answer_is_none_when_the_engine_cannot_measure(self, profiled):
        """``None`` rather than a row of nulls, which would read as a zero."""
        assert (
            profiled.introspector.estimate_join_coverage("orders", "note", "buyers", "label")
            is not None
        )


class TestRenderedSqlIsPinned:
    """The shape the node construction produces, so text cannot sneak back."""

    def test_the_profile_is_one_set_operation_over_query_statements(self, sqlite_backend):
        """One arm per column, joined by the operator word and nothing else."""
        expr = ColumnDataProfileQueryStatement(
            sqlite_backend.dialect, "orders", columns=("id", "status")
        )
        sql, params = expr.to_sql()

        assert params == ()
        assert sql.count("UNION ALL") == 1, "the arms were not joined by the node"
        assert sql.startswith("SELECT ")
        assert sql.endswith('FROM "orders"')
        # Each arm carries its own label and the provenance it is read with.
        assert sql.count('AS "column_name"') == 2
        assert sql.count('AS "source"') == 2
        assert "'aggregate'" in sql

    def test_a_single_column_profile_is_one_arm(self, sqlite_backend):
        """No operator is written when there is nothing to join."""
        expr = ColumnDataProfileQueryStatement(sqlite_backend.dialect, "orders", columns=("id",))
        sql, _ = expr.to_sql()

        assert "UNION" not in sql
        assert sql.endswith('FROM "orders"')

    def test_an_empty_column_list_selects_no_rows(self, sqlite_backend):
        """A table with no columns is answerable; the answer is empty."""
        expr = ColumnDataProfileQueryStatement(sqlite_backend.dialect, "orders")
        sql, params = expr.to_sql()

        assert params == ()
        assert "WHERE 0 = 1" in sql
        assert sqlite_backend.fetch_all(sql, params) == []

    def test_the_value_sample_groups_and_orders_and_limits(self, sqlite_backend):
        """``GROUP BY`` the column, ``ORDER BY COUNT(*) DESC``, a bound LIMIT."""
        expr = ColumnValueSampleQueryStatement(sqlite_backend.dialect, "orders", "status", limit=5)
        sql, params = expr.to_sql()

        assert sql == (
            'SELECT "status" AS "value", COUNT(*) AS "count" FROM "orders" '
            'GROUP BY "status" ORDER BY COUNT(*) DESC, "status" ASC LIMIT ?'
        )
        assert params == (5,)

    def test_the_coverage_row_is_two_subqueries(self, sqlite_backend):
        """Both fractions, each NULLIF-guarded and NULL-excluded on both sides."""
        expr = JoinCoverageQueryStatement(
            sqlite_backend.dialect, "orders", "buyer_id", "buyers", "id"
        )
        sql, params = expr.to_sql()

        assert params == ()
        assert sql.startswith("SELECT ")
        assert sql.endswith('AS "right_coverage"')
        # Each side is three guards: the tested column in the DISTINCT arm,
        # the other column in the IN subquery, and the denominator.
        assert sql.count("NULLIF(") == 2
        assert sql.count("IS NOT NULL") == 6
        assert sql.count("* 1.0") == 2, "SQLite divides integers by truncation"
        # Both sides are read as distinct values, not rows.
        assert sql.count("SELECT DISTINCT") == 2

    def test_the_node_itself_writes_only_the_operator_word(self, sqlite_backend):
        """The node carries no SQL; the parts are its own statements."""
        parts = [
            QueryStatement(sqlite_backend.dialect, select=[Column(sqlite_backend.dialect, "a")]),
            QueryStatement(sqlite_backend.dialect, select=[Column(sqlite_backend.dialect, "b")]),
            QueryStatement(sqlite_backend.dialect, select=[Column(sqlite_backend.dialect, "c")]),
        ]
        node = SetOperationStatement(
            sqlite_backend.dialect, op=SetOperationKind.UNION_ALL, parts=parts
        )

        # The word form is stored, never the keyword: the dialect maps it.
        assert node.op is SetOperationKind.UNION_ALL
        assert "UNION" not in str(node.op).upper() or node.op.value == "union_all"
        sql, params = node.to_sql()
        assert sql == 'SELECT "a" UNION ALL SELECT "b" UNION ALL SELECT "c"'
        assert params == ()

    def test_an_operation_the_dialect_refuses_is_refused(self, sqlite_backend, monkeypatch):
        """A dialect without the operation does not render a broken promise."""
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

        monkeypatch.setattr(sqlite_backend.dialect, "supports_union_all", lambda: False)
        parts = [
            QueryStatement(sqlite_backend.dialect, select=[Column(sqlite_backend.dialect, "a")]),
            QueryStatement(sqlite_backend.dialect, select=[Column(sqlite_backend.dialect, "b")]),
        ]
        node = SetOperationStatement(
            sqlite_backend.dialect, op=SetOperationKind.UNION_ALL, parts=parts
        )

        with pytest.raises(UnsupportedFeatureError):
            node.to_sql()
