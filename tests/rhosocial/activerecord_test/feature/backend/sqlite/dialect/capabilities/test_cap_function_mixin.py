# tests/rhosocial/activerecord_test/feature/backend/sqlite/dialect/capabilities/test_cap_function_mixin.py
"""Every SQLite function formatter has a surface test."""

from rhosocial.activerecord.backend.expression import Column, Literal
from rhosocial.activerecord.backend.expression.advanced_functions import (
    LpadFunction,
    RepeatFunction,
    RpadFunction,
)
from rhosocial.activerecord.backend.expression.core import FunctionCall
from rhosocial.activerecord.backend.expression.functions.math import (
    LogarithmFunction,
    TruncateFunction,
)
from rhosocial.activerecord.backend.expression.functions.string import (
    AsciiFunction,
    LeftFunction,
    PositionExpression,
    RightFunction,
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.expression.json import (
    SQLiteJsonExtractFunction,
)

DIALECT = SQLiteDialect(version=(3, 53, 0))


def test_repeat_lpad_rpad_formatters():
    repeat = RepeatFunction(DIALECT, Literal(DIALECT, "ab"), Literal(DIALECT, 2), alias="r")
    sql, params = repeat.to_sql()
    assert "REPLACE" in sql and "ZEROBLOB" in sql
    assert params == (2, "00", "ab")

    lpad = LpadFunction(
        DIALECT,
        Literal(DIALECT, "ab"),
        Literal(DIALECT, 4),
        Literal(DIALECT, "x"),
    )
    sql, _ = lpad.to_sql()
    assert "CASE" in sql and "SUBSTR" in sql

    rpad = RpadFunction(
        DIALECT,
        Literal(DIALECT, "ab"),
        Literal(DIALECT, 4),
        Literal(DIALECT, "x"),
        alias="r",
    )
    sql, params = rpad.to_sql()
    assert "SUBSTR" in sql
    assert params == ("ab", 4, "00", "x", 1, 4)


def test_format_function_call_rewrites_sqlite_spellings():
    ascii_call = FunctionCall(DIALECT, "ASCII", Literal(DIALECT, "x"))
    assert "UNICODE" in ascii_call.to_sql()[0]

    truncate_two = FunctionCall(DIALECT, "TRUNCATE", Literal(DIALECT, 1.234), Literal(DIALECT, 2))
    assert "POW" in truncate_two.to_sql()[0]

    truncate_one = FunctionCall(DIALECT, "TRUNCATE", Literal(DIALECT, 1.234))
    assert "TRUNC" in truncate_one.to_sql()[0]

    position = FunctionCall(DIALECT, "POSITION", Literal(DIALECT, "b"), Literal(DIALECT, "abc"))
    assert "INSTR" in position.to_sql()[0]

    left = FunctionCall(DIALECT, "LEFT", Literal(DIALECT, "abc"), Literal(DIALECT, 2))
    assert "SUBSTR" in left.to_sql()[0]

    right = FunctionCall(DIALECT, "RIGHT", Literal(DIALECT, "abc"), Literal(DIALECT, 2))
    assert "MAX" in right.to_sql()[0]

    log_call = FunctionCall(DIALECT, "LOG", Literal(DIALECT, 100), Literal(DIALECT, 10))
    assert "LOG" in log_call.to_sql()[0]

    passthrough = FunctionCall(DIALECT, "ABS", Literal(DIALECT, -1))
    assert passthrough.to_sql()[0].startswith("ABS(")


def test_dedicated_function_nodes_and_aliases():
    truncate = TruncateFunction(DIALECT, Literal(DIALECT, 1.234))
    assert "TRUNC" in truncate.to_sql()[0]

    truncate_precision = TruncateFunction(DIALECT, Literal(DIALECT, 1.234), Literal(DIALECT, 2))
    assert "POW" in truncate_precision.to_sql()[0]

    log_plain = LogarithmFunction(DIALECT, Literal(DIALECT, 100))
    assert "LOG" in log_plain.to_sql()[0]
    log_one = LogarithmFunction(DIALECT, Literal(DIALECT, 100))
    log_one.alias = "l"
    assert log_one.to_sql()[0].endswith('AS "l"')

    log_base = LogarithmFunction(DIALECT, Literal(DIALECT, 100), Literal(DIALECT, 10))
    log_base.alias = "l"
    sql, params = log_base.to_sql()
    assert params == (10, 100)

    ascii_expr = AsciiFunction(DIALECT, Literal(DIALECT, "x"))
    assert "UNICODE" in ascii_expr.to_sql()[0]

    position = PositionExpression(DIALECT, Literal(DIALECT, "abc"), Literal(DIALECT, "b"))
    assert "INSTR" in position.to_sql()[0]

    left = LeftFunction(DIALECT, Literal(DIALECT, "abc"), Literal(DIALECT, 2))
    assert "SUBSTR" in left.to_sql()[0]

    right = RightFunction(DIALECT, Literal(DIALECT, "abc"), Literal(DIALECT, 2))
    assert "MAX" in right.to_sql()[0]

    extract = SQLiteJsonExtractFunction(DIALECT, Column(DIALECT, "doc"), Literal(DIALECT, "$.a"))
    extract.alias = "j"
    sql, params = extract.to_sql()
    assert sql.endswith('AS "j"')
    assert params == ("$.a",)

    truncate.alias = "t"
    assert truncate.to_sql()[0].endswith('AS "t"')
    log_base.alias = None
    assert "LOG" in log_base.to_sql()[0]
    ascii_expr.alias = "a"
    assert ascii_expr.to_sql()[0].endswith('AS "a"')
    position.alias = "p"
    assert position.to_sql()[0].endswith('AS "p"')
    left.alias = "l"
    assert left.to_sql()[0].endswith('AS "l"')
    right.alias = "r"
    assert right.to_sql()[0].endswith('AS "r"')


def test_function_version_gate_branches():
    low = SQLiteDialect(version=(3, 8, 0))
    high = SQLiteDialect(version=(3, 53, 0))

    assert low._is_sqlite_function_supported("json_extract") is True
    assert low._is_sqlite_function_supported("unhex") is False
    assert high._is_sqlite_function_supported("unhex") is True
    assert low._is_sqlite_function_supported("json_build_object") is False
    assert (
        SQLiteDialect(version=(4, 0, 0))._is_sqlite_function_supported("json_build_object") is False
    )
