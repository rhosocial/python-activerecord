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
    WildcardExpression,
)
from rhosocial.activerecord.backend.expression.query_sources import (
    CTEExpression,
    WithQueryExpression,
    SetOperationExpression,
    ValuesExpression,
)
from rhosocial.activerecord.backend.expression.query_parts import (
    GroupByHavingClause,
    LimitOffsetClause,
    OrderByClause,
    JoinExpression,
)
from rhosocial.activerecord.backend.expression.advanced_functions import (
    ExistsExpression,
    CaseExpression,
)
from rhosocial.activerecord.backend.expression.functions.string import concat_op
from rhosocial.activerecord.backend.expression.functions.type_conversion import cast
from rhosocial.activerecord.backend.expression.predicates import LikePredicate
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


def build_bom(d):
    """Build a multi-level Bill of Materials explosion query (tree recursion).

    WITH RECURSIVE BOM_Explosion AS (
      SELECT child_id, quantity, quantity AS total_qty
      FROM parts_tree WHERE parent_id = 1
      UNION ALL
      SELECT c.child_id, c.quantity, b.total_qty * c.quantity
      FROM parts_tree c JOIN BOM_Explosion b ON c.parent_id = b.child_id
    )
    SELECT child_id, SUM(total_qty) AS required_count
    FROM BOM_Explosion GROUP BY child_id;
    """
    anchor = QueryExpression(
        d,
        select=[Column(d, "child_id"), Column(d, "quantity"), Column(d, "quantity").as_("total_qty")],
        from_=TableExpression(d, "parts_tree"),
        where=Column(d, "parent_id") == Literal(d, 1),
    )
    step = QueryExpression(
        d,
        select=[
            Column(d, "child_id", "c"),
            Column(d, "quantity", "c"),
            Column(d, "total_qty", "b") * Column(d, "quantity", "c"),
        ],
        from_=[
            TableExpression(d, "parts_tree", alias="c"),
            TableExpression(d, "BOM_Explosion", alias="b"),
        ],
        where=Column(d, "parent_id", "c") == Column(d, "child_id", "b"),
    )
    union = SetOperationExpression(d, left=anchor, right=step, operation="UNION", all_=True)
    cte = CTEExpression(
        d, name="BOM_Explosion", query=union, columns=["child_id", "quantity", "total_qty"]
    )
    main = QueryExpression(
        d,
        select=[Column(d, "child_id"), FunctionCall(d, "SUM", Column(d, "total_qty")).as_("required_count")],
        from_=TableExpression(d, "BOM_Explosion"),
        group_by_having=GroupByHavingClause(d, group_by=[Column(d, "child_id")]),
    )
    return WithQueryExpression(d, ctes=[cte], main_query=main)


def build_flight_paths(d):
    """Build a cheapest-flight / BFS path search with cycle detection (graph).

    WITH RECURSIVE FlightPaths AS (
      SELECT destination, price, 1 AS depth, 'TPE -> ' || destination AS path
      FROM flights WHERE departure = 'TPE'
      UNION ALL
      SELECT f.destination, p.price + f.price, p.depth + 1, p.path || ' -> ' || f.destination
      FROM flights f JOIN FlightPaths p ON f.departure = p.destination
      WHERE p.path NOT LIKE '%' || f.destination || '%' AND p.depth < 5
    )
    SELECT * FROM FlightPaths WHERE destination = 'JFK' ORDER BY price ASC LIMIT 1;
    """
    anchor = QueryExpression(
        d,
        select=[
            Column(d, "destination"),
            Column(d, "price"),
            Literal(d, 1),
            concat_op(d, Literal(d, "TPE -> "), Column(d, "destination")),
        ],
        from_=TableExpression(d, "flights"),
        where=Column(d, "departure") == Literal(d, "TPE"),
    )
    step = QueryExpression(
        d,
        select=[
            Column(d, "destination", "f"),
            Column(d, "price", "p") + Column(d, "price", "f"),
            Column(d, "depth", "p") + Literal(d, 1),
            concat_op(d, Column(d, "path", "p"), Literal(d, " -> "), Column(d, "destination", "f")),
        ],
        from_=[
            TableExpression(d, "flights", alias="f"),
            TableExpression(d, "FlightPaths", alias="p"),
        ],
        where=(
            LikePredicate(
                d,
                "NOT LIKE",
                Column(d, "path", "p"),
                concat_op(d, Literal(d, "%"), Column(d, "destination", "f"), Literal(d, "%")),
            )
        )
        & (Column(d, "depth", "p") < Literal(d, 5)),
    )
    union = SetOperationExpression(d, left=anchor, right=step, operation="UNION", all_=True)
    cte = CTEExpression(
        d, name="FlightPaths", query=union, columns=["destination", "price", "depth", "path"]
    )
    main = QueryExpression(
        d,
        select=[WildcardExpression(d)],
        from_=TableExpression(d, "FlightPaths"),
        where=Column(d, "destination") == Literal(d, "JFK"),
        order_by=OrderByClause(d, [Column(d, "price")]),
        limit_offset=LimitOffsetClause(d, limit=Literal(d, 1)),
    )
    return WithQueryExpression(d, ctes=[cte], main_query=main)


def build_game_of_life(d):
    """Build a single-generation Conway's Game of Life step (cellular automaton).

    Expands each live cell's 8 neighbours via UNION ALL, counts them with
    GROUP BY, then applies the birth / survival rules with CASE WHEN against
    a LEFT JOIN of the live table.
    """
    live = TableExpression(d, "live", alias="l")
    x = Column(d, "x")
    y = Column(d, "y")
    gen = Column(d, "gen")

    def neighbor(dx, dy):
        return QueryExpression(
            d,
            select=[
                (x + Literal(d, dx)).as_("x"),
                (y + Literal(d, dy)).as_("y"),
                gen,
            ],
            from_=live,
        )

    offsets = [(0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)]
    expansion = neighbor(*offsets[0])
    for dx, dy in offsets[1:]:
        expansion = SetOperationExpression(
            d, left=expansion, right=neighbor(dx, dy), operation="UNION", all_=True
        )

    nb = Subquery(d, expansion, alias="nb")
    neighbors = QueryExpression(
        d,
        select=[Column(d, "x"), Column(d, "y"), Column(d, "gen"), FunctionCall(d, "COUNT", Literal(d, "*")).as_("cnt")],
        from_=nb,
        group_by_having=GroupByHavingClause(
            d, group_by=[Column(d, "x"), Column(d, "y"), Column(d, "gen")]
        ),
    )
    nsub = Subquery(d, neighbors, alias="n")
    l_x_null = Column(d, "x", "l").is_null()
    alive = CaseExpression(
        d,
        cases=[
            (l_x_null & (Column(d, "cnt", "n") == Literal(d, 3)), Literal(d, 1)),
            ((~l_x_null) & Column(d, "cnt", "n").in_([2, 3]), Literal(d, 1)),
        ],
        else_result=Literal(d, 0),
    )
    on = (
        (Column(d, "x", "l") == Column(d, "x", "n"))
        & (Column(d, "y", "l") == Column(d, "y", "n"))
        & (Column(d, "gen", "l") == Column(d, "gen", "n"))
    )
    join = JoinExpression(d, left_table=nsub, right_table=live, join_type="LEFT JOIN", condition=on)
    return QueryExpression(
        d,
        select=[
            Column(d, "x", "n"),
            Column(d, "y", "n"),
            Column(d, "gen", "n") + Literal(d, 1),
            alive,
        ],
        from_=join,
    )


class TestComplexWithExpressionRoundtrip:
    """Complex WITH RECURSIVE expression trees round-trip losslessly."""

    @pytest.mark.parametrize("name,builder", [
        ("mandelbrot", build_mandelbrot),
        ("sudoku", build_sudoku),
        ("bom", build_bom),
        ("flight_paths", build_flight_paths),
        ("game_of_life", build_game_of_life),
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

    def test_bom_explosion_computes_quantities(self, sqlite_dialect):
        """BOM recursion multiplies quantities down the tree and sums per part."""
        q = build_bom(sqlite_dialect)
        sql, params = q.to_sql()
        conn = sqlite3.connect(":memory:")
        try:
            conn.executescript(
                """
                CREATE TABLE parts_tree(parent_id INT, child_id INT, quantity INT);
                INSERT INTO parts_tree VALUES
                 (1, 2, 2), (1, 3, 1), (2, 4, 3), (2, 5, 2), (3, 6, 4),
                 (4, 7, 1), (6, 8, 2), (6, 9, 1);
                """
            )
            cur = conn.execute(sql, params)
            result = dict(cur.fetchall())
            assert result == {
                2: 2, 3: 1, 4: 6, 5: 4, 6: 4, 7: 6, 8: 8, 9: 4,
            }
        finally:
            conn.close()

    def test_flight_paths_finds_cheapest_route(self, sqlite_dialect):
        """BFS with cycle detection finds the cheapest TPE -> JFK flight."""
        q = build_flight_paths(sqlite_dialect)
        sql, params = q.to_sql()
        conn = sqlite3.connect(":memory:")
        try:
            conn.executescript(
                """
                CREATE TABLE flights(departure TEXT, destination TEXT, price INT);
                INSERT INTO flights VALUES
                 ('TPE','HKG',120),('TPE','NRT',200),('TPE','LAX',800),
                 ('HKG','JFK',600),('NRT','JFK',500),('NRT','LAX',400),('LAX','JFK',300);
                """
            )
            cur = conn.execute(sql, params)
            rows = cur.fetchall()
            assert len(rows) == 1
            assert rows[0][1] == 420  # TPE -> HKG (120) -> JFK (300)
            assert rows[0][3] == "TPE -> HKG -> JFK"
        finally:
            conn.close()

    def test_game_of_life_evolves_glider(self, sqlite_dialect):
        """Conway rules (CASE WHEN + neighbour counting) evolve a glider correctly."""
        q = build_game_of_life(sqlite_dialect)
        sql, params = q.to_sql()
        conn = sqlite3.connect(":memory:")
        try:
            conn.executescript(
                """
                CREATE TABLE live(x INT, y INT, gen INT);
                INSERT INTO live VALUES (1,0,0),(2,1,0),(0,2,0),(1,2,0),(2,2,0);
                """
            )
            cur = conn.execute(sql, params)
            next_gen = sorted((r[0], r[1]) for r in cur.fetchall() if r[3] == 1)
            assert next_gen == [(0, 1), (1, 2), (1, 3), (2, 1), (2, 2)]
        finally:
            conn.close()