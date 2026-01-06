#!/usr/bin/env python
"""
Sudoku solver SQL example test using SQLite dialect
"""
import pytest
import sys
import sqlite3
from datetime import datetime

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
    sys.version_info < (3, 11) or sqlite3.sqlite_version_info < (3, 35),
    reason="Recursive CTEs require Python 3.11+ and SQLite 3.35+"
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


@pytest.mark.skipif(
    sys.version_info < (3, 11) or sqlite3.sqlite_version_info < (3, 35),
    reason="Recursive CTEs require Python 3.11+ and SQLite 3.35+"
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
    sys.version_info < (3, 11) or sqlite3.sqlite_version_info < (3, 35),
    reason="Recursive CTEs require Python 3.11+ and SQLite 3.35+"
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


if __name__ == "__main__":
    pytest.main([__file__])