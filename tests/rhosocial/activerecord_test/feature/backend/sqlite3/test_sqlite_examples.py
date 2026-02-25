#!/usr/bin/env python
"""
Sudoku solver SQL example test using SQLite dialect
"""
import pytest
import sqlite3
import sys

from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


@pytest.fixture
def sqlite_backend():
    """
    Creates a test fixture for an in-memory SQLite backend
    """
    backend = SQLiteBackend(database=":memory:")
    backend.connect()
    yield backend
    backend.disconnect()


@pytest.mark.skipif(
    sys.version_info < (3, 8) or sqlite3.sqlite_version_info < (3, 8, 3),
    reason="Recursive CTEs require Python 3.8+ and SQLite 3.8.3+"
)
def test_sudoku_solver_raw_sql(sqlite_backend):
    """
    Test Sudoku solver using raw SQL.
    This test executes the complete Sudoku solving SQL query to verify it produces the correct result.
    """
    backend = sqlite_backend

    # Create a test table to ensure the backend is working
    backend.execute(
        "CREATE TABLE temp_test (id INTEGER PRIMARY KEY, name TEXT)",
        options=ExecutionOptions(stmt_type=StatementType.DDL)
    )

    print("\n--- Building and Executing Sudoku Solver SQL ---")

    # Define the Sudoku input
    sudoku_input = '53..7....6..195....98....6.8...6...34..8.3..17...2...6.6....28....419..5....8..79'

    print(f"Sudoku input: {sudoku_input}")

    # Complete Sudoku solving SQL query
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

    # Execute the Sudoku solving query
    result = backend.execute(
        sudoku_sql,
        params=(sudoku_input,),
        options=ExecutionOptions(stmt_type=StatementType.DQL)  # Use DQL to ensure result set is processed
    )

    # Verify the result
    assert result is not None
    assert result.data is not None
    assert len(result.data) >= 1  # Should return at least one row

    solution = result.data[0]['s']
    assert solution is not None
    assert len(solution) == 81  # Sudoku solution should be 81 characters

    # Verify the solution content
    expected_solution = "534678912672195348198342567859761423426853791713924856961537284287419635345286179"
    assert solution == expected_solution

    print(f"Sudoku solution: {solution}")

    # Format and print the Sudoku solution
    print("\nFormatted Sudoku solution:")
    for i in range(9):
        row = solution[i*9:(i+1)*9]
        formatted_row = " ".join(list(row))
        print(formatted_row)


@pytest.mark.benchmark
@pytest.mark.skipif(
    sys.version_info < (3, 8) or sqlite3.sqlite_version_info < (3, 8, 3),
    reason="Recursive CTEs require Python 3.8+ and SQLite 3.8.3+"
)
def test_sudoku_solver_with_different_puzzle(sqlite_backend):
    """
    Test Sudoku solver with a different puzzle
    """
    backend = sqlite_backend

    # Another Sudoku input (more challenging puzzle)
    sudoku_input = '8..........36......7..9.2...5...7.......457.....1...3...1....68..85...1..9....4..'

    # Sudoku solving SQL
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

    # Execute the Sudoku solving query
    result = backend.execute(
        sudoku_sql,
        params=(sudoku_input,),
        options=ExecutionOptions(stmt_type=StatementType.DQL)
    )

    # Verify the result exists
    assert result is not None
    assert result.data is not None
    assert len(result.data) >= 1  # Should return at least one row

    solution = result.data[0]['s']
    assert solution is not None
    assert len(solution) == 81  # Sudoku solution should be 81 characters

    print(f"Second Sudoku solution: {solution}")


@pytest.mark.skipif(
    sys.version_info < (3, 8) or sqlite3.sqlite_version_info < (3, 8, 3),
    reason="Recursive CTEs require Python 3.8+ and SQLite 3.8.3+"
)
def test_sudoku_solver_validates_solution(sqlite_backend):
    """
    Test that the Sudoku solver generates a valid solution
    """
    backend = sqlite_backend

    # Simple Sudoku input
    sudoku_input = '53..7....6..195....98....6.8...6...34..8.3..17...2...6.6....28....419..5....8..79'

    # Sudoku solving SQL
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

    # Execute the Sudoku solving query
    result = backend.execute(
        sudoku_sql,
        params=(sudoku_input,),
        options=ExecutionOptions(stmt_type=StatementType.DQL)
    )

    solution = result.data[0]['s']
    
    # Verify solution validity
    assert len(solution) == 81
    
    # Check that solution contains no empty cells (dots)
    assert '.' not in solution
    
    # Check that solution contains only digits 1-9
    for char in solution:
        assert char.isdigit() and 1 <= int(char) <= 9
    
    # Validate row, column, and box rules
    _validate_sudoku_solution(solution)


def _validate_sudoku_solution(solution):
    """
    Validates that a Sudoku solution follows the rules
    """
    # Convert string to 9x9 grid
    grid = []
    for i in range(9):
        row = []
        for j in range(9):
            row.append(int(solution[i*9 + j]))
        grid.append(row)

    # Validate each row
    for i in range(9):
        row = grid[i]
        assert len(set(row)) == 9, f"Row {i} has duplicate values: {row}"

    # Validate each column
    for j in range(9):
        col = [grid[i][j] for i in range(9)]
        assert len(set(col)) == 9, f"Column {j} has duplicate values: {col}"

    # Validate each 3x3 box
    for box_row in range(3):
        for box_col in range(3):
            box = []
            for i in range(3):
                for j in range(3):
                    box.append(grid[box_row*3 + i][box_col*3 + j])
            assert len(set(box)) == 9, f"Box ({box_row},{box_col}) has duplicate values: {box}"


def test_sudoku_substring_function_expression(sqlite_backend):
    """
    Test SUBSTR function expression used in Sudoku solver
    """
    from rhosocial.activerecord.backend.expression import FunctionCall, Literal

    dialect = sqlite_backend.dialect

    # Test basic SUBSTR function call
    substr_expr = FunctionCall(dialect, "SUBSTR",
                              Literal(dialect, "HelloWorld"),
                              Literal(dialect, 1),
                              Literal(dialect, 5))
    sql, params = substr_expr.to_sql()

    assert "SUBSTR(" in sql
    assert params == ("HelloWorld", 1, 5)
    print(f"SUBSTR expression: {sql} with params {params}")


def test_sudoku_instr_function_expression(sqlite_backend):
    """
    Test INSTR function expression used in Sudoku solver
    """
    from rhosocial.activerecord.backend.expression import FunctionCall, Literal

    dialect = sqlite_backend.dialect

    # Test basic INSTR function call
    instr_expr = FunctionCall(dialect, "INSTR",
                             Literal(dialect, "HelloWorld"),
                             Literal(dialect, "o"))
    sql, params = instr_expr.to_sql()

    assert "INSTR(" in sql
    assert params == ("HelloWorld", "o")
    print(f"INSTR expression: {sql} with params {params}")


def test_sudoku_modulo_division_expression(sqlite_backend):
    """
    Test modulo and division expressions used in Sudoku solver
    """
    from rhosocial.activerecord.backend.expression import Column, Literal

    dialect = sqlite_backend.dialect

    # Test division: (ind-1)/9
    ind_col = Column(dialect, "ind", table="x")
    div_expr = (ind_col - Literal(dialect, 1)) / Literal(dialect, 9)  # Uses BinaryArithmeticExpression internally
    sql, params = div_expr.to_sql()

    assert "/" in sql
    assert params == (1, 9)
    print(f"Division expression: {sql} with params {params}")

    # Test modulo: ((ind-1)%9)
    mod_expr = (ind_col - Literal(dialect, 1)) % Literal(dialect, 9)  # Uses BinaryArithmeticExpression internally
    sql, params = mod_expr.to_sql()

    assert "%" in sql
    assert params == (1, 9)
    print(f"Modulo expression: {sql} with params {params}")


def test_sudoku_complex_arithmetic_expression(sqlite_backend):
    """
    Test complex arithmetic expressions used in Sudoku solver
    """
    from rhosocial.activerecord.backend.expression import Column, Literal

    dialect = sqlite_backend.dialect

    # Test complex expression: ((ind-1)/9)*9 + lp
    ind_col = Column(dialect, "ind", table="x")
    lp_col = Column(dialect, "lp", table="lp")

    # Build: ((ind-1)/9)*9 + lp
    inner_calc = (ind_col - Literal(dialect, 1)) / Literal(dialect, 9)
    mult_calc = inner_calc * Literal(dialect, 9)
    final_calc = mult_calc + lp_col

    sql, params = final_calc.to_sql()

    # Verify the expression contains the expected operations
    assert "+" in sql
    assert "*" in sql
    assert "/" in sql
    assert params == (1, 9, 9) + ()  # lp_col doesn't add params since it's a column
    print(f"Complex arithmetic expression: {sql} with params {params}")


def test_sudoku_exists_expression(sqlite_backend):
    """
    Test EXISTS expression used in Sudoku solver
    """
    from rhosocial.activerecord.backend.expression import (
        Column, Literal, FunctionCall, QueryExpression, TableExpression, ExistsExpression
    )

    dialect = sqlite_backend.dialect

    # Create a subquery for the EXISTS clause
    subquery = QueryExpression(
        dialect,
        select=[Literal(dialect, 1)],  # SELECT 1
        from_=TableExpression(dialect, "digits", alias="lp"),
        where=(Column(dialect, "z", table="z") == FunctionCall(dialect, "SUBSTR",
                                                              Column(dialect, "s", table="x"),
                                                              Literal(dialect, 1)))
    )

    exists_expr = ExistsExpression(dialect, subquery)
    sql, params = exists_expr.to_sql()

    assert "EXISTS" in sql.upper()
    # From the literals in the subquery: 1 from SELECT clause, 1 from WHERE clause
    assert params == (1, 1)
    print(f"EXISTS expression: {sql} with params {params}")


def test_sudoku_not_exists_expression(sqlite_backend):
    """
    Test NOT EXISTS expression used in Sudoku solver
    """
    from rhosocial.activerecord.backend.expression import (
        Literal, QueryExpression, TableExpression, ExistsExpression, LogicalPredicate
    )

    dialect = sqlite_backend.dialect

    # Create a subquery for the NOT EXISTS clause
    subquery = QueryExpression(
        dialect,
        select=[Literal(dialect, 1)],  # SELECT 1
        from_=TableExpression(dialect, "digits", alias="lp")
    )

    # Create EXISTS expression and negate it with NOT
    exists_expr = ExistsExpression(dialect, subquery)
    not_exists_expr = LogicalPredicate(dialect, "NOT", exists_expr)

    sql, params = not_exists_expr.to_sql()

    assert "NOT" in sql.upper()
    assert "EXISTS" in sql.upper()
    print(f"NOT EXISTS expression: {sql} with params {params}")


def test_sudoku_full_cte_expression(sqlite_backend):
    """
    Test full Sudoku solver using expression system - verify expression building
    """
    from rhosocial.activerecord.backend.expression import (
        Literal, ValuesExpression, QueryExpression, TableExpression, Column, FunctionCall,
        CTEExpression, WithQueryExpression, SetOperationExpression, CastExpression, concat_op
    )

    backend = sqlite_backend

    print("\n--- Building Sudoku Solver SQL with Expression System ---")

    dialect = backend.dialect

    # Define the Sudoku input
    sudoku_input = '53..7....6..195....98....6.8...6...34..8.3..17...2...6.6....28....419..5....8..79'

    print(f"Sudoku input: {sudoku_input}")

    # Build the input CTE: input(sud) AS (VALUES(?))
    input_cte = CTEExpression(
        dialect=dialect,
        name="input",
        query=ValuesExpression(
            dialect=dialect,
            values=[(sudoku_input,)],
            alias=None,  # No alias to avoid extra parentheses
            column_names=None  # No column names in VALUES, but specified in CTE
        ),
        columns=["sud"]
    )

    # Build the digits CTE: digits(z, lp) AS (VALUES('1', 1) UNION ALL SELECT CAST(lp+1 AS TEXT), lp+1 FROM digits WHERE lp<9)
    # Initial value part
    initial_digits_values = ValuesExpression(
        dialect=dialect,
        values=[('1', 1)],
        alias=None,
        column_names=None
    )

    # Recursive part
    digits_table = TableExpression(dialect, "digits")
    lp_column = Column(dialect, "lp", table="digits")

    # SELECT CAST(lp+1 AS TEXT), lp+1 FROM digits WHERE lp<9
    cast_expr = CastExpression(dialect, lp_column + Literal(dialect, 1), "TEXT")
    lp_plus_one = lp_column + Literal(dialect, 1)

    recursive_query = QueryExpression(
        dialect=dialect,
        select=[cast_expr, lp_plus_one],
        from_=digits_table,
        where=(lp_column < Literal(dialect, 9))
    )

    # Use SetOperationExpression to build the UNION ALL
    digits_union = SetOperationExpression(
        dialect=dialect,
        left=initial_digits_values,
        right=recursive_query,
        operation="UNION",
        all_=True,
        alias=None
    )

    digits_cte = CTEExpression(
        dialect=dialect,
        name="digits",
        query=digits_union,
        columns=["z", "lp"]
    )

    # Build the x CTE: x(s, ind) AS (SELECT sud, instr(sud, '.') FROM input UNION ALL ...)
    # Initial part
    input_table = TableExpression(dialect, "input")
    sud_column = Column(dialect, "sud", table="input")
    instr_call = FunctionCall(dialect, "INSTR", sud_column, Literal(dialect, '.'))

    initial_x_query = QueryExpression(
        dialect=dialect,
        select=[sud_column, instr_call],
        from_=input_table
    )

    # Recursive part - simplified for demonstration
    x_table = TableExpression(dialect, "x")
    s_column = Column(dialect, "s", table="x")
    ind_column = Column(dialect, "ind", table="x")
    z_column = Column(dialect, "z", table="z")

    # Build the complex string concatenation: substr(s, 1, ind-1) || z || substr(s, ind+1)
    substr1 = FunctionCall(dialect, "SUBSTR", s_column, Literal(dialect, 1), ind_column - Literal(dialect, 1))
    substr2 = FunctionCall(dialect, "SUBSTR", s_column, ind_column + Literal(dialect, 1))
    new_string_expr = concat_op(dialect, substr1, z_column, substr2)

    # New instr call for the concatenated string
    new_instr_call = FunctionCall(dialect, "INSTR", new_string_expr, Literal(dialect, '.'))

    # Build the NOT EXISTS subquery
    from rhosocial.activerecord.backend.expression import QueryExpression, TableExpression, Column, Literal, FunctionCall
    from rhosocial.activerecord.backend.expression.advanced_functions import ExistsExpression

    # Subquery for NOT EXISTS: SELECT 1 FROM digits AS lp WHERE ...
    lp_table = TableExpression(dialect, "digits", alias="lp")
    z_z_column = Column(dialect, "z", table="z")  # From outer query
    s_column_outer = Column(dialect, "s", table="x")  # From outer query
    ind_column_outer = Column(dialect, "ind", table="x")  # From outer query
    lp_column_sub = Column(dialect, "lp", table="lp")  # From subquery

    # Build the three conditions for the NOT EXISTS subquery
    # Condition 1: z.z = substr(s, ((ind-1)/9)*9 + lp, 1)
    cond1_calc1 = ((ind_column_outer - Literal(dialect, 1)) / Literal(dialect, 9)) * Literal(dialect, 9)
    cond1_calc2 = cond1_calc1 + lp_column_sub
    cond1 = z_z_column == FunctionCall(dialect, "SUBSTR", s_column_outer, cond1_calc2, Literal(dialect, 1))

    # Condition 2: z.z = substr(s, ((ind-1)%9) + (lp-1)*9 + 1, 1)
    cond2_calc1 = (ind_column_outer - Literal(dialect, 1)) % Literal(dialect, 9)
    cond2_calc2 = (lp_column_sub - Literal(dialect, 1)) * Literal(dialect, 9)
    cond2_calc3 = cond2_calc1 + cond2_calc2 + Literal(dialect, 1)
    cond2 = z_z_column == FunctionCall(dialect, "SUBSTR", s_column_outer, cond2_calc3, Literal(dialect, 1))

    # Condition 3: z.z = substr(s, (((ind-1)/3) % 3) * 3 + ((ind-1)/27) * 27 + lp + ((lp-1) / 3) * 6, 1)
    cond3_calc1 = (((ind_column_outer - Literal(dialect, 1)) / Literal(dialect, 3)) % Literal(dialect, 3)) * Literal(dialect, 3)
    cond3_calc2 = ((ind_column_outer - Literal(dialect, 1)) / Literal(dialect, 27)) * Literal(dialect, 27)
    cond3_calc3 = (lp_column_sub - Literal(dialect, 1)) / Literal(dialect, 3)
    cond3_calc4 = cond3_calc3 * Literal(dialect, 6)
    cond3_calc5 = cond3_calc1 + cond3_calc2 + lp_column_sub + cond3_calc4
    cond3 = z_z_column == FunctionCall(dialect, "SUBSTR", s_column_outer, cond3_calc5, Literal(dialect, 1))

    # Combine conditions with OR
    subquery_where = cond1 | cond2 | cond3

    # Create the subquery for NOT EXISTS
    not_exists_subquery = QueryExpression(
        dialect=dialect,
        select=[Literal(dialect, 1)],  # SELECT 1
        from_=lp_table,
        where=subquery_where
    )

    # Create the NOT EXISTS expression
    not_exists_expr = ExistsExpression(dialect, not_exists_subquery, is_not=True)

    # FROM x, digits AS z (cross join using list)
    from_clause = [x_table, TableExpression(dialect, "digits", alias="z")]

    recursive_x_query = QueryExpression(
        dialect=dialect,
        select=[new_string_expr, new_instr_call],
        from_=from_clause,  # Cross join
        where=(ind_column > Literal(dialect, 0)) & not_exists_expr  # Add the NOT EXISTS constraint
    )

    # Use SetOperationExpression to build the UNION ALL for x CTE
    x_union = SetOperationExpression(
        dialect=dialect,
        left=initial_x_query,
        right=recursive_x_query,
        operation="UNION",
        all_=True,
        alias=None
    )

    x_cte = CTEExpression(
        dialect=dialect,
        name="x",
        query=x_union,
        columns=["s", "ind"]
    )

    # Final query: SELECT s FROM x WHERE ind=0
    final_query = QueryExpression(
        dialect=dialect,
        select=[Column(dialect, "s")],
        from_=TableExpression(dialect, "x"),
        where=(Column(dialect, "ind") == Literal(dialect, 0))
    )

    # Build the complete WITH query
    with_query = WithQueryExpression(
        dialect=dialect,
        ctes=[input_cte, digits_cte, x_cte],  # input, digits, and x CTEs
        main_query=final_query,
        recursive=True
    )

    # Generate the final SQL
    sql, params = with_query.to_sql()

    print(f"Generated Sudoku SQL: {sql}")
    print(f"Parameters: {params}")

    # Verify the generated SQL structure
    assert "WITH" in sql.upper()
    assert "RECURSIVE" in sql.upper()
    assert "input" in sql
    assert "digits" in sql
    assert "x" in sql
    assert "||" in sql  # Concatenation operator
    assert "SUBSTR" in sql.upper()  # SUBSTR function
    assert "INSTR" in sql.upper()  # INSTR function
    assert "CAST" in sql.upper()  # CAST function

    print("✓ Generated SQL has correct structure")

    # Execute the generated SQL
    print("\n--- Attempting to execute generated Sudoku SQL ---")
    from rhosocial.activerecord.backend.options import ExecutionOptions
    from rhosocial.activerecord.backend.schema import StatementType

    result = backend.execute(
        sql,
        params=params,
        options=ExecutionOptions(stmt_type=StatementType.DQL)  # Use DQL to ensure result set is processed
    )

    # Check if we got a result
    assert result is not None
    assert result.data is not None
    assert len(result.data) >= 1

    solution = result.data[0]['s']
    print(f"Generated SQL Sudoku solution: {solution}")

    # Verify the solution content
    expected_solution = "534678912672195348198342567859761423426853791713924856961537284287419635345286179"
    assert solution == expected_solution
    print("✓ Generated SQL produced correct Sudoku solution")

    # For this test, we'll verify that the expression system can build the components
    # The full Sudoku logic is too complex to execute in a unit test
    # We just verify that the expression building works without throwing errors
    assert sql is not None
    assert params is not None
    assert len(sql) > 0  # Generated SQL should not be empty


class TestMandelbrotSet:
    """Tests for Mandelbrot Set generation using recursive CTEs."""

    @pytest.mark.skipif(
        sys.version_info < (3, 8) or sqlite3.sqlite_version_info < (3, 8, 3),
        reason="Recursive CTEs require Python 3.8+ and SQLite 3.8.3+"
    )
    def test_mandelbrot_set_raw_sql(self, sqlite_backend):
        """
        Test Mandelbrot Set generation using raw SQL.
        This test executes the complete Mandelbrot Set SQL query to verify it produces the correct visualization.
        """
        backend = sqlite_backend

        # Create a test table to ensure the backend is working
        backend.execute(
            "CREATE TABLE temp_test (id INTEGER PRIMARY KEY, name TEXT)",
            options=ExecutionOptions(stmt_type=StatementType.DDL)
        )

        print("\n--- Building and Executing Mandelbrot Set SQL ---")

        # Complete Mandelbrot Set SQL query
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

        # Execute the Mandelbrot Set query
        result = backend.execute(
            mandelbrot_sql,
            params=(),
            options=ExecutionOptions(stmt_type=StatementType.DQL)  # Use DQL to ensure result set is processed
        )

        # Verify the result
        assert result is not None
        assert result.data is not None
        assert len(result.data) >= 1  # Should return at least one row

        visualization = result.data[0]
        # The result should have a single column (the name varies by implementation)
        # Get the first column value
        mandelbrot_output = next(iter(visualization.values()))

        assert mandelbrot_output is not None
        print(f"Mandelbrot Set visualization:\n{mandelbrot_output}")

        # Verify that the output contains Mandelbrot Set characteristics
        # The output should contain ASCII art representation with chars ' ', '.', '+', '*', '#'
        assert any(c in mandelbrot_output for c in [' ', '.', '+', '*', '#'])

        # Should have multiple lines (rows in the visualization)
        lines = mandelbrot_output.split('\n')
        assert len(lines) > 1

        print("✓ Mandelbrot Set visualization generated successfully")

    @pytest.mark.skipif(
        sys.version_info < (3, 8) or sqlite3.sqlite_version_info < (3, 8, 3),
        reason="Recursive CTEs require Python 3.8+ and SQLite 3.8.3+"
    )
    def test_mandelbrot_set_expression_system(self, sqlite_backend):
        """
        Test Mandelbrot Set generation using expression system.
        This test builds the Mandelbrot Set SQL using the expression system and verifies it produces the same result as raw SQL.
        """
        from rhosocial.activerecord.backend.expression import (
            Literal, ValuesExpression, QueryExpression, TableExpression, Column, FunctionCall,
            CTEExpression, WithQueryExpression, SetOperationExpression, CastExpression, concat_op
        )

        backend = sqlite_backend

        # Create a test table to ensure the backend is working
        backend.execute(
            "CREATE TABLE temp_test (id INTEGER PRIMARY KEY, name TEXT)",
            options=ExecutionOptions(stmt_type=StatementType.DDL)
        )

        print("\n--- Building Mandelbrot Set SQL with Expression System ---")

        dialect = backend.dialect

        # Build the xaxis CTE: xaxis(x) AS (VALUES(-2.0) UNION ALL SELECT x+0.05 FROM xaxis WHERE x<1.2)
        # Initial value part
        initial_xaxis_values = ValuesExpression(
            dialect=dialect,
            values=[(-2.0,)],
            alias=None,
            column_names=None
        )

        # Recursive part
        xaxis_table = TableExpression(dialect, "xaxis")
        x_col = Column(dialect, "x", table="xaxis")

        # SELECT x+0.05 FROM xaxis WHERE x<1.2
        x_plus_increment = x_col + Literal(dialect, 0.05)

        recursive_xaxis_query = QueryExpression(
            dialect=dialect,
            select=[x_plus_increment],
            from_=xaxis_table,
            where=(x_col < Literal(dialect, 1.2))
        )

        # Use SetOperationExpression to build the UNION ALL
        xaxis_union = SetOperationExpression(
            dialect=dialect,
            left=initial_xaxis_values,
            right=recursive_xaxis_query,
            operation="UNION",
            all_=True,
            alias=None
        )

        xaxis_cte = CTEExpression(
            dialect=dialect,
            name="xaxis",
            query=xaxis_union,
            columns=["x"]
        )

        # Build the yaxis CTE: yaxis(y) AS (VALUES(-1.0) UNION ALL SELECT y+0.1 FROM yaxis WHERE y<1.0)
        # Initial value part
        initial_yaxis_values = ValuesExpression(
            dialect=dialect,
            values=[(-1.0,)],
            alias=None,
            column_names=None
        )

        # Recursive part
        yaxis_table = TableExpression(dialect, "yaxis")
        y_col = Column(dialect, "y", table="yaxis")

        # SELECT y+0.1 FROM yaxis WHERE y<1.0
        y_plus_increment = y_col + Literal(dialect, 0.1)

        recursive_yaxis_query = QueryExpression(
            dialect=dialect,
            select=[y_plus_increment],
            from_=yaxis_table,
            where=(y_col < Literal(dialect, 1.0))
        )

        # Use SetOperationExpression to build the UNION ALL
        yaxis_union = SetOperationExpression(
            dialect=dialect,
            left=initial_yaxis_values,
            right=recursive_yaxis_query,
            operation="UNION",
            all_=True,
            alias=None
        )

        yaxis_cte = CTEExpression(
            dialect=dialect,
            name="yaxis",
            query=yaxis_union,
            columns=["y"]
        )

        # Build the m CTE: m(iter, cx, cy, x, y) AS (
        #   SELECT 0, x, y, 0.0, 0.0 FROM xaxis, yaxis
        #   UNION ALL
        #   SELECT iter+1, cx, cy, x*x-y*y + cx, 2.0*x*y + cy FROM m
        #    WHERE (x*x + y*y) < 4.0 AND iter<28
        # )
        # Initial part: SELECT 0, x, y, 0.0, 0.0 FROM xaxis, yaxis
        initial_m_query = QueryExpression(
            dialect=dialect,
            select=[
                Literal(dialect, 0),  # iter
                Column(dialect, "x", table="xaxis"),  # cx
                Column(dialect, "y", table="yaxis"),  # cy
                Literal(dialect, 0.0),  # x
                Literal(dialect, 0.0)   # y
            ],
            from_=[TableExpression(dialect, "xaxis"), TableExpression(dialect, "yaxis")]  # Cross join
        )

        # Recursive part
        m_table = TableExpression(dialect, "m")
        iter_col = Column(dialect, "iter", table="m")
        cx_col = Column(dialect, "cx", table="m")
        cy_col = Column(dialect, "cy", table="m")
        x_m_col = Column(dialect, "x", table="m")
        y_m_col = Column(dialect, "y", table="m")

        # SELECT iter+1, cx, cy, x*x-y*y + cx, 2.0*x*y + cy FROM m WHERE (x*x + y*y) < 4.0 AND iter<28
        new_iter = iter_col + Literal(dialect, 1)
        new_x = (x_m_col * x_m_col - y_m_col * y_m_col) + cx_col
        new_y = Literal(dialect, 2.0) * x_m_col * y_m_col + cy_col

        condition1 = (x_m_col * x_m_col + y_m_col * y_m_col) < Literal(dialect, 4.0)
        condition2 = iter_col < Literal(dialect, 28)
        where_condition = condition1 & condition2

        recursive_m_query = QueryExpression(
            dialect=dialect,
            select=[new_iter, cx_col, cy_col, new_x, new_y],
            from_=m_table,
            where=where_condition
        )

        # Use SetOperationExpression to build the UNION ALL for m CTE
        m_union = SetOperationExpression(
            dialect=dialect,
            left=initial_m_query,
            right=recursive_m_query,
            operation="UNION",
            all_=True,
            alias=None
        )

        m_cte = CTEExpression(
            dialect=dialect,
            name="m",
            query=m_union,
            columns=["iter", "cx", "cy", "x", "y"]
        )

        # Build the m2 CTE: m2(iter, cx, cy) AS (
        #   SELECT max(iter), cx, cy FROM m GROUP BY cx, cy
        # )
        m2_from = TableExpression(dialect, "m")
        max_iter = FunctionCall(dialect, "MAX", Column(dialect, "iter", table="m"))
        m2_cx = Column(dialect, "cx", table="m")
        m2_cy = Column(dialect, "cy", table="m")

        from rhosocial.activerecord.backend.expression.query_parts import GroupByHavingClause
        m2_query = QueryExpression(
            dialect=dialect,
            select=[max_iter, m2_cx, m2_cy],
            from_=m2_from,
            group_by_having=GroupByHavingClause(
                dialect=dialect,
                group_by=[Column(dialect, "cx", table="m"), Column(dialect, "cy", table="m")],
                having=None
            )
        )

        m2_cte = CTEExpression(
            dialect=dialect,
            name="m2",
            query=m2_query,
            columns=["iter", "cx", "cy"]
        )

        # Build the a CTE: a(t) AS (
        #   SELECT group_concat( substr(' .+*#', 1+min(iter/7,4), 1), '')
        #   FROM m2 GROUP BY cy
        # )
        a_from = TableExpression(dialect, "m2")
        # substr(' .+*#', 1+min(iter/7,4), 1)
        substr_expr = FunctionCall(
            dialect, "SUBSTR",
            Literal(dialect, " .+*#"),
            Literal(dialect, 1) + FunctionCall(dialect, "MIN", Column(dialect, "iter", table="m2") / Literal(dialect, 7), Literal(dialect, 4)),
            Literal(dialect, 1)
        )
        group_concat_expr = FunctionCall(dialect, "GROUP_CONCAT", substr_expr, Literal(dialect, ''))

        a_query = QueryExpression(
            dialect=dialect,
            select=[group_concat_expr],
            from_=a_from,
            group_by_having=GroupByHavingClause(
                dialect=dialect,
                group_by=[Column(dialect, "cy", table="m2")],
                having=None
            )
        )

        a_cte = CTEExpression(
            dialect=dialect,
            name="a",
            query=a_query,
            columns=["t"]
        )

        # Final query: SELECT group_concat(rtrim(t),x'0a') FROM a
        final_from = TableExpression(dialect, "a")
        rtrim_expr = FunctionCall(dialect, "RTRIM", Column(dialect, "t", table="a"))
        final_group_concat = FunctionCall(dialect, "GROUP_CONCAT", rtrim_expr, Literal(dialect, "\n"))  # Using \n instead of x'0a'

        final_query = QueryExpression(
            dialect=dialect,
            select=[final_group_concat],
            from_=final_from
        )

        # Build the complete WITH query
        with_query = WithQueryExpression(
            dialect=dialect,
            ctes=[xaxis_cte, yaxis_cte, m_cte, m2_cte, a_cte],
            main_query=final_query
        )

        # Generate the final SQL
        sql, params = with_query.to_sql()

        print(f"Generated Mandelbrot SQL: {sql}")
        print(f"Parameters: {params}")

        # Execute the generated SQL
        result = backend.execute(
            sql,
            params=params,
            options=ExecutionOptions(stmt_type=StatementType.DQL)  # Use DQL to ensure result set is processed
        )

        # Verify the result
        assert result is not None
        assert result.data is not None
        assert len(result.data) >= 1  # Should return at least one row

        expression_result = result.data[0]
        expression_output = next(iter(expression_result.values()))

        print(f"Expression system Mandelbrot visualization:\n{expression_output}")

        # Now execute the raw SQL for comparison
        raw_mandelbrot_sql = """
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

        raw_result = backend.execute(
            raw_mandelbrot_sql,
            params=(),
            options=ExecutionOptions(stmt_type=StatementType.DQL)
        )

        raw_visualization = raw_result.data[0]
        raw_output = next(iter(raw_visualization.values()))

        # Compare the results
        assert expression_output == raw_output, f"Expression result differs from raw SQL:\nExpression: {expression_output}\nRaw SQL: {raw_output}"

        print("✓ Expression system produced identical Mandelbrot visualization as raw SQL")


if __name__ == "__main__":
    pytest.main([__file__])