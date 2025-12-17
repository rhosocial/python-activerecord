# src/rhosocial/activerecord/backend/expression_/__init__.py
"""
SQL Expression building blocks.
"""

from .bases import (
    ToSQLProtocol,
    BaseExpression,
    SQLValueExpression,
    SQLPredicate,
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
    Literal,
)
from .predicates import (
    ComparisonPredicate,
    LogicalPredicate,
    LikePredicate,
    InPredicate,
    BetweenPredicate,
    IsNullPredicate,
)
from .aggregates import (
    AggregatableExpression,
    AggregateFunctionCall,
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
from .functions import (
    count,
    sum_,
    avg,
    min_,
    max_,
    lower,
    upper,
    concat,
    coalesce,
)

__all__ = [
    "ToSQLProtocol", "BaseExpression", "SQLValueExpression", "SQLPredicate",
    "Identifier",
    "SQLOperation", "BinaryExpression", "UnaryExpression", "RawSQLExpression", "BinaryArithmeticExpression",
    "Column", "FunctionCall", "Subquery", "TableExpression", "Literal",
    "ComparisonPredicate", "LogicalPredicate", "LikePredicate", "InPredicate", "BetweenPredicate", "IsNullPredicate",
    "AggregatableExpression", "AggregateFunctionCall",
    "CaseExpression", "CastExpression", "ExistsExpression", "AnyExpression", "AllExpression",
    "WindowExpression", "JSONExpression", "ArrayExpression", "OrderedSetAggregation",
    "SetOperationExpression", "GroupingExpression", "GroupExpression", "JoinExpression", "CTEExpression",
    "WithQueryExpression", "ValuesExpression", "TableFunctionExpression", "LateralExpression",
    "JSONTableColumn", "JSONTableExpression",
    "QueryExpression", "DeleteExpression", "UpdateExpression", "InsertExpression", "ExplainExpression",
    "MergeActionType", "MergeAction", "MergeExpression",
    "GraphEdgeDirection", "GraphVertex", "GraphEdge", "MatchClause",
    "count", "sum_", "avg", "min_", "max_", "lower", "upper", "concat", "coalesce",
]