# src/rhosocial/activerecord/backend/expression/statements.py
"""
SQL DML (Data Manipulation Language), DQL (Data Query Language),
and DDL (Data Definition Language) statements.

These expression classes are responsible for collecting the parameters and structure
for a given SQL statement and delegating the actual SQL string generation
to a backend-specific dialect.
"""
import abc
from typing import Tuple, Any, List, Optional, Dict, Union, TYPE_CHECKING
from enum import Enum
from dataclasses import dataclass, field

from . import bases
from . import core
from . import mixins

# if TYPE_CHECKING:
#     from ..dialect import SQLDialectBase, ExplainOptions
#     from .query_clauses import SetOperationExpression, JoinExpression, ValuesExpression, TableFunctionExpression, LateralExpression
#     from .advanced_functions import WindowFunctionCall, WindowSpecification, WindowFrameSpecification


# region DML and DQL Statements

# region Merge Statement
class MergeActionType(Enum):
    """Represents the type of action to perform in a MERGE statement."""
    UPDATE = "UPDATE"
    INSERT = "INSERT"
    DELETE = "DELETE"


@dataclass
class MergeAction:
    """
    Represents an action (UPDATE, INSERT, or DELETE) to be performed
    within a MERGE statement's WHEN clause.
    """
    action_type: MergeActionType
    assignments: Optional[Dict[str, "bases.BaseExpression"]] = field(default_factory=dict)  # For UPDATE SET clause
    values: Optional[List["bases.BaseExpression"]] = field(default_factory=list)  # For INSERT VALUES clause
    condition: Optional["bases.SQLPredicate"] = None  # Optional additional condition for the WHEN clause


class MergeExpression(bases.BaseExpression):
    """
    Represents a SQL MERGE statement conforming to SQL standard syntax.

    The MERGE statement performs conditional processing based on whether a row
    exists in the target table that matches the source row according to the ON condition.

    Basic syntax:
        MERGE INTO target_table
        USING source
        ON condition
        WHEN MATCHED THEN action
        WHEN NOT MATCHED THEN action
        [WHEN NOT MATCHED BY SOURCE THEN action];

    Example:
        # Simple merge: update if exists, insert if not
        merge = MergeExpression(
            dialect,
            target_table="products",
            source=ValuesSource(dialect, [[1, "Product A", 19.99]], "new_products", ["id", "name", "price"]),
            on_condition=Column(dialect, "id", "tgt") == Column(dialect, "id", "src"),
            when_matched=[
                MergeAction(
                    action_type=MergeActionType.UPDATE,
                    assignments={
                        "name": Column(dialect, "name", "src"),
                        "price": Column(dialect, "price", "src")
                    }
                )
            ],
            when_not_matched=[
                MergeAction(
                    action_type=MergeActionType.INSERT,
                    assignments={
                        "id": Column(dialect, "id", "src"),
                        "name": Column(dialect, "name", "src"),
                        "price": Column(dialect, "price", "src")
                    }
                )
            ]
        )
    """
    def __init__(self, dialect: "SQLDialectBase",
                 target_table: Union[str, "core.TableExpression"],
                 source: Union["core.Subquery", "core.TableExpression", "ValuesExpression", "TableFunctionExpression", "LateralExpression"],
                 on_condition: "bases.SQLPredicate",  # The main matching condition
                 when_matched: Optional[List[MergeAction]] = None,  # WHEN MATCHED THEN ...
                 when_not_matched: Optional[List[MergeAction]] = None,  # WHEN NOT MATCHED THEN ...
                 when_not_matched_by_source: Optional[List[MergeAction]] = None):  # WHEN NOT MATCHED BY SOURCE THEN ... (not supported by all DBs)
        super().__init__(dialect)
        self.target_table = target_table if isinstance(target_table, core.TableExpression) else core.TableExpression(dialect, str(target_table))
        self.source = source
        self.on_condition = on_condition
        self.when_matched = when_matched or []
        self.when_not_matched = when_not_matched or []
        self.when_not_matched_by_source = when_not_matched_by_source or []

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegates SQL generation for the MERGE statement to the configured dialect."""
        return self.dialect.format_merge_statement(self)
# endregion Merge Statement


# region Query Statement
class SelectModifier(Enum):
    """
    Specifies the SELECT clause modifier to apply to the result set.

    This enumeration allows controlling duplicate row inclusion in query results.
    Note that ALL is often the default behavior in SQL and may be omitted in
    the generated SQL depending on the dialect's requirements.
    """
    DISTINCT = "DISTINCT"
    ALL = "ALL"


class ForUpdateClause(bases.BaseExpression):
    """
    Represents the FOR UPDATE clause used for row-level locking in SELECT statements.

    The FOR UPDATE clause locks selected rows preventing other transactions from
    modifying them until the current transaction is committed or rolled back.

    Example Usage:
        # Basic FOR UPDATE
        ForUpdateClause(dialect)

        # FOR UPDATE with specific columns
        ForUpdateClause(dialect, of_columns=[Column(dialect, "id"), "name"])

        # FOR UPDATE with NOWAIT
        ForUpdateClause(dialect, nowait=True)

        # FOR UPDATE with SKIP LOCKED
        ForUpdateClause(dialect, skip_locked=True)
    """
    def __init__(self, dialect: "SQLDialectBase",
                 of_columns: Optional[List[Union[str, "bases.BaseExpression"]]] = None,  # Specify columns to lock
                 nowait: bool = False,  # NOWAIT option - fail immediately if locked
                 skip_locked: bool = False,  # SKIP LOCKED option - skip locked rows
                 dialect_options: Optional[Dict[str, Any]] = None):  # Dialect-specific options
        super().__init__(dialect)
        self.of_columns = of_columns or []  # Columns to apply the lock to
        self.nowait = nowait  # If True, fail immediately if rows are locked
        self.skip_locked = skip_locked  # If True, skip locked rows instead of waiting
        self.dialect_options = dialect_options or {}  # Additional dialect-specific options

    def to_sql(self) -> Tuple[str, tuple]:
        """
        Generate the SQL representation of the FOR UPDATE clause.

        This method delegates the actual SQL generation to the configured dialect,
        allowing for database-specific variations in the FOR UPDATE syntax.

        Args:
            None - All data is contained within the object instance

        Returns:
            Tuple containing:
            - SQL string fragment for the FOR UPDATE clause
            - Tuple of parameter values for prepared statements
        """
        return self.dialect.format_for_update_clause(self)


class QueryExpression(mixins.ArithmeticMixin, mixins.ComparisonMixin, bases.SQLValueExpression):
    """
    Represents a complete SELECT query expression with all clauses supported by the framework.

    This class encapsulates a full SQL SELECT statement structure, offering comprehensive
    support for various SQL clauses including SELECT modifiers, complex FROM clauses with
    joins and subqueries, filtering, grouping, window functions, and locking mechanisms.

    The class validates inter-clause dependencies (e.g., HAVING requires GROUP BY) and
    delegates SQL generation to the configured dialect for database-specific syntax.

    Example Usage:
        # Basic SELECT query
        query = QueryExpression(
            dialect,
            select=[Column(dialect, "id"), Column(dialect, "name")],
            from_=TableExpression(dialect, "users"),
            where=Column(dialect, "status") == Literal(dialect, "active")  # Using overloaded comparison operator
        )

        # Scalar SELECT query - selecting constants or function results without FROM
        scalar_query = QueryExpression(
            dialect,
            select=[Literal(dialect, 1)]  # Equivalent to SELECT 1;
        )

        now_query = QueryExpression(
            dialect,
            select=[FunctionCall(dialect, "NOW")]  # Equivalent to SELECT NOW();
        )

        # SELECT with DISTINCT and complex clauses
        query = QueryExpression(
            dialect,
            select=[Column(dialect, "category"), FunctionCall(dialect, "COUNT", Column(dialect, "id"))],
            from_=TableExpression(dialect, "products"),
            where=Column(dialect, "price") > Literal(dialect, 100),  # Using overloaded comparison operator
            group_by=[Column(dialect, "category")],
            having=FunctionCall(dialect, "COUNT", Column(dialect, "id")) > Literal(dialect, 5),  # Using overloaded comparison operator
            order_by=[(Column(dialect, "category"), "ASC")],
            limit=10,
            select_modifier=SelectModifier.DISTINCT
        )

        # Simple aggregate functions
        count_query = QueryExpression(
            dialect,
            select=[FunctionCall(dialect, "COUNT", Column(dialect, "id"))],  # COUNT(id)
            from_=TableExpression(dialect, "users")
        )

        max_price_query = QueryExpression(
            dialect,
            select=[FunctionCall(dialect, "MAX", Column(dialect, "price"))],  # MAX(price)
            from_=TableExpression(dialect, "products")
        )

        # Window functions using the window function classes
        # Example of using window functions - ROW_NUMBER() with PARTITION BY
        window_spec = WindowSpecification(
            dialect,
            partition_by=[Column(dialect, "department")],
            order_by=[(Column(dialect, "salary"), "DESC")]
        )
        window_func = WindowFunctionCall(
            dialect,
            function_name="ROW_NUMBER",
            window_spec=window_spec,
            alias="row_num"
        )

        window_query = QueryExpression(
            dialect,
            select=[
                Column(dialect, "employee_name"),
                Column(dialect, "department"),
                Column(dialect, "salary"),
                window_func  # Window function call
            ],
            from_=TableExpression(dialect, "employees"),
            order_by=[Column(dialect, "department"), (Column(dialect, "row_num"), "ASC")]
        )
    """
    def __init__(self, dialect: "SQLDialectBase",
                 select: List["bases.BaseExpression"],  # SELECT clause - required, list of selected expressions
                 from_: Optional[Union[  # FROM clause - optional, but determines the nature of the query
                     "core.TableExpression",      # Single table
                     "core.Subquery",             # Subquery
                     "SetOperationExpression",    # Set operations (UNION, etc.)
                     "JoinExpression",            # Join expression (treated as a single object)
                     List[Union["core.TableExpression", "core.Subquery", "SetOperationExpression"]],  # Multiple tables/subqueries
                     "ValuesExpression",          # VALUES expression
                     "TableFunctionExpression",   # Table function
                     "LateralExpression"          # LATERAL expression
                 ]] = None,
                 where: Optional["bases.SQLPredicate"] = None,  # WHERE clause - optional, must be a predicate
                 group_by: Optional[List["bases.BaseExpression"]] = None,  # GROUP BY clause - optional, list of expressions
                 having: Optional["bases.SQLPredicate"] = None,  # HAVING clause - optional, only valid with GROUP BY, must be a predicate
                 order_by: Optional[List[  # ORDER BY clause - optional, list of ordering specifications
                     Union[
                         "bases.BaseExpression",  # Expression ordering (assumes ASC direction)
                         Tuple["bases.BaseExpression", str]  # (expression, ASC/DESC direction)
                     ]
                 ]] = None,
                 qualify: Optional["bases.SQLPredicate"] = None,  # QUALIFY clause - optional, for filtering window function results
                 limit: Optional[Union[int, "bases.BaseExpression"]] = None,  # LIMIT clause - optional, for limiting result count
                 offset: Optional[Union[int, "bases.BaseExpression"]] = None,  # OFFSET clause - requires LIMIT, for skipping rows
                 for_update: Optional["ForUpdateClause"] = None,  # FOR UPDATE clause - optional locking specification
                 select_modifier: Optional[SelectModifier] = None,  # SELECT modifier - DISTINCT|ALL, None means no modifier
                 *,  # Force keyword arguments
                 dialect_options: Optional[Dict[str, Any]] = None):  # Dialect-specific options - optional
        """
        Initialize a QueryExpression instance with the specified query components.

        Args:
            dialect: The SQL dialect instance that determines query generation rules
            select: List of expressions to select (required). At least one expression must be provided.
            from_: Source of data for the query (optional). Can be a table, subquery, join, etc.
            where: Filtering condition applied to rows (optional). Must be a predicate.
            group_by: List of expressions to group by (optional). Used with aggregate functions.
            having: Group filtering condition (optional). Can only be used with GROUP BY. Must be a predicate.
            order_by: List of ordering specifications (optional). Each can be an expression
                     (defaults to ASC) or a tuple of (expression, direction).
            qualify: Filtering condition for window function results (optional). Available in some dialects.
            limit: Maximum number of rows to return (optional). Can be int or expression.
            offset: Number of rows to skip before returning results (optional). Requires LIMIT.
            for_update: Row locking specification (optional). Used for concurrent access control.
            select_modifier: Modifier for the SELECT clause (optional). Options: DISTINCT, ALL.
            dialect_options: Additional database-specific parameters (optional).

        Raises:
            ValueError: If HAVING is provided without GROUP BY
                      If OFFSET is provided without LIMIT (depending on dialect support)
                      If assignments are empty (though not applicable to QueryExpression)

        Note:
            - The HAVING clause requires a GROUP BY clause to be present
            - OFFSET without LIMIT behavior depends on dialect support
            - ORDER BY items can include either expressions (defaulting to ASC) or tuples of (expression, direction)
            - The select_modifier controls duplicate inclusion (DISTINCT removes duplicates, ALL keeps all rows)
        """
        super().__init__(dialect)

        # Validate HAVING requires GROUP BY
        if having is not None and not group_by:
            raise ValueError("HAVING clause requires GROUP BY clause")

        # Validate OFFSET requires LIMIT (some databases allow OFFSET alone, but this is database-specific behavior)
        if offset is not None and limit is None:
            # Decide whether to allow OFFSET without LIMIT based on dialect
            if not dialect.supports_offset_without_limit():
                raise ValueError("OFFSET clause requires LIMIT clause in this dialect")

        self.select = select or []  # List of expressions to be selected
        self.from_ = from_  # Source of query data (optional)
        self.where = where  # Filter condition (predicate), optional
        self.group_by = group_by or []  # Grouping expressions, optional
        self.having = having  # Group filter condition (predicate), optional, requires GROUP BY
        self.order_by = order_by or []  # Ordering specifications, optional
        self.qualify = qualify  # Window function filter condition, optional
        self.limit = limit  # Result limit, optional
        self.offset = offset  # Row skip count, optional, requires LIMIT
        self.for_update = for_update  # FOR UPDATE clause object, optional
        self.select_modifier = select_modifier  # SELECT modifier (DISTINCT/ALL), optional
        self.dialect_options = dialect_options or {}  # Dialect-specific options

    def to_sql(self) -> Tuple[str, tuple]:
        """
        Generate the SQL string and parameters for this query expression.

        This method delegates the SQL generation to the configured dialect, allowing for
        database-specific variations in syntax and feature support. The generated SQL
        follows the structure: SELECT ... FROM ... WHERE ... GROUP BY ... HAVING ... etc.

        Returns:
            A tuple containing:
            - str: The complete SQL query string
            - tuple: The parameter values for prepared statement execution
        """
        return self.dialect.format_query_statement(self)
# endregion Query Statement


# region Explain Statement
class ExplainType(Enum):
    """EXPLAIN statement type, representing different analysis modes."""
    BASIC = "BASIC"                    # Basic plan
    ANALYZE = "ANALYZE"                # Execute and analyze
    QUERY_PLAN = "QUERY_PLAN"          # Query plan
    PLAN = "PLAN"                      # Execution plan
    FORMAT = "FORMAT"                  # Formatted output
    PROFILE = "PROFILE"                # Performance profile


class ExplainFormat(Enum):
    """EXPLAIN output formats."""
    TEXT = "TEXT"                      # Text format
    JSON = "JSON"                      # JSON format
    XML = "XML"                        # XML format
    YAML = "YAML"                      # YAML format
    TREE = "TREE"                      # Tree format
    TRADITIONAL = "TRADITIONAL"        # Traditional format


@dataclass
class ExplainOptions:
    """
    EXPLAIN options class to control the behavior of EXPLAIN statements.

    Note: Different databases support different sets of options, these options will be processed
    by the dialect implementation to generate suitable EXPLAIN statement for specific database.
    """
    # Options similar to PostgreSQL
    analyze: bool = False              # Execute query and show actual statistics
    verbose: bool = False              # Show additional plan information
    costs: bool = True                 # Show plan cost estimates (enabled by default)
    buffers: bool = False              # Show buffer usage statistics
    timing: bool = False               # Show timing statistics for each node
    summary: bool = True               # Show summary information

    # Output format options
    format: Optional[ExplainFormat] = None    # Output format

    # Format-related options
    format_name: Optional[str] = None  # FORMAT=XXX format name
    analyze_format: Optional[bool] = None  # Format options for ANALYZE

    # General options
    type: Optional[ExplainType] = None      # Analysis type
    settings: bool = False                  # Show settings impact (PostgreSQL)
    wal: bool = False                       # Show WAL statistics

    # Dialect-specific options - for uncommon database options
    dialect_options: Optional[Dict[str, Any]] = None


class ExplainExpression(bases.BaseExpression):
    """
    Unified EXPLAIN expression class that supports differences across database dialects.

    Due to the large differences in EXPLAIN syntax across different databases, this class
    collects options and delegates SQL generation to the specific dialect implementation.

    Usage Examples:
        # Basic EXPLAIN
        basic_explain = ExplainExpression(
            dialect,
            statement=query_stmt
        )

        # EXPLAIN with options
        detailed_explain = ExplainExpression(
            dialect,
            statement=query_stmt,
            options=ExplainOptions(
                analyze=True,          # Execute and analyze the query
                verbose=True,          # Show additional information
                costs=True,            # Include cost estimates
                buffers=True,          # Include buffer statistics
                format=ExplainFormat.JSON  # Output in JSON format
            )
        )

        # EXPLAIN with specific format
        formatted_explain = ExplainExpression(
            dialect,
            statement=query_stmt,
            options=ExplainOptions(
                format=ExplainFormat.TEXT,  # Text output format
                costs=True,                 # Include cost estimates
                buffers=False,              # Exclude buffer statistics
                timing=True                 # Include timing information
            )
        )
    """
    def __init__(self, dialect: "SQLDialectBase",
                 statement: "bases.BaseExpression",  # Statement to be analyzed
                 options: Optional[ExplainOptions] = None):  # EXPLAIN options
        super().__init__(dialect)
        self.statement = statement  # SQL statement to analyze (query, insert, update, delete, etc.)
        self.options = options  # EXPLAIN options, keeping None if passed as None

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegate to dialect for EXPLAIN statement SQL generation."""
        return self.dialect.format_explain_statement(self)
# endregion Explain Statement


class ReturningClause(bases.BaseExpression):
    """
    Represents a RETURNING clause used in INSERT, UPDATE, and DELETE statements.

    The RETURNING clause allows retrieval of values from modified rows during
    DML operations, which is useful for obtaining auto-generated values, or
    for audit trails. The specific syntax and supported expressions may vary
    significantly between different SQL databases.

    This class follows the framework pattern of collecting parameters and
    delegating SQL generation to the specific dialect.

    Example Usage:
        # Basic RETURNING clause with columns
        returning_clause = ReturningClause(
            dialect,
            expressions=[Column(dialect, "id"), Column(dialect, "created_at")]
        )

        # RETURNING clause with computed expressions
        returning_clause = ReturningClause(
            dialect,
            expressions=[
                Column(dialect, "id"),
                FunctionCall(dialect, "NOW"),
                Literal(dialect, "updated")  # Constant value
            ],
            alias="modified_rows"
        )

        # RETURNING * to return all columns
        returning_clause = ReturningClause(
            dialect,
            expressions=[RawSQLExpression(dialect, "*")]  # Use RawSQL for asterisk
        )
    """
    def __init__(self, dialect: "SQLDialectBase",
                 expressions: List["bases.BaseExpression"],  # List of expressions to return
                 alias: Optional[str] = None,                # Optional alias for the returning result
                 dialect_options: Optional[Dict[str, Any]] = None):  # Dialect-specific options
        super().__init__(dialect)
        self.expressions = expressions or []
        self.alias = alias  # Optional alias for the returning clause
        self.dialect_options = dialect_options or {}  # Dialect-specific options

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegates to dialect for RETURNING clause SQL generation."""
        return self.dialect.format_returning_clause(self)


# region Delete Statement
class DeleteExpression(bases.BaseExpression):
    """
    Represents an SQL DELETE statement, allowing removal of rows from a table.
    It supports specifying a target table, an optional FROM clause for joining
    with other tables or subqueries (behavior and supported sources may vary
    significantly across SQL dialects), a WHERE clause for filtering rows,
    a RETURNING clause, and backend-specific options.
    """
    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: Union[str, "core.TableExpression"],
        *, # Enforce keyword-only arguments for optional parameters
        from_: Optional[Union[
            "core.TableExpression",
            "core.Subquery",
            "SetOperationExpression",
            "JoinExpression",
            List[Union["core.TableExpression", "core.Subquery", "SetOperationExpression", "JoinExpression", "ValuesExpression", "TableFunctionExpression", "LateralExpression"]]
        ]] = None,
        where: Optional["bases.SQLPredicate"] = None,
        returning: Optional["ReturningClause"] = None,  # Using ReturningClause instead of list of expressions
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)

        # Normalize the target table to a TableExpression
        self.table = table if isinstance(table, core.TableExpression) else core.TableExpression(dialect, str(table))
        self.from_ = from_
        self.where = where
        self.returning = returning  # ReturningClause object or None
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegates SQL generation for the DELETE statement to the configured dialect."""
        return self.dialect.format_delete_statement(self)
# endregion Delete Statement


# region Update Statement
class UpdateExpression(bases.BaseExpression):
    """
    Represents an SQL UPDATE statement, allowing modification of existing rows
    in a table. It supports a target table, assignment of new values to columns,
    an optional FROM clause for joining with other tables or subqueries (behavior
    and supported sources may vary significantly across SQL dialects, e.g.,
    PostgreSQL offers a more flexible FROM than SQLite's more restrictive syntax),
    a WHERE clause for filtering rows, a RETURNING clause, and backend-specific options.
    """
    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: Union[str, "core.TableExpression"],
        assignments: Dict[str, "bases.BaseExpression"],
        *, # Enforce keyword-only arguments for optional parameters
        from_: Optional[Union[ # Optional FROM clause, compatible with various SQL dialects.
                               # SQLite's UPDATE FROM is more restrictive, typically allowing only
                               # a comma-separated list of table-or-subquery or a single JOIN clause.
                               # More advanced SQL dialects (e.g., PostgreSQL) allow richer FROM sources.
            "core.TableExpression",
            "core.Subquery",
            "SetOperationExpression",
            "JoinExpression",
            List[Union["core.TableExpression", "core.Subquery", "SetOperationExpression", "JoinExpression", "ValuesExpression", "TableFunctionExpression", "LateralExpression"]]
        ]] = None,
        where: Optional["bases.SQLPredicate"] = None,
        returning: Optional["ReturningClause"] = None,  # Using ReturningClause instead of list of expressions
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)

        # Normalize the target table to a TableExpression
        self.table = table if isinstance(table, core.TableExpression) else core.TableExpression(dialect, str(table))
        self.assignments = assignments
        self.from_ = from_
        self.where = where
        self.returning = returning  # ReturningClause object or None
        self.dialect_options = dialect_options or {}

        # Basic validation for assignments
        if not self.assignments:
            raise ValueError("Assignments cannot be empty for an UPDATE statement.")

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegates SQL generation for the UPDATE statement to the configured dialect."""
        return self.dialect.format_update_statement(self)
# endregion Update Statement


# region Insert Statement
class InsertDataSource(abc.ABC):
    """
    Abstract base class for an INSERT statement's data source.
    Implementations represent the source of data, such as a VALUES clause,
    a SELECT query, or the DEFAULT VALUES keyword.
    """
    def __init__(self, dialect: "SQLDialectBase"):
        self._dialect = dialect

    @property
    def dialect(self) -> "SQLDialectBase":
        return self._dialect


class ValuesSource(InsertDataSource):
    """
    Represents a data source from a VALUES clause, where values are provided
    as explicit expressions for insertion into a table.

    The `values_list` parameter defines the rows of data to be inserted.
    Each element in `values_list` is itself a list, representing a single row,
    and each element within a row list must be an expression.

    Currently, the type hint for these expressions is `bases.BaseExpression`.
    This generic type allows for various expression types (e.g., `Literal`, `Column`,
    `RawSQLExpression`, scalar `QueryExpression` as subqueries) to be used as values.
    It is a pragmatic choice given the current stage of framework development.

    However, it's important to note that statement-level expressions (such as
    `InsertExpression`, `UpdateExpression`, `DeleteExpression`, or non-scalar `QueryExpression`)
    are *not* valid elements within `values_list`. These are complete SQL statements
    and do not represent a single value or expression suitable for a `VALUES` clause.

    In future iterations, as the framework matures, the type hint may be refined
    to a more specific `Union` of supported `bases.BaseExpression` derived classes
    (e.g., `Union[Literal, Column, ScalarSubquery]`) to provide stricter type checking
    and clearer developer guidance on what constitutes a valid value expression.
    """
    def __init__(self, dialect: "SQLDialectBase", values_list: List[List["bases.BaseExpression"]]):
        super().__init__(dialect)
        if not values_list or not all(isinstance(row, list) for row in values_list):
            raise ValueError("'values_list' must be a non-empty list of lists.")
        if len(set(len(row) for row in values_list)) > 1:
            raise ValueError("All rows in 'values_list' must have the same number of columns.")
        self.values_list = values_list


class SelectSource(InsertDataSource):
    """Represents a data source from a SELECT subquery."""
    def __init__(self, dialect: "SQLDialectBase", select_query: "QueryExpression"):
        super().__init__(dialect)
        self.select_query = select_query


class DefaultValuesSource(InsertDataSource):
    """Represents the DEFAULT VALUES data source."""
    pass


class OnConflictClause(bases.BaseExpression):
    """
    Represents an ON CONFLICT clause for "upsert" operations, supporting
    both DO NOTHING and DO UPDATE actions.
    """
    def __init__(
        self,
        dialect: "SQLDialectBase",
        conflict_target: Optional[List[Union[str, "bases.BaseExpression"]]],
        *,
        do_nothing: bool = False,
        update_assignments: Optional[Dict[str, "bases.BaseExpression"]] = None,
        update_where: Optional["bases.SQLPredicate"] = None
    ):
        super().__init__(dialect)
        if do_nothing and (update_assignments is not None):
            raise ValueError("Cannot specify both 'do_nothing=True' and 'update_assignments' for ON CONFLICT.")
        if not do_nothing and update_assignments is None:
            raise ValueError("Must specify either 'do_nothing=True' or 'update_assignments' for ON CONFLICT.")

        self.conflict_target = conflict_target
        self.do_nothing = do_nothing
        self.update_assignments = update_assignments
        self.update_where = update_where

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegates formatting of the ON CONFLICT clause to the configured dialect."""
        return self.dialect.format_on_conflict_clause(self)


class InsertExpression(bases.BaseExpression):
    """
    Represents a structured INSERT statement, supporting various data sources,
    upsert logic (ON CONFLICT), and RETURNING clauses.
    """
    def __init__(
        self,
        dialect: "SQLDialectBase",
        into: Union[str, "core.TableExpression"],
        source: InsertDataSource,
        columns: Optional[List[str]] = None,
        *,
        on_conflict: Optional[OnConflictClause] = None,
        returning: Optional["ReturningClause"] = None,  # Using ReturningClause instead of list of expressions
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)

        self.into = into if isinstance(into, core.TableExpression) else core.TableExpression(dialect, str(into))
        self.source = source
        self.columns = columns
        self.on_conflict = on_conflict
        self.returning = returning  # ReturningClause object or None
        self.dialect_options = dialect_options or {}

        # Perform validation
        # 1. First, check if on_conflict is used with a valid source
        if on_conflict and not isinstance(source, (ValuesSource, SelectSource)):
            raise ValueError("'on_conflict' is only supported for 'VALUES' or 'SELECT' sources.")

        # 2. Then, check for other misuses of DefaultValuesSource
        if isinstance(source, DefaultValuesSource) and columns:
            raise ValueError("'DEFAULT VALUES' source cannot be used with 'columns'.")

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegates SQL generation for the INSERT statement to the configured dialect."""
        return self.dialect.format_insert_statement(self)
# endregion Insert Statement

# endregion DML and DQL Statements


# region DDL Expressions

class ColumnConstraintType(Enum):
    """Types of column constraints."""
    PRIMARY_KEY = "PRIMARY KEY"
    NOT_NULL = "NOT NULL"
    UNIQUE = "UNIQUE"
    CHECK = "CHECK"
    FOREIGN_KEY = "FOREIGN KEY"
    DEFAULT = "DEFAULT"


@dataclass
class ColumnConstraint:
    """Represents a column constraint (PRIMARY KEY, NOT NULL, UNIQUE, etc.)"""
    constraint_type: ColumnConstraintType
    name: Optional[str] = None  # Optional constraint name
    check_condition: Optional["bases.SQLPredicate"] = None  # For CHECK constraints
    foreign_key_reference: Optional[Tuple[str, List[str]]] = None  # (referenced_table, referenced_columns)
    default_value: Any = None  # For DEFAULT constraints
    is_auto_increment: bool = False  # For AUTO_INCREMENT/IDENTITY columns
    comment: Optional[str] = None  # Column comment (optional)
    dialect_options: Optional[Dict[str, Any]] = None  # Database-specific options


@dataclass
class ColumnDefinition:
    """Represents a column's definition within a CREATE/ALTER TABLE statement."""
    name: str
    data_type: str  # e.g. "VARCHAR(255)", "INTEGER", "DECIMAL(10,2)", "CHARACTER VARYING(255)"
    nullable: Optional[bool] = None  # None = database default, True = NULL permitted, False = NOT NULL
    constraints: List[ColumnConstraint] = field(default_factory=list)  # Column constraints
    comment: Optional[str] = None  # Column comment
    dialect_options: Optional[Dict[str, Any]] = None  # Database-specific options


class TableConstraintType(Enum):
    """Types of table constraints supported by SQL."""
    PRIMARY_KEY = "PRIMARY KEY"
    UNIQUE = "UNIQUE"
    FOREIGN_KEY = "FOREIGN KEY"
    CHECK = "CHECK"
    EXCLUDE = "EXCLUDE"


class ReferentialAction(Enum):
    """Actions for referential integrity constraints."""
    CASCADE = "CASCADE"
    RESTRICT = "RESTRICT"
    SET_NULL = "SET NULL"
    SET_DEFAULT = "SET DEFAULT"
    NO_ACTION = "NO ACTION"


@dataclass
class TableConstraint:
    """Represents a table-level constraint."""
    constraint_type: TableConstraintType
    name: Optional[str] = None  # Optional constraint name
    columns: Optional[List[str]] = None  # For PK, UK constraints
    check_condition: Optional["bases.SQLPredicate"] = None  # For CHECK constraints
    foreign_key_table: Optional[str] = None  # For FK constraints
    foreign_key_columns: Optional[List[str]] = None  # For FK constraints
    dialect_options: Optional[Dict[str, Any]] = None  # Database-specific options


@dataclass
class ForeignKeyConstraint(TableConstraint):
    """Specialized table constraint for foreign keys with additional options."""
    constraint_type: TableConstraintType = TableConstraintType.FOREIGN_KEY
    on_delete: ReferentialAction = ReferentialAction.NO_ACTION
    on_update: ReferentialAction = ReferentialAction.NO_ACTION
    match_type: Optional[str] = None  # "SIMPLE", "PARTIAL", "FULL" for foreign key matching


@dataclass
class IndexDefinition:
    """Represents an index definition for a table."""
    name: str
    columns: List[str]  # List of column names to index
    unique: bool = False  # Whether the index enforces uniqueness
    type: Optional[str] = None  # Index type: BTREE, HASH, GIN, etc.
    partial_condition: Optional["bases.SQLPredicate"] = None  # For partial indexes (PostgreSQL)
    include_columns: Optional[List[str]] = None  # Included columns (non-key columns in index, SQL Server/PostgreSQL)
    dialect_options: Optional[Dict[str, Any]] = None  # Database-specific options


class CreateTableExpression(bases.BaseExpression):
    """Represents a comprehensive CREATE TABLE statement supporting full SQL standard features."""
    def __init__(self,
                 dialect: "SQLDialectBase",
                 table_name: str,
                 columns: List[ColumnDefinition],  # List of column definitions with constraints
                 indexes: Optional[List[IndexDefinition]] = None,  # Table indexes
                 table_constraints: Optional[List[TableConstraint]] = None,  # Table-level constraints
                 temporary: bool = False,  # TEMPORARY table flag
                 if_not_exists: bool = False,  # IF NOT EXISTS flag
                 inherits: Optional[List[str]] = None,  # PostgreSQL INHERITS clause
                 tablespace: Optional[str] = None,  # Table tablespace (PostgreSQL/Oracle)
                 storage_options: Optional[Dict[str, Any]] = None,  # Storage parameters (PostgreSQL WITH options, MySQL ENGINE options)
                 partition_by: Optional[Tuple[str, List[str]]] = None,  # Partitioning specification (partition_type, partition_columns)
                 as_query: Optional["QueryExpression"] = None,  # Create table AS query result
                 dialect_options: Optional[Dict[str, Any]] = None):  # Dialect-specific options
        super().__init__(dialect)
        self.table_name = table_name
        self.columns = columns  # List of column definitions with embedded constraints
        self.indexes = indexes or []  # List of indexes to create
        self.table_constraints = table_constraints or []  # List of table-level constraints
        self.temporary = temporary  # Temporary table flag
        self.if_not_exists = if_not_exists  # IF NOT EXISTS flag
        self.inherits = inherits or []  # Tables to inherit from (PostgreSQL-specific)
        self.tablespace = tablespace  # Tablespace specification
        self.storage_options = storage_options or {}  # Storage-related options
        self.partition_by = partition_by  # Partitioning specification
        self.as_query = as_query  # Query to base table on (for CREATE TABLE AS)
        self.dialect_options = dialect_options or {}  # Dialect-specific options

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegates SQL generation for the CREATE TABLE statement to the configured dialect."""
        return self.dialect.format_create_table_statement(self)


class DropTableExpression(bases.BaseExpression):
    """Represents a DROP TABLE statement."""
    def __init__(self, dialect: "SQLDialectBase", table_name: str, if_exists: bool = False):
        super().__init__(dialect)
        self.table_name = table_name
        self.if_exists = if_exists

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegates SQL generation for the DROP TABLE statement to the configured dialect."""
        return self.dialect.format_drop_table_statement(self)


class AlterTableActionType(Enum):
    """Type of action for ALTER TABLE statement."""
    ADD_COLUMN = "ADD COLUMN"
    DROP_COLUMN = "DROP COLUMN"
    ALTER_COLUMN = "ALTER COLUMN"
    ADD_CONSTRAINT = "ADD CONSTRAINT"
    DROP_CONSTRAINT = "DROP CONSTRAINT"
    RENAME_COLUMN = "RENAME COLUMN"
    RENAME_TABLE = "RENAME TABLE"
    ADD_INDEX = "ADD INDEX"
    DROP_INDEX = "DROP INDEX"


class AlterTableAction(abc.ABC):
    """Abstract base class for a single action within an ALTER TABLE statement."""
    action_type: AlterTableActionType
    pass


@dataclass
class AddColumn(AlterTableAction):
    """Represents an 'ADD COLUMN' action."""
    column: ColumnDefinition
    action_type: AlterTableActionType = AlterTableActionType.ADD_COLUMN


@dataclass
class DropColumn(AlterTableAction):
    """Represents a 'DROP COLUMN' action."""
    column_name: str
    action_type: AlterTableActionType = AlterTableActionType.DROP_COLUMN


@dataclass
class AlterColumn(AlterTableAction):
    """Represents an 'ALTER COLUMN' action to modify column properties."""
    column_name: str
    operation: str  # "SET DATA TYPE", "SET DEFAULT", "DROP DEFAULT", "SET NOT NULL", "DROP NOT NULL", etc.
    action_type: AlterTableActionType = AlterTableActionType.ALTER_COLUMN
    new_value: Any = None  # New type, default value, etc.
    cascade: bool = False  # For constraint modifications


@dataclass
class AddConstraint(AlterTableAction):
    """Represents an 'ADD CONSTRAINT' action."""
    constraint: TableConstraint
    action_type: AlterTableActionType = AlterTableActionType.ADD_CONSTRAINT


@dataclass
class DropConstraint(AlterTableAction):
    """Represents a 'DROP CONSTRAINT' action."""
    constraint_name: str
    cascade: bool = False  # Whether to CASCADE the constraint drop
    action_type: AlterTableActionType = AlterTableActionType.DROP_CONSTRAINT


@dataclass
class RenameObject(AlterTableAction):
    """Represents a 'RENAME' action for columns or tables."""
    old_name: str
    new_name: str
    action_type: AlterTableActionType = AlterTableActionType.RENAME_COLUMN
    object_type: str = "COLUMN"  # "COLUMN", "TABLE", or "INDEX"


@dataclass
class AddIndex(AlterTableAction):
    """Represents an 'ADD INDEX' action."""
    index: IndexDefinition
    action_type: AlterTableActionType = AlterTableActionType.ADD_INDEX


@dataclass
class DropIndex(AlterTableAction):
    """Represents a 'DROP INDEX' action."""
    index_name: str
    if_exists: bool = False
    action_type: AlterTableActionType = AlterTableActionType.DROP_INDEX


class AlterTableExpression(bases.BaseExpression):
    """
    Represents a comprehensive ALTER TABLE statement supporting full SQL standard functionality.

    The ALTER TABLE statement allows for modification of an existing table's structure,
    including adding/dropping columns, altering column properties, managing constraints
    and indexes, and renaming objects. Different SQL databases support different subsets
    of ALTER TABLE functionality, with significant variations in syntax.

    This class collects all ALTER TABLE parameters and delegates the actual SQL generation
    to a backend-specific dialect for database-specific syntax.

    Examples:
        # Add column
        alter_expr = AlterTableExpression(
            dialect,
            table_name="users",
            actions=[AddColumn(ColumnDefinition(dialect, "email", "VARCHAR(100)"))]
        )

        # Drop column
        alter_expr = AlterTableExpression(
            dialect,
            table_name="products",
            actions=[DropColumn("description")]
        )

        # Multiple actions in one statement
        alter_expr = AlterTableExpression(
            dialect,
            table_name="orders",
            actions=[
                AddColumn(ColumnDefinition(dialect, "status", "VARCHAR(20)")),
                RenameObject("id", "order_id", object_type="COLUMN")
            ]
        )

        # Add constraint
        alter_expr = AlterTableExpression(
            dialect,
            table_name="users",
            actions=[
                AddConstraint(
                    TableConstraint(
                        constraint_type=TableConstraintType.CHECK,
                        check_condition=Column(dialect, "age") > Literal(dialect, 0)
                    )
                )
            ]
        )

        # Alter column properties
        alter_expr = AlterTableExpression(
            dialect,
            table_name="products",
            actions=[
                AlterColumn(
                    "price",
                    operation="SET DATA TYPE",
                    new_value="NUMERIC(10,2)"
                )
            ]
        )
    """
    def __init__(self, dialect: "SQLDialectBase",
                 table_name: str,
                 actions: List[AlterTableAction],
                 *,  # Force keyword arguments
                 dialect_options: Optional[Dict[str, Any]] = None):
        """
        Initialize an ALTER TABLE expression with the specified modifications.

        Args:
            dialect: The SQL dialect instance that determines query generation rules
            table_name: Name of the table to alter
            actions: List of actions to perform on the table
            dialect_options: Additional database-specific parameters

        Raises:
            ValueError: If required parameters are missing or invalid
        """
        super().__init__(dialect)
        self.table_name = table_name
        self.actions = actions
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> Tuple[str, tuple]:
        """
        Generate the SQL string and parameters for this ALTER TABLE expression.

        This method delegates the SQL generation to the configured dialect, allowing for
        database-specific variations in ALTER TABLE syntax. The generated SQL follows
        the structure: ALTER TABLE table_name action1, action2, ...

        Returns:
            A tuple containing:
            - str: The complete ALTER TABLE SQL string
            - tuple: The parameter values for prepared statement execution
        """
        return self.dialect.format_alter_table_statement(self)

# endregion DDL Expressions