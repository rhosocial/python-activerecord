# tests/rhosocial/activerecord_test/feature/backend/dialect/test_table_function_columns.py
"""Table functions returning SETOF record need typed column aliases."""
import pytest

from rhosocial.activerecord.backend.dialect import LateralJoinMixin, SQLDialectBase
from rhosocial.activerecord.backend.dialect.mixins.expression import ExpressionMixin
from rhosocial.activerecord.backend.expression import Parameter
from rhosocial.activerecord.backend.expression.sources.query_sources import TableFunctionExpression


class JoinDialect(SQLDialectBase, LateralJoinMixin, ExpressionMixin):
    pass


def test_typed_column_aliases():
    d = JoinDialect()
    expr = TableFunctionExpression(
        d,
        "crosstab",
        Parameter(d, "SELECT ...", inline=True),
        alias="ct",
        column_names=["row", "category"],
        column_types=["int", "text"],
    )
    sql, params = expr.to_sql()
    assert sql == 'CROSSTAB(\'SELECT ...\') AS "ct"("row" int, "category" text)'
    assert params == ()


def test_untyped_columns_unchanged():
    d = JoinDialect()
    expr = TableFunctionExpression(
        d, "unnest", Parameter(d, "ARRAY[1,2]", inline=True),
        alias="n", column_names=["num"],
    )
    sql, _ = expr.to_sql()
    assert sql == 'UNNEST(\'ARRAY[1,2]\') AS "n"("num")'


def test_column_types_require_column_names():
    d = JoinDialect()
    with pytest.raises(ValueError, match="column_names"):
        TableFunctionExpression(
            d, "crosstab", Parameter(d, "x", inline=True), column_types=["int"]
        )


def test_mismatched_lengths_refused():
    d = JoinDialect()
    expr = TableFunctionExpression(
        d, "crosstab", Parameter(d, "x", inline=True),
        alias="ct", column_names=["a", "b"], column_types=["int"],
    )
    with pytest.raises(ValueError, match="same length"):
        expr.to_sql()


def test_unsafe_type_spelling_refused():
    d = JoinDialect()
    expr = TableFunctionExpression(
        d, "crosstab", Parameter(d, "x", inline=True),
        alias="ct", column_names=["a"], column_types=["int); DROP TABLE t;--"],
    )
    with pytest.raises(ValueError, match="Unsupported column type"):
        expr.to_sql()
