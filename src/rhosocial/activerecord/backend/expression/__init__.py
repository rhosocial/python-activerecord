# src/rhosocial/activerecord/backend/expression/__init__.py
"""
SQL Expression building blocks.

Architecture Principles:
- Expression classes implement the ToSQLProtocol and define how to generate SQL
- Each expression class must call its dialect's format_* methods instead of self-formatting
- Dialect classes are responsible for the actual SQL formatting and parameter handling
- Expression classes should never directly concatenate SQL strings; they should delegate to dialect
- This pattern ensures each dialect can customize formatting behavior while maintaining security
- The relationship: Expression.to_sql() -> Dialect.format_*() -> SQL string and parameters
"""

from .bases import (
    ToSQLProtocol,
    BaseExpression,
    SQLValueExpression,
    SQLPredicate,
    SQLQueryAndParams,
    is_sql_query_and_params,
)
from .mixins import AliasableMixin
from .literals import (
    Identifier,
)
from .operators import (
    SQLOperation,
    BinaryExpression,
    UnaryExpression,
    RawSQLExpression,
    RawSQLPredicate,
    BinaryArithmeticExpression,
)
from .core import (
    Column,
    FunctionCall,
    Subquery,
    TableExpression,
    Literal,
    WildcardExpression,
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
    WhereClause,
    GroupByHavingClause,
    OrderByClause,
    LimitOffsetClause,
    QualifyClause,
    ForUpdateClause,
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
    AlterColumn,
    AddConstraint,
    DropConstraint,
    RenameObject,
    AddIndex,
    DropIndex,
    AlterTableExpression,
    TruncateExpression,
)
from .graph import (
    GraphEdgeDirection,
    GraphVertex,
    GraphEdge,
    MatchClause,
)

# Import all function factories
from .functions import (
    # Aggregate function factories
    count, sum_, avg, min_, max_,
    # Scalar function factories
    concat, coalesce,
    # String function factories
    length, substring, trim, replace, initcap, left, right, lpad, rpad, reverse, strpos,
    # Math function factories
    abs_, round_, ceil, floor, sqrt, power, exp, log, sin, cos, tan,
    # Date/Time function factories
    now, current_date, current_time, year, month, day, hour, minute, second,
    date_part, date_trunc,
    # Conditional function factories
    case, nullif, greatest, least,
    # Window function factories
    row_number, rank, dense_rank, lag, lead, first_value, last_value, nth_value,
    # JSON function factories
    json_extract, json_extract_text, json_build_object, json_array_elements,
    json_objectagg, json_arrayagg,
    # Array function factories
    array_agg, unnest, array_length,
    # Type conversion function factories
    cast, to_char, to_number, to_date,
    # Grouping function factories
    grouping_sets, rollup, cube,
    # Additional functions
    lower, upper,
    # String concatenation operator
    concat_op,
)

__all__ = [
    # Base classes and type aliases
    "ToSQLProtocol", "BaseExpression", "SQLValueExpression", "SQLPredicate", "SQLQueryAndParams", "is_sql_query_and_params",

    # Mixins
    "AliasableMixin",

    # Literals
    "Identifier",
    
    # Operators
    "SQLOperation", "BinaryExpression", "UnaryExpression", "RawSQLExpression", "RawSQLPredicate", "BinaryArithmeticExpression",
    
    # Core expressions
    "Column", "FunctionCall", "Subquery", "TableExpression", "Literal", "WildcardExpression",
    
    # Predicates
    "ComparisonPredicate", "LogicalPredicate", "LikePredicate", "InPredicate", "BetweenPredicate", "IsNullPredicate",
    
    # Aggregates
    "AggregateFunctionCall",
    
    # Advanced functions
    "CaseExpression", "CastExpression", "ExistsExpression", "AnyExpression", "AllExpression",
    "WindowFrameSpecification", "WindowSpecification", "WindowDefinition", "WindowClause", "WindowFunctionCall",
    "JSONExpression", "ArrayExpression", "OrderedSetAggregation",
    
    # Query parts
    "GroupingExpression", "JoinExpression", "JoinType",
    "WhereClause", "GroupByHavingClause", "OrderByClause", "LimitOffsetClause", "QualifyClause", "ForUpdateClause",
    
    # Query sources
    "SetOperationExpression", "CTEExpression", "WithQueryExpression", "ValuesExpression",
    "TableFunctionExpression", "LateralExpression", "JSONTableColumn", "JSONTableExpression",
    
    # Statements
    "QueryExpression", "DeleteExpression", "UpdateExpression", "InsertExpression", "ExplainExpression",
    "MergeActionType", "MergeAction", "MergeExpression", "SelectModifier",
    "ExplainType", "ExplainFormat", "ExplainOptions", "ReturningClause",
    "InsertDataSource", "ValuesSource", "SelectSource", "DefaultValuesSource", "OnConflictClause",
    "ColumnDefinition", "IndexDefinition", "CreateTableExpression", "DropTableExpression",
    "CreateViewExpression", "DropViewExpression", "ViewOptions", "ViewCheckOption",
    "AlterTableAction", "AddColumn", "DropColumn", "AlterColumn", "AddConstraint", "DropConstraint",
    "RenameObject", "AddIndex", "DropIndex", "AlterTableExpression", "TruncateExpression",
    
    # Graph
    "GraphEdgeDirection", "GraphVertex", "GraphEdge", "MatchClause",
    
    # Functions
    "count", "sum_", "avg", "min_", "max_", "lower", "upper", "concat", "coalesce",
    "length", "substring", "trim", "replace", "initcap", "left", "right", "lpad", "rpad", "reverse", "strpos",
    "abs_", "round_", "ceil", "floor", "sqrt", "power", "exp", "log", "sin", "cos", "tan",
    "now", "current_date", "current_time", "year", "month", "day", "hour", "minute", "second",
    "date_part", "date_trunc",
    "case", "nullif", "greatest", "least",
    "row_number", "rank", "dense_rank", "lag", "lead", "first_value", "last_value", "nth_value",
    "json_extract", "json_extract_text", "json_build_object", "json_array_elements",
    "json_objectagg", "json_arrayagg",
    "array_agg", "unnest", "array_length",
    "cast", "to_char", "to_number", "to_date",
    "grouping_sets", "rollup", "cube",
    "concat_op",
]