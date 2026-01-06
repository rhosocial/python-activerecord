# src/rhosocial/activerecord/backend/expression/statements.py
"""
SQL DML (Data Manipulation Language), DQL (Data Query Language),
and DDL (Data Definition Language) statements.

These expression classes are responsible for collecting the parameters and structure
for a given SQL statement and delegating the actual SQL string generation
to a backend-specific dialect.
"""
import abc
from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple, Any, List, Optional, Dict, Union, TYPE_CHECKING

from . import bases
from . import core
from . import mixins
from .query_parts import WhereClause, GroupByHavingClause, OrderByClause, QualifyClause, LimitOffsetClause, \
    ForUpdateClause

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase
    from .query_sources import SetOperationExpression, ValuesExpression, TableFunctionExpression, LateralExpression
    from .query_parts import WhereClause, GroupByHavingClause, OrderByClause, LimitOffsetClause, ForUpdateClause, JoinExpression


# Define type aliases for complex union types
FromSourceType = Union[
    str,                       # Table name as string
    "core.TableExpression",      # Single table
    "core.Subquery",             # Subquery
    "SetOperationExpression",    # Set operations (UNION, etc.)
    "JoinExpression",            # Join expression (treated as a single object)
    "ValuesExpression",          # VALUES expression
    "TableFunctionExpression",   # Table function
    "LateralExpression",         # LATERAL expression
]


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
            where=WhereClause(dialect, condition=Column(dialect, "status") == Literal(dialect, "active"))
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
            where=WhereClause(dialect, condition=Column(dialect, "price") > Literal(dialect, 100)),
            group_by_having=GroupByHavingClause(dialect, group_by=[Column(dialect, "category")],
                                               having=FunctionCall(dialect, "COUNT", Column(dialect, "id")) > Literal(dialect, 5)),
            order_by=OrderByClause(dialect, expressions=[(Column(dialect, "category"), "ASC")]),
            limit_offset=LimitOffsetClause(dialect, limit=10),
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
            order_by=OrderByClause(dialect, expressions=[Column(dialect, "department"), (Column(dialect, "row_num"), "ASC")])
        )

        # Query with FOR UPDATE clause
        lock_query = QueryExpression(
            dialect,
            select=[Column(dialect, "id"), Column(dialect, "status")],
            from_=TableExpression(dialect, "orders"),
            where=WhereClause(dialect, condition=Column(dialect, "status") == Literal(dialect, "pending")),
            for_update=ForUpdateClause(
                dialect,
                of_columns=[Column(dialect, "id")],
                nowait=True
            )
        )
    """
    def __init__(self, dialect: "SQLDialectBase",
                 select: List["bases.BaseExpression"],  # SELECT clause - required, list of selected expressions
                 from_: Optional[Union[  # FROM clause - optional, but determines the nature of the query
                     FromSourceType,  # Single data source type
                     # List of data source types (for comma-separated FROM clause - implicit CROSS JOIN)
                     List[FromSourceType]
                 ]] = None,
                 where: Optional[Union["bases.SQLPredicate", "WhereClause"]] = None,  # WHERE condition or clause object
                 group_by_having: Optional["GroupByHavingClause"] = None,  # Combined GROUP BY/HAVING clause object
                 order_by: Optional["OrderByClause"] = None,  # ORDER BY clause object
                 qualify: Optional["QualifyClause"] = None,  # QUALIFY clause object
                 limit_offset: Optional["LimitOffsetClause"] = None,  # Combined LIMIT/OFFSET clause object
                 for_update: Optional["ForUpdateClause"] = None,  # FOR UPDATE clause object
                 select_modifier: Optional[SelectModifier] = None,  # SELECT modifier - DISTINCT|ALL, None means no modifier
                 *,  # Force keyword arguments
                 dialect_options: Optional[Dict[str, Any]] = None):  # Dialect-specific options - optional
        """
        Initialize a QueryExpression instance with the specified query components.

        This class provides a comprehensive implementation of SQL SELECT statements with support for
        all major SQL clauses through dedicated clause objects. This approach allows for better
        encapsulation and validation of clause-specific requirements (e.g. HAVING requiring GROUP BY).

        Args:
            dialect: The SQL dialect instance that determines query generation rules
            select: List of expressions to select (required). At least one expression must be provided.
            from_: Source of data for the query (optional). Can be a table, subquery, join, etc.
                   Note: When using a single source, pass the expression directly (e.g., TableExpression).
                   When using multiple sources, you can either:
                   1. Pass a list of expressions (equivalent to comma-separated tables in FROM clause, creates implicit CROSS JOIN)
                   2. Use JoinExpression to explicitly define join conditions between tables
            where: WHERE clause object with the filtering condition (optional).
            group_by_having: Combined GROUP BY/HAVING clause object (optional). Handles validation
                           that HAVING requires GROUP BY within the clause object.
            order_by: ORDER BY clause object with the ordering specifications (optional).
            qualify: QUALIFY clause object with the filtering condition for window functions (optional).
            limit_offset: Combined LIMIT/OFFSET clause object (optional). Handles validation
                                that OFFSET requires LIMIT within the clause object.
            for_update: FOR UPDATE clause object with the locking specification (optional).
            select_modifier: Modifier for the SELECT clause (optional). Options: DISTINCT, ALL.
            dialect_options: Additional database-specific parameters (optional).

        Raises:
            ValueError: If HAVING is provided without GROUP BY (validated within GroupByHavingClause)
                      If OFFSET is provided without LIMIT (validated by dialect supports_offset_without_limit)
                      If assignments are empty (though not applicable to QueryExpression)
            TypeError: If from_ parameter is not one of the supported types

        Note:
            - Clause objects handle their own validation (e.g. GroupByHavingClause validates HAVING/GROUP BY dependency)
            - The select_modifier controls duplicate inclusion (DISTINCT removes duplicates, ALL keeps all rows)
            - All SQL clauses are represented by dedicated clause objects for better encapsulation
        """
        super().__init__(dialect)

        # Handle where parameter: accept either a predicate or a WhereClause object
        if where is not None:
            if isinstance(where, WhereClause):
                self.where = where  # Already a WhereClause object
            else:
                # Wrap a predicate in a WhereClause object
                self.where = WhereClause(dialect, condition=where)
        else:
            self.where = None

        # Store other clause objects directly
        self.group_by_having = group_by_having
        self.order_by = order_by
        self.qualify = qualify
        self.limit_offset = limit_offset
        self.for_update = for_update

        # Store basic parameters
        self.select = select or []  # List of expressions to be selected
        self.from_ = from_  # Source of query data (optional)
        self.select_modifier = select_modifier  # SELECT modifier (DISTINCT/ALL), optional
        self.dialect_options = dialect_options or {}  # Dialect-specific options


    def validate(self, strict: bool = True) -> None:
        """Validate QueryExpression parameters according to SQL standard.

        Args:
            strict: If True, perform strict validation that may impact performance.
                   If False, skip validation for performance optimization.

        Raises:
            TypeError: If validation fails with incorrect parameter types
        """
        if not strict:
            return

        # Validate select parameter
        if not isinstance(self.select, list):
            raise TypeError(f"select must be a list of expressions, got {type(self.select)}")

        # Validate from_ parameter - should be one of the allowed types
        def _is_valid_from_source(item):
            """Check if an item is a valid FROM source type."""
            # Check if it's one of the valid types: basic types or specific expression classes
            return (isinstance(item, (str, core.TableExpression, core.Subquery)) or
                    type(item).__name__ in [
                        'SetOperationExpression', 'JoinExpression', 'ValuesExpression',
                        'TableFunctionExpression', 'LateralExpression'
                    ])

        if self.from_ is not None:
            if isinstance(self.from_, list):
                # If it's a list, validate each element in the list
                for i, item in enumerate(self.from_):
                    if not _is_valid_from_source(item):
                        raise TypeError(f"from_ list item at index {i} must be one of: str, TableExpression, Subquery, SetOperationExpression, JoinExpression, ValuesExpression, TableFunctionExpression, LateralExpression, got {type(item)}")
            else:
                # For single values, validate using the same helper
                if not _is_valid_from_source(self.from_):
                    raise TypeError(f"from_ must be one of: str, TableExpression, Subquery, SetOperationExpression, JoinExpression, list, ValuesExpression, TableFunctionExpression, LateralExpression, got {type(self.from_)}")

        # Validate where parameter
        if self.where is not None and not isinstance(self.where, (WhereClause, bases.SQLPredicate)):
            raise TypeError(f"where must be WhereClause or SQLPredicate, got {type(self.where)}")

        # Validate group_by_having parameter
        if self.group_by_having is not None and not isinstance(self.group_by_having, GroupByHavingClause):
            raise TypeError(f"group_by_having must be GroupByHavingClause, got {type(self.group_by_having)}")

        # Validate order_by parameter
        if self.order_by is not None and not isinstance(self.order_by, OrderByClause):
            raise TypeError(f"order_by must be OrderByClause, got {type(self.order_by)}")

        # Validate qualify parameter
        if self.qualify is not None and not isinstance(self.qualify, QualifyClause):
            raise TypeError(f"qualify must be QualifyClause, got {type(self.qualify)}")

        # Validate limit_offset parameter
        if self.limit_offset is not None and not isinstance(self.limit_offset, LimitOffsetClause):
            raise TypeError(f"limit_offset must be LimitOffsetClause, got {type(self.limit_offset)}")

        # Validate for_update parameter
        if self.for_update is not None and not isinstance(self.for_update, ForUpdateClause):
            raise TypeError(f"for_update must be ForUpdateClause, got {type(self.for_update)}")

        # Validate select_modifier parameter
        if self.select_modifier is not None and not isinstance(self.select_modifier, SelectModifier):
            raise TypeError(f"select_modifier must be SelectModifier, got {type(self.select_modifier)}")


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
        table: Union[str, "core.TableExpression", List[Union[str, "core.TableExpression"]]],
        *, # Enforce keyword-only arguments for optional parameters
        using: Optional[Union[
            "core.TableExpression",
            "core.Subquery",
            "SetOperationExpression",
            "JoinExpression",
            List[Union["core.TableExpression", "core.Subquery", "SetOperationExpression", "JoinExpression", "ValuesExpression", "TableFunctionExpression", "LateralExpression"]]
        ]] = None,
        where: Optional[Union["bases.SQLPredicate", "WhereClause"]] = None,  # WHERE condition or clause object
        returning: Optional["ReturningClause"] = None,  # RETURNING clause object
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)

        # Normalize the target table(s) to a list of TableExpression objects
        if isinstance(table, list):
            if not table:
                raise ValueError("Table list cannot be empty for a DELETE statement.")
            self.tables = []
            for t in table:
                if isinstance(t, core.TableExpression):
                    self.tables.append(t)
                else:
                    self.tables.append(core.TableExpression(dialect, str(t)))
        else:
            # Single table
            single_table = table if isinstance(table, core.TableExpression) else core.TableExpression(dialect, str(table))
            self.tables = [single_table]

        self.using = using

        # Handle where parameter: accept either a predicate or a WhereClause object
        if where is not None:
            if isinstance(where, WhereClause):
                self.where = where  # Already a WhereClause object
            else:
                # Wrap a predicate in a WhereClause object
                self.where = WhereClause(dialect, condition=where)
        else:
            self.where = None

        self.returning = returning  # RETURNING clause object
        self.dialect_options = dialect_options or {}

    def validate(self, strict: bool = True) -> None:
        """Validate DeleteExpression parameters according to SQL standard.

        Args:
            strict: If True, perform strict validation that may impact performance.
                   If False, skip validation for performance optimization.

        Raises:
            TypeError: If validation fails with incorrect parameter types
            ValueError: If validation fails with invalid values
        """
        if not strict:
            return

        # Validate tables parameter (already normalized in constructor)
        if not isinstance(self.tables, list):
            raise TypeError(f"tables must be a list of tables, got {type(self.tables)}")
        if not self.tables:
            raise ValueError("Tables cannot be empty for a DELETE statement.")
        for i, table in enumerate(self.tables):
            if not isinstance(table, core.TableExpression):
                raise TypeError(f"tables[{i}] must be TableExpression, got {type(table)}")

        # Validate using parameter
        if self.using is not None:
            # Check if it's one of the valid types using isinstance with type names
            valid_types = (str, core.TableExpression, core.Subquery)
            if not isinstance(self.using, valid_types) and not isinstance(self.using, list):
                # For complex types, check their type names
                using_type_name = type(self.using).__name__
                valid_type_names = ['SetOperationExpression', 'JoinExpression', 'ValuesExpression',
                                  'TableFunctionExpression', 'LateralExpression', 'QueryExpression']
                if using_type_name not in valid_type_names:
                    raise TypeError(f"using must be one of: str, TableExpression, Subquery, SetOperationExpression, JoinExpression, list, ValuesExpression, TableFunctionExpression, LateralExpression, QueryExpression, got {type(self.using)}")

        # Validate where parameter
        if self.where is not None and not isinstance(self.where, (WhereClause, bases.SQLPredicate)):
            raise TypeError(f"where must be WhereClause or SQLPredicate, got {type(self.where)}")

        # Validate returning parameter
        if self.returning is not None and not isinstance(self.returning, ReturningClause):
            raise TypeError(f"returning must be ReturningClause, got {type(self.returning)}")

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
        where: Optional[Union["bases.SQLPredicate", "WhereClause"]] = None,  # WHERE condition or clause object
        returning: Optional["ReturningClause"] = None,  # RETURNING clause object
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)

        # Validate assignments
        if not assignments:
            raise ValueError("Assignments cannot be empty for an UPDATE statement.")

        # Normalize the target table to a TableExpression
        self.table = table if isinstance(table, core.TableExpression) else core.TableExpression(dialect, str(table))
        self.assignments = assignments
        self.from_ = from_

        # Handle where parameter: accept either a predicate or a WhereClause object
        if where is not None:
            if isinstance(where, WhereClause):
                self.where = where  # Already a WhereClause object
            else:
                # Wrap a predicate in a WhereClause object
                self.where = WhereClause(dialect, condition=where)
        else:
            self.where = None

        self.returning = returning  # RETURNING clause object
        self.dialect_options = dialect_options or {}

    def validate(self, strict: bool = True) -> None:
        """Validate UpdateExpression parameters according to SQL standard.

        Args:
            strict: If True, perform strict validation that may impact performance.
                   If False, skip validation for performance optimization.

        Raises:
            TypeError: If validation fails with incorrect parameter types
        """
        if not strict:
            return

        # Note: The table parameter is normalized in the constructor to always be a TableExpression,
        # so we don't need to validate its type here.

        # Validate assignments parameter
        if not isinstance(self.assignments, dict):
            raise TypeError(f"assignments must be dict, got {type(self.assignments)}")

        # Validate from_ parameter
        if self.from_ is not None:
            # Check if it's one of the valid types using isinstance with type names
            valid_types = (str, core.TableExpression, core.Subquery)
            if not isinstance(self.from_, valid_types) and not isinstance(self.from_, list):
                # For complex types, check their type names
                from_type_name = type(self.from_).__name__
                valid_type_names = ['SetOperationExpression', 'JoinExpression', 'ValuesExpression',
                                  'TableFunctionExpression', 'LateralExpression']
                if from_type_name not in valid_type_names:
                    raise TypeError(f"from_ must be one of: str, TableExpression, Subquery, SetOperationExpression, JoinExpression, list, ValuesExpression, TableFunctionExpression, LateralExpression, got {type(self.from_)}")

        # Validate where parameter
        if self.where is not None and not isinstance(self.where, (WhereClause, bases.SQLPredicate)):
            raise TypeError(f"where must be WhereClause or SQLPredicate, got {type(self.where)}")

        # Validate returning parameter
        if self.returning is not None and not isinstance(self.returning, ReturningClause):
            raise TypeError(f"returning must be ReturningClause, got {type(self.returning)}")

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
        if len({len(row) for row in values_list}) > 1:
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

    def validate(self, strict: bool = True) -> None:
        """Validate InsertExpression parameters according to SQL standard.

        Args:
            strict: If True, perform strict validation that may impact performance.
                   If False, skip validation for performance optimization.

        Raises:
            TypeError: If validation fails with incorrect parameter types
        """
        if not strict:
            return

        # Validate into parameter
        if not isinstance(self.into, (str, core.TableExpression)):
            raise TypeError(f"into must be str or TableExpression, got {type(self.into)}")

        # Validate source parameter
        if not isinstance(self.source, InsertDataSource):
            raise TypeError(f"source must be InsertDataSource, got {type(self.source)}")

        # Validate columns parameter
        if self.columns is not None and not isinstance(self.columns, list):
            raise TypeError(f"columns must be list of strings or None, got {type(self.columns)}")

        # Validate on_conflict parameter
        if self.on_conflict is not None and not isinstance(self.on_conflict, OnConflictClause):
            raise TypeError(f"on_conflict must be OnConflictClause, got {type(self.on_conflict)}")

        # Validate returning parameter
        if self.returning is not None and not isinstance(self.returning, ReturningClause):
            raise TypeError(f"returning must be ReturningClause, got {type(self.returning)}")

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
    NULL = "NULL"          # Explicitly allow NULL (usually redundant but sometimes needed for clarity)
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
    dialect_options: Optional[Dict[str, Any]] = None  # Database-specific options


@dataclass
class ColumnDefinition:
    """Represents a column's definition within a CREATE/ALTER TABLE statement."""
    name: str
    data_type: str  # e.g. "VARCHAR(255)", "INTEGER", "DECIMAL(10,2)", "CHARACTER VARYING(255)"
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
                 *,  # Force keyword arguments
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

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegate to the dialect's format_* method based on action type."""
        # Access dialect from the object's __dict__ which is set by AlterTableExpression
        if hasattr(self, '_dialect'):
            dialect = self._dialect
            if self.action_type == AlterTableActionType.ADD_COLUMN:
                return dialect.format_add_column_action(self)
            elif self.action_type == AlterTableActionType.DROP_COLUMN:
                return dialect.format_drop_column_action(self)
            elif self.action_type == AlterTableActionType.ALTER_COLUMN:
                return dialect.format_alter_column_action(self)
            elif self.action_type == AlterTableActionType.ADD_CONSTRAINT:
                return dialect.format_add_table_constraint_action(self)
            elif self.action_type == AlterTableActionType.DROP_CONSTRAINT:
                return dialect.format_drop_table_constraint_action(self)
            elif self.action_type == AlterTableActionType.RENAME_COLUMN:
                return dialect.format_rename_column_action(self)
            elif self.action_type == AlterTableActionType.RENAME_TABLE:
                return dialect.format_rename_table_action(self)
            elif self.action_type == AlterTableActionType.ADD_INDEX:
                return dialect.format_add_index_action(self)
            elif self.action_type == AlterTableActionType.DROP_INDEX:
                return dialect.format_drop_index_action(self)
            else:
                # Handle unknown action types
                return f"PROCESS {type(self).__name__}", ()
        else:
            raise AttributeError("Dialect not set for AlterTableAction. "
                               "It should be set by the parent AlterTableExpression.")


@dataclass
class AddColumn(AlterTableAction):
    """Represents an 'ADD COLUMN' action per SQL standard."""
    column: ColumnDefinition
    action_type: AlterTableActionType = AlterTableActionType.ADD_COLUMN
    dialect_options: Optional[Dict[str, Any]] = None  # dialect-specific options


@dataclass
class DropColumn(AlterTableAction):
    """Represents a 'DROP COLUMN' action per SQL standard."""
    column_name: str
    action_type: AlterTableActionType = AlterTableActionType.DROP_COLUMN
    if_exists: bool = False  # Non-standard but widely supported
    dialect_options: Optional[Dict[str, Any]] = None  # dialect-specific options


from enum import Enum


class ColumnAlterOperation(Enum):
    """SQL standard column operation types"""
    SET_DEFAULT = "SET DEFAULT"
    DROP_DEFAULT = "DROP DEFAULT"
    SET_NOT_NULL = "SET NOT NULL"  # Non-standard but widely supported
    DROP_NOT_NULL = "DROP NOT NULL"  # Non-standard but widely supported


@dataclass
class AlterColumn(AlterTableAction):
    """Represents an 'ALTER COLUMN' action per SQL standard."""
    column_name: str
    operation: Union[ColumnAlterOperation, str]  # operation type
    action_type: AlterTableActionType = AlterTableActionType.ALTER_COLUMN
    new_value: Any = None  # default value, etc.
    cascade: bool = False  # For constraint modifications
    dialect_options: Optional[Dict[str, Any]] = None


@dataclass
class AddTableConstraint(AlterTableAction):
    """SQL standard ADD CONSTRAINT operation"""
    constraint: TableConstraint
    action_type: AlterTableActionType = AlterTableActionType.ADD_CONSTRAINT
    dialect_options: Optional[Dict[str, Any]] = None


@dataclass
class DropTableConstraint(AlterTableAction):
    """SQL standard DROP CONSTRAINT operation"""
    constraint_name: str
    action_type: AlterTableActionType = AlterTableActionType.DROP_CONSTRAINT
    cascade: bool = False  # For dialect implementation
    dialect_options: Optional[Dict[str, Any]] = None


@dataclass
class RenameColumn(AlterTableAction):
    """SQL standard RENAME COLUMN operation"""
    old_name: str
    new_name: str
    action_type: AlterTableActionType = AlterTableActionType.RENAME_COLUMN
    dialect_options: Optional[Dict[str, Any]] = None


@dataclass
class RenameTable(AlterTableAction):
    """SQL standard RENAME TABLE operation"""
    old_name: str
    new_name: str
    action_type: AlterTableActionType = AlterTableActionType.RENAME_TABLE
    dialect_options: Optional[Dict[str, Any]] = None


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
    dialect_options: Optional[Dict[str, Any]] = None  # dialect-specific options


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


@dataclass
class ColumnAlias:
    """Represents a column alias in a view definition."""
    name: str  # Column name
    alias: Optional[str] = None  # Optional alias for the column


class ViewAlgorithm(Enum):
    """Algorithm types for MySQL-style view creation."""
    UNDEFINED = "UNDEFINED"
    MERGE = "MERGE"
    TEMPTABLE = "TEMPTABLE"


class ViewCheckOption(Enum):
    """Check options for view constraints."""
    NONE = "NONE"
    LOCAL = "LOCAL"
    CASCADED = "CASCADED"


@dataclass
class ViewOptions:
    """Options for view creation, supporting various database-specific features."""
    algorithm: Optional[ViewAlgorithm] = None  # MySQL-specific
    definer: Optional[str] = None  # MySQL-specific (user@host)
    security: Optional[str] = None  # SQL SECURITY (DEFINER, INVOKER)
    schemabinding: bool = False  # SQL Server-specific
    encryption: bool = False  # SQL Server-specific
    materialized: bool = False  # PostgreSQL-like (for materialized views)
    recursive: bool = False  # For recursive CTE-based views
    force: bool = False  # Oracle-specific (create even if base tables don't exist)
    read_only: bool = False  # Oracle-specific
    check_option: Optional[ViewCheckOption] = None  # WITH CHECK OPTION variants
    dialect_options: Optional[Dict[str, Any]] = None  # Database-specific options


class CreateViewExpression(bases.BaseExpression):
    """
    Represents a CREATE VIEW statement supporting full SQL standard features and extensions.

    Views are virtual tables based on the result-set of a SELECT statement. They can be queried
    like regular tables but don't store data themselves. Views provide a way to simplify complex
    queries, enforce security, and abstract schema changes.

    Examples:
        # Basic view creation
        basic_view = CreateViewExpression(
            dialect,
            view_name="customer_info",
            query=QueryExpression(
                dialect,
                select=[Column(dialect, "id"), Column(dialect, "name"), Column(dialect, "email")],
                from_=TableExpression(dialect, "customers")
            )
        )

        # View with column aliases
        aliased_view = CreateViewExpression(
            dialect,
            view_name="user_summary",
            query=QueryExpression(
                dialect,
                select=[
                    Column(dialect, "user_id").alias("id"),
                    FunctionCall(dialect, "COUNT", Column(dialect, "order_id")).alias("total_orders")
                ],
                from_=TableExpression(dialect, "orders"),
                group_by=[Column(dialect, "user_id")]
            ),
            column_aliases=["id", "total_orders"]
        )

        # MySQL-style view with algorithm
        mysql_view = CreateViewExpression(
            dialect,
            view_name="optimized_view",
            query=some_query,
            options=ViewOptions(algorithm=ViewAlgorithm.MERGE)
        )
    """
    def __init__(self,
                 dialect: "SQLDialectBase",
                 view_name: str,
                 query: "QueryExpression",
                 column_aliases: Optional[List[Union[str, ColumnAlias]]] = None,
                 replace: bool = False,  # CREATE OR REPLACE
                 temporary: bool = False,  # CREATE TEMPORARY VIEW (some DBs)
                 options: Optional[ViewOptions] = None):
        super().__init__(dialect)
        self.view_name = view_name
        self.query = query
        self.column_aliases = column_aliases or []
        self.replace = replace  # Whether to use CREATE OR REPLACE semantics
        self.temporary = temporary  # Whether to create a temporary view
        self.options = options or ViewOptions()

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegates SQL generation for the CREATE VIEW statement to the configured dialect."""
        return self.dialect.format_create_view_statement(self)


class DropViewExpression(bases.BaseExpression):
    """
    Represents a DROP VIEW statement supporting standard and extended features.

    This class handles view deletion with options for different database systems.

    Examples:
        # Basic view drop
        drop_view = DropViewExpression(dialect, view_name="old_view")

        # Drop with IF EXISTS
        drop_safe = DropViewExpression(
            dialect,
            view_name="possibly_missing_view",
            if_exists=True
        )

        # Cascade drop (drops dependent objects)
        drop_cascade = DropViewExpression(
            dialect,
            view_name="master_view",
            cascade=True
        )
    """
    def __init__(self,
                 dialect: "SQLDialectBase",
                 view_name: str,
                 if_exists: bool = False,  # DROP VIEW IF EXISTS
                 cascade: bool = False):  # DROP VIEW ... CASCADE (drops dependent objects)
        super().__init__(dialect)
        self.view_name = view_name
        self.if_exists = if_exists
        self.cascade = cascade

    def to_sql(self) -> Tuple[str, tuple]:
        """Delegates SQL generation for the DROP VIEW statement to the configured dialect."""
        return self.dialect.format_drop_view_statement(self)


class TruncateExpression(bases.BaseExpression):
    """
    Represents a TRUNCATE TABLE statement supporting SQL standard and database-specific features.

    The TRUNCATE statement provides a fast way to delete all rows from a table.
    It's functionally similar to DELETE without a WHERE clause but is often more efficient
    as it doesn't log individual row deletions. Some databases also support
    additional options like RESTART IDENTITY to reset auto-increment counters.

    Basic syntax:
        TRUNCATE [TABLE] table_name

    Examples:
        # Basic truncate
        truncate_expr = TruncateExpression(dialect, table_name="users")

        # Truncate with restart identity (PostgreSQL)
        truncate_expr = TruncateExpression(
            dialect,
            table_name="users",
            restart_identity=True
        )

        # Truncate with cascade (PostgreSQL)
        truncate_expr = TruncateExpression(
            dialect,
            table_name="orders",
            cascade=True
        )
    """
    def __init__(self, dialect: "SQLDialectBase",
                 table_name: str,
                 restart_identity: bool = False,  # RESTART IDENTITY option (PostgreSQL)
                 cascade: bool = False,          # CASCADE option (PostgreSQL)
                 *,                             # Force keyword arguments
                 dialect_options: Optional[Dict[str, Any]] = None):
        """
        Initialize a TRUNCATE expression with the specified parameters.

        Args:
            dialect: The SQL dialect instance that determines query generation rules
            table_name: Name of the table to truncate
            restart_identity: Whether to restart identity counters (PostgreSQL-specific)
            cascade: Whether to truncate dependent tables as well (PostgreSQL-specific)
            dialect_options: Additional database-specific parameters
        """
        super().__init__(dialect)
        self.table_name = table_name
        self.restart_identity = restart_identity  # For PostgreSQL-style RESTART IDENTITY
        self.cascade = cascade  # For PostgreSQL-style CASCADE
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> Tuple[str, tuple]:
        """
        Generate the SQL string and parameters for this TRUNCATE expression.

        This method delegates the SQL generation to the configured dialect, allowing for
        database-specific variations in TRUNCATE syntax.

        Returns:
            A tuple containing:
            - str: The complete TRUNCATE SQL string
            - tuple: The parameter values for prepared statement execution (usually empty)
        """
        return self.dialect.format_truncate_statement(self)


class AlterTableExpression(bases.BaseExpression):
    """
    Represents a comprehensive ALTER TABLE statement supporting SQL standard functionality.

    The ALTER TABLE statement allows for modification of an existing table's structure,
    including adding/dropping columns, altering column properties, managing constraints
    and indexes, and renaming objects per SQL standard. Different SQL databases support
    different subsets of ALTER TABLE functionality, with variations in syntax.

    This class collects all ALTER TABLE parameters and delegates the actual SQL generation
    to a backend-specific dialect for database-specific syntax.

    Examples:
        # Add column
        alter_expr = AlterTableExpression(
            dialect,
            table_name="users",
            actions=[AddColumn(ColumnDefinition("email", "VARCHAR(100)"))]
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
                AddColumn(ColumnDefinition("status", "VARCHAR(20)")),
                RenameColumn("id", "order_id")
            ]
        )

        # Add constraint
        alter_expr = AlterTableExpression(
            dialect,
            table_name="users",
            actions=[
                AddTableConstraint(
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
                    operation=ColumnAlterOperation.SET_DEFAULT,
                    new_value="0.00"
                )
            ]
        )
    """
    def __init__(self, dialect: "SQLDialectBase",
                 table_name: str,
                 actions: List[Union[AlterTableAction, "AddTableConstraint", "DropTableConstraint",
                                   "RenameColumn", "RenameTable", "AlterColumn"]],
                 *,  # Force keyword arguments
                 dialect_options: Optional[Dict[str, Any]] = None):
        """
        Initialize an ALTER TABLE expression with the specified modifications per SQL standard.

        Args:
            dialect: The SQL dialect instance that determines query generation rules
            table_name: Name of the table to alter
            actions: List of actions to perform on the table (per SQL standard)
            dialect_options: Additional database-specific parameters

        Raises:
            ValueError: If required parameters are missing or invalid
        """
        super().__init__(dialect)
        self.table_name = table_name
        # Inject dialect to all actions for ToSQLProtocol compliance
        self.actions = []
        for action in actions:
            action._dialect = dialect
            self.actions.append(action)
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> Tuple[str, tuple]:
        """
        Generate the SQL string and parameters for this ALTER TABLE expression per SQL standard.

        This method delegates the SQL generation to the configured dialect, allowing for
        database-specific variations in ALTER TABLE syntax while maintaining standard compliance.

        Returns:
            A tuple containing:
            - str: The complete ALTER TABLE SQL string
            - tuple: The parameter values for prepared statement execution
        """
        return self.dialect.format_alter_table_statement(self)

# endregion DDL Expressions