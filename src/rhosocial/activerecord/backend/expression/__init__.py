# src/rhosocial/activerecord/backend/expression/__init__.py
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
    WindowFrameSpecification,
    WindowSpecification,
    WindowDefinition,
    WindowClause,
    WindowFunctionCall,
    JSONExpression,
    ArrayExpression,
    OrderedSetAggregation,
)
from .query_parts import (
    GroupingExpression,
    JoinExpression,
    JoinType,
)

from .query_sources import (
    SetOperationExpression,
    CTEExpression,
    WithQueryExpression,
    ValuesExpression,
    TableFunctionExpression,
    LateralExpression,
    JSONTableColumn,
    JSONTableExpression,
)
from .query_parts import (
    WhereClause,
    GroupByHavingClause,
    LimitOffsetClause,
    OrderByClause,
    QualifyClause,
    ForUpdateClause  # Added ForUpdateClause which was mentioned in statements.py
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
    SelectModifier,
    ForUpdateClause,
    ExplainType,
    ExplainFormat,
    ExplainOptions,
    ReturningClause,
    # Insert Abstractions
    InsertDataSource,
    ValuesSource,
    SelectSource,
    DefaultValuesSource,
    OnConflictClause,
    # DDL Expressions
    ColumnDefinition,
    IndexDefinition,
    CreateTableExpression,
    DropTableExpression,
    CreateViewExpression,
    DropViewExpression,
    ViewOptions,
    ViewCheckOption,
    AlterTableAction,
    AddColumn,
    DropColumn,
    AlterTableExpression,
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
    "WindowFrameSpecification", "WindowSpecification", "WindowDefinition", "WindowClause", "WindowFunctionCall",
    "JSONExpression", "ArrayExpression", "OrderedSetAggregation",
    "SetOperationExpression", "GroupingExpression", "GroupExpression", "JoinExpression", "CTEExpression",
    "WithQueryExpression", "ValuesExpression", "TableFunctionExpression", "LateralExpression",
    "JSONTableColumn", "JSONTableExpression",
    "WhereClause", "GroupByHavingClause", "LimitOffsetClause",
    "QueryExpression", "DeleteExpression", "UpdateExpression", "InsertExpression", "ExplainExpression",
    "MergeActionType", "MergeAction", "MergeExpression", "SelectModifier", "ForUpdateClause",
    "ExplainType", "ExplainFormat", "ExplainOptions", "ReturningClause",
    "InsertDataSource", "ValuesSource", "SelectSource", "DefaultValuesSource", "OnConflictClause",
    "ColumnDefinition", "IndexDefinition", "CreateTableExpression", "DropTableExpression",
    "CreateViewExpression", "DropViewExpression", "ViewOptions", "ViewCheckOption",
    "AlterTableAction", "AddColumn", "DropColumn", "AlterColumn", "AddConstraint", "DropConstraint", "RenameObject", "AddIndex", "DropIndex", "AlterTableExpression",
    "GraphEdgeDirection", "GraphVertex", "GraphEdge", "MatchClause",
    "count", "sum_", "avg", "min_", "max_", "lower", "upper", "concat", "coalesce",
]