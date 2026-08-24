# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_expression_roundtrip_complex_with.py
"""
Complex WITH RECURSIVE expression round-trip tests based on SQLite's documented
example queries (Mandelbrot set, Sudoku solver).

https://sqlite.org/lang_with.html — Outlandish Recursive Query Examples

These queries are built as deep expression trees (CTEExpression,
WithQueryExpression, SetOperationExpression, ValuesExpression, QueryExpression,
FunctionCall, arithmetic operators, concat_op, ExistsExpression, etc.) and
round-tripped through dict / JSON / XML to stress-test the serialization
machinery with deeply nested recursive structures.
"""

import pytest
import sqlite3

from rhosocial.activerecord.backend.expression import (
    Column,
    Literal,
    FunctionCall,
    TableExpression,
    QueryExpression,
    Subquery,
)
from rhosocial.activerecord.backend.expression.query_sources import (
    CTEExpression,
    WithQueryExpression,
    SetOperationExpression,
    ValuesExpression,
)
from rhosocial.activerecord.backend.expression.query_parts import GroupByHavingClause
from rhosocial.activerecord.backend.expression.advanced_functions import ExistsExpression
from rhosocial.activerecord.backend.expression.functions.string import concat_op
from rhosocial.activerecord.backend.expression.functions.type_conversion import cast
from rhosocial.activerecord.backend.expression.serialization import (
    serialize,
    deserialize,
    serialize_json,
    deserialize_json,
    serialize_xml,
    deserialize_xml,
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.testsuite.utils.expression import assert_params_equal


@pytest.fixture
def sqlite_dialect():
    d = SQLiteDialect(version=(3, 53, 0))
    return d


def build_mandelbrot(d):
    """Build the Mandelbrot set query from the SQLite docs as an expression tree."""

    def _make_axis_union(cte_name, column, start, step, limit_):
        base = ValuesExpression(d, [(start,)])
        rec = QueryExpression(
            d,
            select=[Column(d, column) + Literal(d, step)],
            from_=TableExpression(d, cte_name),
            where=Column(d, column) < Literal(d, limit_),
        )
        return SetOperationExpression(d, left=base, right=rec, operation="UNION", all_=True)

    xaxis_cte = CTEExpression(
        d, name="xaxis", query=_make_axis_union("xaxis", "x", -2.0, 0.05, 1.2), columns=["x"]
    )
    yaxis_cte = CTEExpression(
        d, name="yaxis", query=_make_axis_union("yaxis", "y", -1.0, 0.1, 1.0), columns=["y"]
    )

    m_seed = QueryExpression(
        d,
        select=[Literal(d, 0), Column(d, "x"), Column(d, "y"), Literal(d, 0.0), Literal(d, 0.0)],
        from_=[TableExpression(d, "xaxis"), TableExpression(d, "yaxis")],
    )
    m_step = QueryExpression(
        d,
        select=[
            Column(d, "iter") + Literal(d, 1),
            Column(d, "cx"),
            Column(d, "cy"),
            Column(d, "x") * Column(d, "x") - Column(d, "y") * Column(d, "y") + Column(d, "cx"),
            Literal(d, 2.0) * Column(d, "x") * Column(d, "y") + Column(d, "cy"),
        ],
        from_=TableExpression(d, "m"),
        where=((Column(d, "x") * Column(d, "x") + Column(d, "y") * Column(d, "y")) < Literal(d, 4.0))
        & (Column(d, "iter") < Literal(d, 28)),
    )
    m_cte = CTEExpression(
        d,
        name="m",
        query=SetOperationExpression(d, left=m_seed, right=m_step, operation="UNION", all_=True),
        columns=["iter", "cx", "cy", "x", "y"],
    )

    m2_query = QueryExpression(
        d,
        select=[FunctionCall(d, "MAX", Column(d, "iter")), Column(d, "cx"), Column(d, "cy")],
        from_=TableExpression(d, "m"),
        group_by_having=GroupByHavingClause(d, group_by=[Column(d, "cx"), Column(d, "cy")]),
    )
    m2_cte = CTEExpression(d, name="m2", query=m2_query, columns=["iter", "cx", "cy"])

    min_expr = FunctionCall(d, "MIN", Column(d, "iter") / Literal(d, 7), Literal(d, 4))
    substr_expr = FunctionCall(d, "SUBSTR", Literal(d, " .+*#"), Literal(d, 1) + min_expr, Literal(d, 1))
    a_query = QueryExpression(
        d,
        select=[FunctionCall(d, "GROUP_CONCAT", substr_expr, Literal(d, ""))],
        from_=TableExpression(d, "m2"),
        group_by_having=GroupByHavingClause(d, group_by=[Column(d, "cy")]),
    )
    a_cte = CTEExpression(d, name="a", query=a_query, columns=["t"])

    main = QueryExpression(
        d,
        select=[FunctionCall(d, "GROUP_CONCAT", FunctionCall(d, "RTRIM", Column(d, "t")), Literal(d, b"\x0a"))],
        from_=TableExpression(d, "a"),
    )
    return WithQueryExpression(
        d, ctes=[xaxis_cte, yaxis_cte, m_cte, m2_cte, a_cte], main_query=main, recursive=True
    )


def build_sudoku(d, puzzle="53..7....6..195....98....6.8...6...34..8.3..17...2...6.6....28....419..5....8..79"):
    """Build the Sudoku solver query from the SQLite docs as an expression tree."""

    input_cte = CTEExpression(
        d, name="input", query=ValuesExpression(d, [(puzzle,)]), columns=["sud"]
    )

    digits_seed = ValuesExpression(d, [("1", 1)])
    digits_step = QueryExpression(
        d,
        select=[cast(d, Column(d, "lp") + Literal(d, 1), "TEXT"), Column(d, "lp") + Literal(d, 1)],
        from_=TableExpression(d, "digits"),
        where=Column(d, "lp") < Literal(d, 9),
    )
    digits_cte = CTEExpression(
        d,
        name="digits",
        query=SetOperationExpression(d, left=digits_seed, right=digits_step, operation="UNION", all_=True),
        columns=["z", "lp"],
    )

    s = Column(d, "s")
    ind = Column(d, "ind")
    z = Column(d, "z")

    x_seed = QueryExpression(
        d,
        select=[Column(d, "sud"), FunctionCall(d, "INSTR", Column(d, "sud"), Literal(d, "."))],
        from_=TableExpression(d, "input"),
    )

    s_candidate = concat_op(
        d,
        FunctionCall(d, "SUBSTR", s, Literal(d, 1), ind - Literal(d, 1)),
        z,
        FunctionCall(d, "SUBSTR", s, ind + Literal(d, 1)),
    )

    # Build the NOT EXISTS subquery with three OR conditions
    lp = Column(d, "lp", "lp")
    one = Literal(d, 1)
    zero = Literal(d, 0)
    nine = Literal(d, 9)
    three = Literal(d, 3)
    six = Literal(d, 6)
    twenty_seven = Literal(d, 27)

    row_cond = Column(d, "z", "z") == FunctionCall(
        d, "SUBSTR", s, ((ind - one) / nine) * nine + lp, one
    )
    col_cond = Column(d, "z", "z") == FunctionCall(
        d, "SUBSTR", s, ((ind - one) % nine) + (lp - one) * nine + one, one
    )
    box_cond = Column(d, "z", "z") == FunctionCall(
        d, "SUBSTR", s,
        (((ind - one) / three) % three) * three + ((ind - one) / twenty_seven) * twenty_seven + lp + ((lp - one) / three) * six,
        one,
    )

    not_exists = ~ExistsExpression(
        d,
        Subquery(
            d,
            QueryExpression(
                d,
                select=[one],
                from_=TableExpression(d, "digits", alias="lp"),
                where=row_cond | col_cond | box_cond,
            ),
        ),
    )

    x_step = QueryExpression(
        d,
        select=[s_candidate, FunctionCall(d, "INSTR", s_candidate, Literal(d, "."))],
        from_=[TableExpression(d, "x"), TableExpression(d, "digits", alias="z")],
        where=(ind > zero) & not_exists,
    )
    x_cte = CTEExpression(
        d,
        name="x",
        query=SetOperationExpression(d, left=x_seed, right=x_step, operation="UNION", all_=True),
        columns=["s", "ind"],
    )

    main = QueryExpression(
        d,
        select=[Column(d, "s")],
        from_=TableExpression(d, "x"),
        where=Column(d, "ind") == Literal(d, 0),
    )
    return WithQueryExpression(d, ctes=[input_cte, digits_cte, x_cte], main_query=main, recursive=True)


class TestComplexWithExpressionRoundtrip:
    """Complex WITH RECURSIVE expression trees round-trip losslessly."""

    @pytest.mark.parametrize("name,builder", [
        ("mandelbrot", build_mandelbrot),
        ("sudoku", build_sudoku),
    ])
    def test_roundtrip_all_encodings(self, sqlite_dialect, name, builder):
        d = sqlite_dialect
        q = builder(d)
        for enc_name, ser, de in [
            ("dict", serialize, deserialize),
            ("json", serialize_json, deserialize_json),
            ("xml", serialize_xml, deserialize_xml),
        ]:
            restored = de(ser(q), d)
            assert_params_equal(restored.get_params(), q.get_params(), f"{name}.{enc_name}")
            r_sql, r_params = restored.to_sql()
            assert r_sql == q.to_sql()[0], f"{name}.{enc_name}: SQL mismatch"
            assert r_params == q.to_sql()[1], f"{name}.{enc_name}: params mismatch"

    def test_mandelbrot_executes_and_produces_ascii_art(self, sqlite_dialect):
        """Verify the generated SQL is valid by running it against a real SQLite database."""
        q = build_mandelbrot(sqlite_dialect)
        sql, params = q.to_sql()
        conn = sqlite3.connect(":memory:")
        try:
            cur = conn.execute(sql, params)
            rows = cur.fetchall()
            assert len(rows) > 0
            assert rows[0][0] is not None
            assert " " in rows[0][0]  # ASCII art has spaces
        finally:
            conn.close()

    def test_sudoku_solves_puzzle(self, sqlite_dialect):
        """Verify the Sudoku solver SQL produces the correct solution."""
        q = build_sudoku(sqlite_dialect)
        sql, params = q.to_sql()
        conn = sqlite3.connect(":memory:")
        try:
            cur = conn.execute(sql, params)
            rows = cur.fetchall()
            expected = "534678912672195348198342567859761423426853791713924856961537284287419635345286179"
            assert len(rows) == 1
            assert rows[0][0] == expected
        finally:
            conn.close()