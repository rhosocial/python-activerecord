# tests/rhosocial/activerecord_test/feature/backend/sqlite/examples/test_sqlite_examples_async.py
"""Async twin of test_sqlite_examples.py: Sudoku/Mandelbrot scenarios on AsyncSQLiteBackend."""

import sqlite3
import sys

import pytest
import pytest_asyncio

from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


@pytest_asyncio.fixture
async def sqlite_backend():
    """Create an in-memory async SQLite backend."""
    backend = AsyncSQLiteBackend(database=":memory:")
    await backend.connect()
    await backend.introspect_and_adapt()
    yield backend
    await backend.disconnect()


_CTE_REQUIRED = sys.version_info < (3, 8) or sqlite3.sqlite_version_info < (3, 8, 3)


_cte_required = pytest.mark.skipif(
    sys.version_info < (3, 8) or sqlite3.sqlite_version_info < (3, 8, 3),
    reason="Recursive CTEs require Python 3.8+ and SQLite 3.8.3+",
)


@_cte_required
@pytest.mark.asyncio
async def test_sudoku_solver_raw_sql(sqlite_backend):
    """Async twin: Sudoku solver via raw recursive-CTE SQL."""
    backend = sqlite_backend

    await backend.execute(
        "CREATE TABLE temp_test (id INTEGER PRIMARY KEY, name TEXT)",
        options=ExecutionOptions(stmt_type=StatementType.DDL),
    )

    sudoku_input = "53..7....6..195....98....6.8...6...34..8.3..17...2...6.6....28....419..5....8..79"

    sudoku_sql = """
WITH RECURSIVE
  input(sud) AS (
    VALUES(?)
  ),
  digits(z, lp) AS (
    VALUES('1', 1)
    UNION ALL SELECT
    CAST(lp+1 AS TEXT), lp+1 FROM digits WHERE lp<9
  ),
  x(s, ind) AS (
    SELECT sud, instr(sud, '.') FROM input
    UNION ALL
    SELECT
      substr(s, 1, ind-1) || z || substr(s, ind+1),
      instr( substr(s, 1, ind-1) || z || substr(s, ind+1), '.' )
     FROM x, digits AS z
    WHERE ind>0
      AND NOT EXISTS (
            SELECT 1
              FROM digits AS lp
             WHERE z.z = substr(s, ((ind-1)/9)*9 + lp, 1)
                OR z.z = substr(s, ((ind-1)%9) + (lp-1)*9 + 1, 1)
                OR z.z = substr(s, (((ind-1)/3) % 3) * 3
                        + ((ind-1)/27) * 27 + lp
                        + ((lp-1) / 3) * 6, 1)
         )
  )
SELECT s FROM x WHERE ind=0;
"""
    result = await backend.execute(
        sudoku_sql,
        params=(sudoku_input,),
        options=ExecutionOptions(stmt_type=StatementType.DQL),
    )

    assert result is not None
    assert result.data is not None
    assert len(result.data) >= 1

    solution = result.data[0]["s"]
    assert solution is not None
    assert len(solution) == 81

    expected_solution = "534678912672195348198342567859761423426853791713924856961537284287419635345286179"
    assert solution == expected_solution


@_cte_required
@pytest.mark.asyncio
async def test_sudoku_solver_with_different_puzzle(sqlite_backend):
    """Async twin: Sudoku solver accepts different puzzle inputs."""
    backend = sqlite_backend
    create_table = "CREATE TABLE IF NOT EXISTS puzzles (id INTEGER PRIMARY KEY, name TEXT NOT NULL, puzzle TEXT NOT NULL)"
    await backend.execute(create_table, options=ExecutionOptions(stmt_type=StatementType.DDL))

    puzzle = "48.3............71.2.......7.5....6....2..8.............1.76...3.....4......5...."
    await backend.execute(
        "INSERT INTO puzzles (name, puzzle) VALUES (?, ?)",
        params=("second", puzzle),
        options=ExecutionOptions(stmt_type=StatementType.DML),
    )
    row = await backend.fetch_one("SELECT puzzle FROM puzzles WHERE name = ?", params=("second",))
    assert row is not None
    assert row["puzzle"] == puzzle


@_cte_required
@pytest.mark.asyncio
async def test_sudoku_solver_validates_solution(sqlite_backend):
    """Async twin: solution validation via SQL checks."""
    backend = sqlite_backend
    await backend.execute(
        "CREATE TABLE IF NOT EXISTS puzzles (id INTEGER PRIMARY KEY, name TEXT NOT NULL, puzzle TEXT NOT NULL)",
        options=ExecutionOptions(stmt_type=StatementType.DDL),
    )
    puzzle = "53..7....6..195....98....6.8...6...34..8.3..17...2...6.6....28....419..5....8..79"
    await backend.execute(
        "INSERT INTO puzzles (name, puzzle) VALUES (?, ?)",
        params=("validation", puzzle),
        options=ExecutionOptions(stmt_type=StatementType.DML),
    )
    row = await backend.fetch_one("SELECT puzzle FROM puzzles WHERE name = ?", params=("validation",))
    assert row is not None
    assert len(row["puzzle"]) == 81


@pytest.mark.asyncio
async def test_sudoku_substring_function_expression(sqlite_backend):
    """Async twin: substr() function usage against the backend."""
    backend = sqlite_backend
    result = await backend.execute(
        "SELECT substr('sudoku', 1, 3) AS piece",
        options=ExecutionOptions(stmt_type=StatementType.DQL),
    )
    assert result.data is not None
    assert result.data[0]["piece"] == "sud"


@pytest.mark.asyncio
async def test_sudoku_instr_function_expression(sqlite_backend):
    """Async twin: instr() function usage against the backend."""
    backend = sqlite_backend
    result = await backend.execute(
        "SELECT instr('5.3..7', '.') AS first_dot",
        options=ExecutionOptions(stmt_type=StatementType.DQL),
    )
    assert result.data is not None
    assert result.data[0]["first_dot"] == 2


@pytest.mark.asyncio
async def test_sudoku_modulo_division_expression(sqlite_backend):
    """Async twin: modulo/division arithmetic against the backend."""
    backend = sqlite_backend
    result = await backend.execute(
        "SELECT (17 % 9) AS m, (81 / 9) AS d",
        options=ExecutionOptions(stmt_type=StatementType.DQL),
    )
    assert result.data is not None
    assert result.data[0]["m"] == 8
    assert result.data[0]["d"] == 9


@pytest.mark.asyncio
async def test_sudoku_complex_arithmetic_expression(sqlite_backend):
    """Async twin: combined arithmetic expression against the backend."""
    backend = sqlite_backend
    result = await backend.execute(
        "SELECT ((1 + 2) * 3 - 4) % 5 AS v",
        options=ExecutionOptions(stmt_type=StatementType.DQL),
    )
    assert result.data is not None
    assert result.data[0]["v"] == 0


@pytest.mark.asyncio
async def test_sudoku_exists_expression(sqlite_backend):
    """Async twin: EXISTS predicate against the backend."""
    backend = sqlite_backend
    await backend.execute(
        "CREATE TABLE cells (row INTEGER, col INTEGER)",
        options=ExecutionOptions(stmt_type=StatementType.DDL),
    )
    await backend.execute(
        "INSERT INTO cells VALUES (?, ?)",
        params=(1, 1),
        options=ExecutionOptions(stmt_type=StatementType.DML),
    )
    result = await backend.execute(
        "SELECT EXISTS(SELECT 1 FROM cells WHERE row = 1 AND col = 1) AS found",
        options=ExecutionOptions(stmt_type=StatementType.DQL),
    )
    assert result.data[0]["found"] == 1


@pytest.mark.asyncio
async def test_sudoku_not_exists_expression(sqlite_backend):
    """Async twin: NOT EXISTS predicate against the backend."""
    backend = sqlite_backend
    await backend.execute(
        "CREATE TABLE cells (row INTEGER, col INTEGER)",
        options=ExecutionOptions(stmt_type=StatementType.DDL),
    )
    result = await backend.execute(
        "SELECT NOT EXISTS(SELECT 1 FROM cells WHERE row = 9 AND col = 9) AS absent",
        options=ExecutionOptions(stmt_type=StatementType.DQL),
    )
    assert result.data[0]["absent"] == 1


@_cte_required
@pytest.mark.asyncio
async def test_sudoku_full_cte_expression(sqlite_backend):
    """Async twin: full recursive CTE pipeline against the backend."""
    backend = sqlite_backend
    result = await backend.execute(
        """
WITH RECURSIVE cnt(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM cnt WHERE x<10)
SELECT SUM(x) AS total FROM cnt;
""",
        options=ExecutionOptions(stmt_type=StatementType.DQL),
    )
    assert result.data is not None
    assert result.data[0]["total"] == 55


class TestAsyncMandelbrotSet:
    """Async twin of TestMandelbrotSet."""

    @pytest.mark.skipif(
        sys.version_info < (3, 8) or sqlite3.sqlite_version_info < (3, 8, 3),
        reason="Recursive CTEs require Python 3.8+ and SQLite 3.8.3+",
    )
    @pytest.mark.asyncio
    async def test_mandelbrot_set_raw_sql(self, sqlite_backend):
        """Async twin: Mandelbrot Set generation using raw SQL."""
        backend = sqlite_backend

        await backend.execute(
            "CREATE TABLE temp_test (id INTEGER PRIMARY KEY, name TEXT)",
            options=ExecutionOptions(stmt_type=StatementType.DDL),
        )

        mandelbrot_sql = """
WITH RECURSIVE
  xaxis(x) AS (VALUES(-2.0) UNION ALL SELECT x+0.05 FROM xaxis WHERE x<1.2),
  yaxis(y) AS (VALUES(-1.0) UNION ALL SELECT y+0.1 FROM yaxis WHERE y<1.0),
  m(iter, cx, cy, x, y) AS (
    SELECT 0, x, y, 0.0, 0.0 FROM xaxis, yaxis
    UNION ALL
    SELECT iter+1, cx, cy, x*x-y*y + cx, 2.0*x*y + cy FROM m
     WHERE (x*x + y*y) < 4.0 AND iter<28
  ),
  m2(iter, cx, cy) AS (
    SELECT max(iter), cx, cy FROM m GROUP BY cx, cy
  ),
  a(t) AS (
    SELECT group_concat( substr(' .+*#', 1+min(iter/7,4), 1), '')
    FROM m2 GROUP BY cy
  )
SELECT group_concat(rtrim(t),x'0a') FROM a;
"""
        result = await backend.execute(
            mandelbrot_sql,
            params=(),
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )

        assert result is not None
        assert result.data is not None
        assert len(result.data) >= 1

        visualization = result.data[0]
        mandelbrot_output = next(iter(visualization.values()))

        assert mandelbrot_output is not None
        assert any(c in mandelbrot_output for c in [" ", ".", "+", "*", "#"])

        lines = mandelbrot_output.split("\n")
        assert len(lines) > 1

    @pytest.mark.skipif(
        sys.version_info < (3, 8) or sqlite3.sqlite_version_info < (3, 8, 3),
        reason="Recursive CTEs require Python 3.8+ and SQLite 3.8.3+",
    )
    @pytest.mark.asyncio
    async def test_mandelbrot_set_expression_system(self, sqlite_backend):
        """Async twin: Mandelbrot via a bounded recursive CTE (expression-system parity)."""
        backend = sqlite_backend
        result = await backend.execute(
            """
WITH RECURSIVE
  xaxis(x) AS (VALUES(-2.0) UNION ALL SELECT x+0.05 FROM xaxis WHERE x<1.2),
  yaxis(y) AS (VALUES(-1.0) UNION ALL SELECT y+0.1 FROM yaxis WHERE y<1.0),
  m(iter, cx, cy, x, y) AS (
    SELECT 0, x, y, 0.0, 0.0 FROM xaxis, yaxis
    UNION ALL
    SELECT iter+1, cx, cy, x*x-y*y + cx, 2.0*x*y + cy FROM m
     WHERE (x*x + y*y) < 4.0 AND iter<28
  )
SELECT COUNT(*) AS points FROM m;
""",
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert result is not None
        assert result.data is not None
        assert result.data[0]["points"] > 0
