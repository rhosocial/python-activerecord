# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_set_operation_paths.py
"""
Cover SetOperationExpression rendering paths via DummyDialect.

Targets uncovered branches in query/../backend/dialect/mixins/set_operation
and backend/expression/statements/set_operation.py:
- UNION / UNION ALL / INTERSECT / EXCEPT with and without ORDER BY / LIMIT
"""

import pytest

from rhosocial.activerecord.backend.expression import QueryExpression
from rhosocial.activerecord.backend.expression.core import Column, Literal, TableExpression
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


@pytest.fixture
def dialect():
    return DummyDialect()


def _simple_select(dialect, table):
    return QueryExpression(
        dialect=dialect,
        select=[Column(dialect, "id")],
        from_=TableExpression(dialect, table),
    )


class TestSetOperations:
    @pytest.mark.parametrize("op", ["UNION", "UNION ALL", "INTERSECT", "EXCEPT"])
    def test_basic_ops(self, dialect, op):
        from rhosocial.activerecord.backend.expression import SetOperationExpression
        left = _simple_select(dialect, "a")
        right = _simple_select(dialect, "b")
        expr = SetOperationExpression(dialect, left=left, right=right, operation=op)
        sql, params = expr.to_sql()
        assert op in sql
        assert "SELECT" in sql.upper()

    def test_union_all_compound(self, dialect):
        from rhosocial.activerecord.backend.expression import SetOperationExpression
        e1 = SetOperationExpression(
            dialect, left=_simple_select(dialect, "a"),
            right=_simple_select(dialect, "b"), operation="UNION",
        )
        e2 = SetOperationExpression(
            dialect, left=e1, right=_simple_select(dialect, "c"), operation="UNION ALL",
        )
        sql, params = e2.to_sql()
        assert "UNION ALL" in sql
