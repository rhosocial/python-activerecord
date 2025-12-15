# src/rhosocial/activerecord/backend/expression/__init__.py
"""
SQL Expression building blocks.
"""

from .base import (
    ToSQLProtocol,
    BaseExpression,
    SQLValueExpression,
    SQLPredicate,
    ComparableExpression,
    StringExpression,
    Literal,
)

from .literals import (
    Identifier,
)

from .operators import (
    SQLOperation,
    BinaryExpression,
    UnaryExpression,
    RawSQLExpression,
    BinaryArithmeticExpression,
)

from .core import (
    Column,
    FunctionCall,
    Subquery,
    TableExpression,
)

from .predicates import (
    ComparisonPredicate,
    LogicalPredicate,
    LikePredicate,
    InPredicate,
    BetweenPredicate,
    IsNullPredicate,
)

from .advanced_functions import (
    CaseExpression,
    CastExpression,
    ExistsExpression,
    AnyExpression,
    AllExpression,
    WindowExpression,
    JSONExpression,
    ArrayExpression,
    OrderedSetAggregation,
)

from .query_clauses import (
    SetOperationExpression,
    GroupingExpression,
    GroupExpression,
    JoinExpression,
    CTEExpression,
    WithQueryExpression,
    ValuesExpression,
    TableFunctionExpression,
    LateralExpression,
    JSONTableColumn,
    JSONTableExpression,
)

from .statements import (
    QueryExpression,
    DeleteExpression,
    UpdateExpression,
    InsertExpression,
    ExplainExpression,
    MergeActionType,
    MergeAction,
    MergeExpression,
)

from .graph import (
    GraphEdgeDirection,
    GraphVertex,
    GraphEdge,
    MatchClause,
)

__all__ = [
    # base.py
    "ToSQLProtocol",
    "BaseExpression",
    "SQLValueExpression",
    "SQLPredicate",
    "ComparableExpression",
    "StringExpression",
    "Literal",

    # literals.py
    "Identifier",

    # operators.py
    "SQLOperation",
    "BinaryExpression",
    "UnaryExpression",
    "RawSQLExpression",
    "BinaryArithmeticExpression",

    # core.py
    "Column",
    "FunctionCall",
    "Subquery",
    "TableExpression",

    # predicates.py
    "ComparisonPredicate",
    "LogicalPredicate",
    "LikePredicate",
    "InPredicate",
    "BetweenPredicate",
    "IsNullPredicate",

    # advanced_functions.py
    "CaseExpression",
    "CastExpression",
    "ExistsExpression",
    "AnyExpression",
    "AllExpression",
    "WindowExpression",
    "JSONExpression",
    "ArrayExpression",
    "OrderedSetAggregation",

    # query_clauses.py
    "SetOperationExpression",
    "GroupingExpression",
    "GroupExpression",
    "JoinExpression",
    "CTEExpression",
    "WithQueryExpression",
    "ValuesExpression",
    "TableFunctionExpression",
    "LateralExpression",
    "JSONTableColumn",
    "JSONTableExpression",

    # statements.py
    "QueryExpression",
    "DeleteExpression",
    "UpdateExpression",
    "InsertExpression",
    "ExplainExpression",
    "MergeActionType",
    "MergeAction",
    "MergeExpression",

    # graph.py
    "GraphEdgeDirection",
    "GraphVertex",
    "GraphEdge",
    "MatchClause",
]
