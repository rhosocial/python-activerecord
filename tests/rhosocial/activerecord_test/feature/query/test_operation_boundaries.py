# tests/rhosocial/activerecord_test/feature/query/test_operation_boundaries.py
"""The four string boundaries the 2026-10-09 ruling settled, plus the NULL-safe
comparison it added to the surface.

``operation-groups-matrix.md`` section F records the measurement: what the ten
backends answer for a negative count, an empty pad, a position below 1 and a
multi-character trim set, and which answer -- if any -- is common ground. This
file pins the outcome. Edges every backend agrees on render; the rest are
refused at construction instead of rendered into whatever the dialect happens
to do. ``is_distinct_from`` is here too: its spelling varies by backend, so it
is a dialect hook with a gate, and the gate refuses rather than substitutes a
different question.
"""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.column_types import StringColumn
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


@pytest.fixture
def sqlite_dialect():
    dialect = SQLiteDialect()
    dialect.version = (3, 46, 1)
    return dialect


@pytest.fixture
def name(sqlite_dialect):
    return StringColumn(sqlite_dialect, "name")


REFUSALS = [
    ("left", (-1,)),
    ("right", (-1,)),
    ("lpad", (-1,)),
    ("lpad", (5, "")),
    ("rpad", (-1,)),
    ("rpad", (5, "")),
    ("substr", (0,)),
    ("substr", (-2, 3)),
    ("substr", (1, -1)),
    ("trim", ("xy",)),
    ("trim", ("",)),
]


@pytest.mark.parametrize(
    "method,args",
    [("left", (-1,)), ("right", (-1,)), ("lpad", (-1,)), ("lpad", (5, "")),
     ("rpad", (-1,)), ("rpad", (5, "")), ("substr", (0,)), ("substr", (-2, 3)),
     ("substr", (1, -1)), ("trim", ("xy",)), ("trim", ("",))],
    ids=("left", "right", "lpad_negative", "lpad_empty_pad",
         "rpad_negative", "rpad_empty_pad", "substr_start0", "substr_negative_start",
         "substr_negative_length", "trim_two_chars", "trim_empty_set"),
)
def test_the_edge_where_the_backends_disagree_is_refused(name, method, args):
    """No two backends answer these the same way, so the answer is a refusal
    at construction rather than a silent coin flip at render time."""
    with pytest.raises(ValueError):
        getattr(name, method)(*args)


@pytest.mark.parametrize(
    "method,args,expected_sql,expected_params",
    [
        ("left", (0,), 'LEFT("name", ?)', (0,)),
        ("repeat", (0,), 'REPEAT("name", ?)', (0,)),
        ("substr", (1, 0), 'SUBSTRING("name", ?, ?)', (1, 0)),
        ("trim", ("x",), 'TRIM(BOTH ? FROM "name")', ("x",)),
    ],
)
def test_the_edge_every_backend_agrees_on_renders(name, method, args, expected_sql, expected_params):
    """The inside of the contract: zero-length results, the empty substring,
    the whole-string over-length read and a one-character trim set behave the
    same on every backend, so they render."""
    sql, params = getattr(name, method)(*args).to_sql()
    assert sql == expected_sql
    assert params == expected_params


def test_lpad_defaults_to_a_space_and_passes_it_explicitly(name):
    """MySQL raises 1582 without a pad and MariaDB supplies one, so the core
    always spells it out instead of letting the backend choose."""
    sql, params = name.lpad(3).to_sql()
    assert sql == 'LPAD("name", ?, ?)'
    assert params == (3, " ")


def test_a_negative_repeat_is_the_empty_string(name):
    """PostgreSQL, MySQL, MariaDB and ClickHouse all answer ``''`` for a
    negative count; SQL Server answers NULL and Oracle, Firebird and SQLite
    lack the function, so the core answers once instead of four times."""
    expr = name.repeat(-1)
    assert "REPEAT" not in expr.to_sql()[0]
    assert expr.to_sql() == ("?", ("",))


def test_is_distinct_from_renders_the_null_safe_comparison():
    """The default rendering is the standard spelling; backends that spell it
    differently override the hook instead of every call site writing dialect
    SQL."""
    column = StringColumn(DummyDialect(), "age")
    assert column.is_distinct_from(0).to_sql() == ('"age" IS DISTINCT FROM ?', (0,))
    assert column.is_not_distinct_from(0).to_sql() == ('"age" IS NOT DISTINCT FROM ?', (0,))


@pytest.mark.parametrize("version,expected", [((3, 39, 0), True), ((3, 38, 0), False)])
def test_sqlite_gates_the_spelling_on_its_version(version, expected):
    dialect = SQLiteDialect()
    dialect.version = version
    assert dialect.supports_distinct_from() is expected


def test_sqlite_below_the_gate_refuses_rather_than_substituting():
    dialect = SQLiteDialect()
    dialect.version = (3, 38, 0)
    column = StringColumn(dialect, "age")
    with pytest.raises(UnsupportedFeatureError):
        column.is_distinct_from(0).to_sql()
