# src/rhosocial/activerecord/backend/expression/statements/dql.py
"""DQL (Data Query Language) statement expressions."""

from enum import Enum
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING

from ..bases import BaseExpression, SQLPredicate, SQLQueryAndParams, SQLValueExpression
from ..core import Subquery, TableExpression
from ..mixins import ArithmeticMixin, ComparisonMixin
from ..query_parts import (
    WhereClause,
    GroupByHavingClause,
    OrderByClause,
    QualifyClause,
    LimitOffsetClause,
    ForUpdateClause,
)
from ._types import FromSourceType
from ...schema import StatementType

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


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


class QueryExpression(ArithmeticMixin, ComparisonMixin, SQLValueExpression):
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
            group_by_having=GroupByHavingClause(
                dialect, group_by=[Column(dialect, "category")],
                having=FunctionCall(dialect, "COUNT", Column(dialect, "id")) > Literal(dialect, 5)
            ),
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
            order_by=OrderByClause(
                dialect, expressions=[Column(dialect, "department"), (Column(dialect, "row_num"), "ASC")]
            )
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

    def __init__(
        self,
        dialect: "SQLDialectBase",
        select: List["BaseExpression"],  # SELECT clause - required, list of selected expressions
        from_: Optional[
            Union[  # FROM clause - optional, but determines the nature of the query
                FromSourceType,  # Single data source type
                # List of data source types (for comma-separated FROM clause - implicit CROSS JOIN)
                List[FromSourceType],
            ]
        ] = None,
        where: Optional[Union["SQLPredicate", "WhereClause"]] = None,  # WHERE condition or clause object
        group_by_having: Optional["GroupByHavingClause"] = None,  # Combined GROUP BY/HAVING clause object
        order_by: Optional["OrderByClause"] = None,  # ORDER BY clause object
        qualify: Optional["QualifyClause"] = None,  # QUALIFY clause object
        limit_offset: Optional["LimitOffsetClause"] = None,  # Combined LIMIT/OFFSET clause object
        for_update: Optional["ForUpdateClause"] = None,  # FOR UPDATE clause object
        select_modifier: Optional[SelectModifier] = None,  # SELECT modifier - DISTINCT|ALL, None means no modifier
        *,  # Force keyword arguments
        dialect_options: Optional[Dict[str, Any]] = None,
    ):  # Dialect-specific options - optional
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
                   1. Pass a list of expressions (equivalent to comma-separated tables in
                      FROM clause, creates implicit CROSS JOIN)
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
            return isinstance(item, (str, TableExpression, Subquery)) or type(item).__name__ in [
                "SetOperationExpression",
                "JoinExpression",
                "ValuesExpression",
                "TableFunctionExpression",
                "LateralExpression",
            ]

        if self.from_ is not None:
            if isinstance(self.from_, list):
                # If it's a list, validate each element in the list
                for i, item in enumerate(self.from_):
                    if not _is_valid_from_source(item):
                        raise TypeError(
                            f"from_ list item at index {i} must be one of: str, TableExpression, "
                            f"Subquery, SetOperationExpression, JoinExpression, ValuesExpression, "
                            f"TableFunctionExpression, LateralExpression, got {type(item)}"
                        )
            else:
                # For single values, validate using the same helper
                if not _is_valid_from_source(self.from_):
                    raise TypeError(
                        f"from_ must be one of: str, TableExpression, Subquery, SetOperationExpression, "
                        f"JoinExpression, list, ValuesExpression, TableFunctionExpression, "
                        f"LateralExpression, got {type(self.from_)}"
                    )

        # Validate where parameter
        if self.where is not None and not isinstance(self.where, (WhereClause, SQLPredicate)):
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

    @property
    def statement_type(self) -> StatementType:
        """Return the statement type for this query expression."""
        return StatementType.DQL

    def to_sql(self) -> "SQLQueryAndParams":
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
