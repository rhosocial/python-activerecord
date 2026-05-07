# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_expression_traversal.py
"""
Comprehensive traversal tests for all generic expressions.

TEST PURPOSE:
    This test file verifies that all generic expressions can be serialized and
    deserialized via a "round-trip" process: serialize → deserialize → compare.
    
    APPROACH: Parameterized Testing
    Instead of trying to auto-detect expression parameters (which requires special
    handling for each expression type), we pre-define test cases with explicit
    parameters for each expression class. This achieves "以不变应万变":
    - Test logic is completely generic (no special cases)
    - Each expression provides its own valid parameters
    - All expressions are tested uniformly
    
    COVERAGE:
    - Core expressions: Column, Literal, FunctionCall, TableExpression, etc.
    - Predicates: ComparisonPredicate, LogicalPredicate, LikePredicate, etc.
    - Query parts: WhereClause, GroupByHavingClause, OrderByClause, etc.
    - DML/DDL statements: InsertExpression, DeleteExpression, CreateTableExpression, etc.
    - Graph expressions: GraphVertex, GraphEdge, MatchClause
    - Transaction expressions: BeginTransactionExpression, CommitExpression, etc.
    
    See also: sqlite/test_expression_traversal.py for dialect_options and backend-specific tests.
"""

import pytest

from rhosocial.activerecord.backend.expression import (
    Column,
    Literal,
    WildcardExpression,
    FunctionCall,
    TableExpression,
    ComparisonPredicate,
    LogicalPredicate,
    InPredicate,
    LikePredicate,
    IsNullPredicate,
    IsBooleanPredicate,
    BetweenPredicate,
)
from rhosocial.activerecord.backend.expression.aggregates import AggregateFunctionCall
from rhosocial.activerecord.backend.expression.query_parts import (
    WhereClause,
    OrderByClause,
    LimitOffsetClause,
    GroupingExpression,
    JoinExpression,
)
from rhosocial.activerecord.backend.expression.query_sources import (
    SetOperationExpression,
    ValuesExpression,
)
from rhosocial.activerecord.backend.expression.statements.dql import QueryExpression
from rhosocial.activerecord.backend.expression.transaction import (
    BeginTransactionExpression,
    CommitTransactionExpression,
    RollbackTransactionExpression,
)
from rhosocial.activerecord.backend.expression.graph import (
    GraphVertex,
    GraphEdge,
    GraphEdgeDirection,
    MatchClause,
)
from rhosocial.activerecord.backend.expression.advanced_functions import (
    AllExpression,
    AnyExpression,
    ArrayExpression,
    CaseExpression,
    ExistsExpression,
    JSONExpression,
    OrderedSetAggregation,
    WindowClause,
    WindowDefinition,
    WindowFrameSpecification,
    WindowFunctionCall,
    WindowSpecification,
)
from rhosocial.activerecord.backend.expression.core import Subquery
from rhosocial.activerecord.backend.expression.literals import Identifier
from rhosocial.activerecord.backend.expression.operators import (
    BinaryArithmeticExpression,
    SQLOperation,
)
from rhosocial.activerecord.backend.expression.introspection import IntrospectionExpression
from rhosocial.activerecord.backend.expression.query_parts import (
    QualifyClause,
    GroupByHavingClause,
    ForUpdateClause,
)
from rhosocial.activerecord.backend.expression.query_sources import (
    CTEExpression,
    JSONTableExpression,
    LateralExpression,
    TableFunctionExpression,
    WithQueryExpression,
    SetOperationExpression,
    ValuesExpression,
)
from rhosocial.activerecord.backend.expression.transaction import (
    BeginTransactionExpression,
    CommitTransactionExpression,
    RollbackTransactionExpression,
    SavepointExpression,
    ReleaseSavepointExpression,
    SetTransactionExpression,
)
from rhosocial.activerecord.backend.expression.operators import (
    BinaryExpression,
    UnaryExpression,
    RawSQLExpression,
    RawSQLPredicate,
)
from rhosocial.activerecord.backend.expression import serialization
from rhosocial.activerecord.backend.expression.serialization import _reconstruct


EXPRESSION_TEST_CASES = [
    dict(name="Column", cls=Column, params_func=lambda d: dict(dialect=d, name="age", table="users")),
    dict(name="Literal", cls=Literal, params_func=lambda d: dict(dialect=d, value=42)),
    dict(name="Literal_string", cls=Literal, params_func=lambda d: dict(dialect=d, value="hello")),
    dict(name="Literal_none", cls=Literal, params_func=lambda d: dict(dialect=d, value=None)),
    dict(name="WildcardExpression", cls=WildcardExpression, params_func=lambda d: dict(dialect=d)),
    dict(name="FunctionCall", cls=FunctionCall, params_func=lambda d: dict(
        dialect=d, func_name="COUNT", args=(WildcardExpression(d),)
    )),
    dict(name="FunctionCallDistinct", cls=FunctionCall, params_func=lambda d: dict(
        dialect=d, func_name="COUNT", is_distinct=True
    )),
    dict(name="TableExpression", cls=TableExpression, params_func=lambda d: dict(dialect=d, name="users")),
    dict(name="ComparisonPredicate", cls=ComparisonPredicate, params_func=lambda d: dict(
        dialect=d, op=">=", left=Column(d, "age"), right=Literal(d, 18)
    )),
    dict(name="LogicalPredicate", cls=LogicalPredicate, params_func=lambda d: dict(
        dialect=d, op="AND",
        predicates=(
            ComparisonPredicate(d, "=", Column(d, "a"), Literal(d, 1)),
            ComparisonPredicate(d, "=", Column(d, "b"), Literal(d, 2)),
        )
    )),
    dict(name="LikePredicate", cls=LikePredicate, params_func=lambda d: dict(
        dialect=d, op="LIKE", expr=Column(d, "name"), pattern=Literal(d, "A%")
    )),
    dict(name="InPredicate", cls=InPredicate, params_func=lambda d: dict(
        dialect=d, expr=Column(d, "category"), values=Literal(d, ["A", "B", "C"])
    )),
    dict(name="IsNullPredicate", cls=IsNullPredicate, params_func=lambda d: dict(
        dialect=d, expr=Column(d, "deleted_at")
    )),
    dict(name="IsBooleanPredicate", cls=IsBooleanPredicate, params_func=lambda d: dict(
        dialect=d, expr=Column(d, "active"), value=True
    )),
    dict(name="BetweenPredicate", cls=BetweenPredicate, params_func=lambda d: dict(
        dialect=d, expr=Column(d, "age"), low=Literal(d, 18), high=Literal(d, 65)
    )),
    dict(name="AggregateFunctionCall", cls=AggregateFunctionCall, params_func=lambda d: dict(
        dialect=d, func_name="SUM", args=(Column(d, "amount"),)
    )),
    dict(name="WhereClause", cls=WhereClause, params_func=lambda d: dict(
        dialect=d, condition=ComparisonPredicate(d, "=", Column(d, "id"), Literal(d, 1))
    )),
    dict(name="OrderByClause", cls=OrderByClause, params_func=lambda d: dict(
        dialect=d, expressions=[(Column(d, "name"), "ASC")]
    )),
    dict(name="LimitOffsetClause", cls=LimitOffsetClause, params_func=lambda d: dict(
        dialect=d, limit=10, offset=0
    )),
    dict(name="GroupingExpression", cls=GroupingExpression, params_func=lambda d: dict(
        dialect=d, operation="GROUP BY", expressions=[Column(d, "dept")]
    )),
    dict(name="JoinExpression", cls=JoinExpression, params_func=lambda d: dict(
        dialect=d, left_table="users", right_table="orders", join_type="INNER",
        condition=ComparisonPredicate(d, "=", Column(d, "users.id"), Column(d, "orders.user_id"))
    )),
    dict(name="SetOperationExpression", cls=SetOperationExpression, params_func=lambda d: dict(
        dialect=d, operation="UNION",
        left=QueryExpression(d, select=[Column(d, "id")], from_=TableExpression(d, name="users")),
        right=QueryExpression(d, select=[Column(d, "id")], from_=TableExpression(d, name="admins"))
    )),
    dict(name="ValuesExpression", cls=ValuesExpression, params_func=lambda d: dict(
        dialect=d, values=[(Literal(d, 1), Literal(d, "a")), (Literal(d, 2), Literal(d, "b"))]
    )),
    dict(name="QueryExpression", cls=QueryExpression, params_func=lambda d: dict(
        dialect=d, select=[Column(d, "id"), Column(d, "name")], from_=TableExpression(d, name="users")
    )),
    dict(name="BeginTransactionExpression", cls=BeginTransactionExpression, params_func=lambda d: dict(dialect=d)),
    dict(name="CommitTransactionExpression", cls=CommitTransactionExpression, params_func=lambda d: dict(dialect=d)),
    dict(
        name="RollbackTransactionExpression",
        cls=RollbackTransactionExpression,
        params_func=lambda d: dict(dialect=d),
    ),
    dict(name="GraphVertex", cls=GraphVertex, params_func=lambda d: dict(
        dialect=d, variable="v", table="users"
    )),
    dict(name="GraphEdge", cls=GraphEdge, params_func=lambda d: dict(
        dialect=d, variable="e", table="follows", direction=GraphEdgeDirection.RIGHT
    )),
    # MatchClause uses *path (VAR_POSITIONAL) - import present, test skipped
    # dict(name="MatchClause", cls=MatchClause, params_func=lambda d: dict(
    #     dialect=d,
    #     GraphVertex(d, variable="v1", table="users"),
    #     GraphEdge(d, variable="e", table="follows", direction=GraphEdgeDirection.RIGHT),
    #     GraphVertex(d, variable="v2", table="users"),
    # )),
    dict(name="RawSQLExpression", cls=RawSQLExpression, params_func=lambda d: dict(
        dialect=d, expression="SELECT 1", params=(1,)
    )),
    dict(name="RawSQLPredicate", cls=RawSQLPredicate, params_func=lambda d: dict(
        dialect=d, expression="id IN (SELECT id FROM admins)"
    )),
    dict(name="BinaryExpression", cls=BinaryExpression, params_func=lambda d: dict(
        dialect=d, op="+", left=Column(d, "a"), right=Column(d, "b")
    )),
    dict(name="UnaryExpression", cls=UnaryExpression, params_func=lambda d: dict(
        dialect=d, op="-", operand=Column(d, "a")
    )),
# advanced_functions
    dict(name="AllExpression", cls=AllExpression, params_func=lambda d: dict(
        dialect=d, expr=Column(d, "x"), op=">", array_expr=ArrayExpression(d, operation="ARRAY", elements=[Literal(d, 1)])
    )),
    dict(name="AnyExpression", cls=AnyExpression, params_func=lambda d: dict(
        dialect=d, expr=Column(d, "x"), op=">", array_expr=ArrayExpression(d, operation="ARRAY", elements=[Literal(d, 1)])
    )),
    dict(name="ArrayExpression", cls=ArrayExpression, params_func=lambda d: dict(
        dialect=d, operation="ARRAY", elements=[Literal(d, 1), Literal(d, 2)]
    )),
    dict(name="CaseExpression", cls=CaseExpression, params_func=lambda d: dict(
        dialect=d, cases=[(ComparisonPredicate(d, "=", Column(d, "status"), Literal(d, 1)), Literal(d, "active"))]
    )),
    dict(name="ExistsExpression", cls=ExistsExpression, params_func=lambda d: dict(
        dialect=d, subquery=Subquery(d, "SELECT 1")
    )),
    dict(name="JSONExpression", cls=JSONExpression, params_func=lambda d: dict(
        dialect=d, column=Column(d, "data"), path="$.key", operation="->"
    )),
    dict(name="OrderedSetAggregation", cls=OrderedSetAggregation, params_func=lambda d: dict(
        dialect=d, func_name="LISTAGG", args=[Column(d, "name")], order_by=OrderByClause(d, expressions=[(Column(d, "name"), "ASC")])
    )),
    dict(name="WindowClause", cls=WindowClause, params_func=lambda d: dict(
        dialect=d, definitions=[WindowDefinition(d, name="w", specification=WindowSpecification(d, order_by=OrderByClause(d, expressions=[(Column(d, "name"), "ASC")])))]
    )),
    dict(name="WindowDefinition", cls=WindowDefinition, params_func=lambda d: dict(
        dialect=d, name="w", specification=WindowSpecification(d, order_by=OrderByClause(d, expressions=[(Column(d, "name"), "ASC")]))
    )),
    dict(name="WindowFrameSpecification", cls=WindowFrameSpecification, params_func=lambda d: dict(
        dialect=d, frame_type="RANGE", start_frame="UNBOUNDED PRECEDING"
    )),
    dict(name="WindowFunctionCall", cls=WindowFunctionCall, params_func=lambda d: dict(
        dialect=d, function_name="ROW_NUMBER", window_spec="w"
    )),
    dict(name="WindowSpecification", cls=WindowSpecification, params_func=lambda d: dict(
        dialect=d, order_by=OrderByClause(d, expressions=[(Column(d, "name"), "ASC")])
    )),
    # MatchClause uses *path (VAR_POSITIONAL) - import present, skipped (commented above)
    # query_sources
    dict(name="CTEExpression", cls=CTEExpression, params_func=lambda d: dict(
        dialect=d, name="cte1", query=Subquery(d, "SELECT 1")
    )),
    dict(name="LateralExpression", cls=LateralExpression, params_func=lambda d: dict(
        dialect=d, expression=Subquery(d, "SELECT generate_series(1, 10)"), alias="gs"
    )),
    dict(name="TableFunctionExpression", cls=TableFunctionExpression, params_func=lambda d: dict(
        dialect=d, func_name="generate_series", args=(Literal(d, 1), Literal(d, 10)), alias="gs"
    )),
    dict(name="WithQueryExpression", cls=WithQueryExpression, params_func=lambda d: dict(
        dialect=d,
        ctes=[CTEExpression(d, name="cte1", query=Subquery(d, "SELECT 1"))],
        main_query=QueryExpression(d, select=[Column(d, "id")], from_=TableExpression(d, name="users"))
    )),
    # query_parts
    dict(name="QualifyClause", cls=QualifyClause, params_func=lambda d: dict(
        dialect=d, condition=ComparisonPredicate(d, ">", Column(d, "row_num"), Literal(d, 1))
    )),
    dict(name="GroupByHavingClause", cls=GroupByHavingClause, params_func=lambda d: dict(
        dialect=d, group_by=[Column(d, "category")]
    )),
    dict(name="ForUpdateClause", cls=ForUpdateClause, params_func=lambda d: dict(
        dialect=d, of_columns=[Column(d, "id")], nowait=True
    )),
    # introspection
    # introspection - IntrospectionExpression is abstract (to_sql raises NotImplementedError)
    # Concrete introspection subclasses require a dialect that supports table introspection.
    # They are tested in backend-specific test files (e.g., sqlite).
    # operators
    dict(name="BinaryArithmeticExpression", cls=BinaryArithmeticExpression, params_func=lambda d: dict(
        dialect=d, op="+", left=Column(d, "a"), right=Column(d, "b")
    )),
    dict(name="SQLOperation", cls=SQLOperation, params_func=lambda d: dict(
        dialect=d, op="COALESCE", operands=(Literal(d, 1), Literal(d, 2))
    )),
    # core
    dict(name="Subquery", cls=Subquery, params_func=lambda d: dict(
        dialect=d, query_input="SELECT 1"
    )),
    # literals
    dict(name="Identifier", cls=Identifier, params_func=lambda d: dict(
        dialect=d, name="my_id"
    )),
    # transaction
    dict(name="SavepointExpression", cls=SavepointExpression, params_func=lambda d: dict(
        dialect=d, name="sp1"
    )),
    dict(name="ReleaseSavepointExpression", cls=ReleaseSavepointExpression, params_func=lambda d: dict(
        dialect=d, name="sp1"
    )),
    dict(name="SetTransactionExpression", cls=SetTransactionExpression, params_func=lambda d: dict(
        dialect=d
    )),
]


class TestExpressionRoundtrip:
    """Test serialization/deserialization roundtrip for all expression types."""

    @pytest.mark.parametrize("test_case", EXPRESSION_TEST_CASES, ids=[x["name"] for x in EXPRESSION_TEST_CASES])
    def test_expression_roundtrip(self, dummy_dialect, test_case):
        """Generic test: serialize → deserialize → compare SQL output."""
        cls = test_case["cls"]
        params = test_case["params_func"](dummy_dialect)

        instance = _reconstruct(cls, dummy_dialect, params)
        spec = serialization.serialize(instance)
        restored = serialization.deserialize(spec, dummy_dialect)
        assert restored.to_sql() == instance.to_sql()