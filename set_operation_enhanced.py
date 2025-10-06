# src/rhosocial/activerecord/query/set_operation.py
"""Set operation query implementation supporting full SQL standard.

This module provides comprehensive support for SQL set operations (UNION, INTERSECT, 
EXCEPT) with full integration into the query builder ecosystem.

Query Mixin Inheritance Hierarchy:
    BaseQueryMixin (base query operations: WHERE, ORDER BY, LIMIT)
        └── AggregateQueryMixin (GROUP BY, HAVING, expressions)
            ├── CTEQueryMixin (WITH clause support)  
            │   └── ActiveQuery (complete query builder)
            └── SetOperationQuery (this class - set operations)

SetOperationQuery inherits from AggregateQueryMixin rather than CTEQueryMixin because:
1. Set operation results often need aggregation (GROUP BY, HAVING)
2. Set operations can BE USED AS CTEs but don't need to CREATE CTEs
3. This avoids circular dependencies and keeps responsibilities clear
4. The result of a set operation is a new temporary result set that can be
   treated like a table for further operations
"""

import logging
from typing import List, Optional, Union, Tuple, Dict, Any, Type
from abc import ABC, abstractmethod
from enum import Enum

from ..interface import IQuery, ModelT
from ..backend.errors import SetOperationNotSupported
from .base import BaseQueryMixin
from .aggregate import AggregateQueryMixin


class SetOperationType(Enum):
    """Enum for set operation types."""
    UNION = "UNION"
    INTERSECT = "INTERSECT"
    EXCEPT = "EXCEPT"
    MINUS = "MINUS"  # Oracle-specific alias for EXCEPT


class SetOperationQuery(AggregateQueryMixin[ModelT]):
    """
    Set operation query representing a temporary result set.
    
    This class implements the full SQL standard for set operations including:
    - Basic set operations (UNION, INTERSECT, EXCEPT/MINUS)
    - ALL/DISTINCT control for duplicates
    - Multiple set operations with parentheses for precedence
    - Nested set operations of arbitrary depth
    - Integration with CTEs, aggregates, and subqueries
    - Support for ORDER BY/LIMIT in subqueries (when valid)
    - Post-operation WHERE/GROUP BY/HAVING/ORDER BY/LIMIT
    - Full EXPLAIN support (inherited from BaseQueryMixin)
    - Conversion to subquery for JOIN operations
    
    SQL Format Examples:
        Basic UNION:
            (SELECT * FROM users WHERE status = 'active')
            UNION
            (SELECT * FROM users WHERE status = 'premium')
        
        With ALL and result filtering:
            (SELECT id, name FROM employees WHERE dept = 'A')
            UNION ALL
            (SELECT id, name FROM employees WHERE dept = 'B')
            ORDER BY name
            LIMIT 10
        
        Complex nested operations:
            ((SELECT * FROM t1) UNION (SELECT * FROM t2))
            INTERSECT
            (SELECT * FROM t3)
            
        With aggregation on result:
            SELECT dept, COUNT(*) as cnt
            FROM (
                (SELECT * FROM employees WHERE year = 2023)
                UNION ALL
                (SELECT * FROM employees WHERE year = 2024)
            ) AS combined
            GROUP BY dept
            HAVING COUNT(*) > 5
    
    The query represents a new result set independent of the source queries,
    but can have additional conditions applied to it.
    """
    
    def __init__(self, 
                 left_query: IQuery[ModelT],
                 right_query: IQuery[ModelT],
                 operation: SetOperationType,
                 all: bool = False,
                 model_class: Optional[Type[ModelT]] = None):
        """
        Initialize a set operation query.
        
        Args:
            left_query: Left operand query (can be any IQuery implementation)
            right_query: Right operand query  
            operation: Type of set operation
            all: Whether to keep duplicates (ALL) or remove them (DISTINCT/default)
            model_class: Model class for backend access (defaults to left query's)
        """
        # Use provided model_class or inherit from left query
        used_model = model_class or left_query.model_class
        super().__init__(used_model)
        
        # Store operation components
        self._left_query = left_query
        self._right_query = right_query
        self._operation = operation
        self._all = all
        
        # Mark as temporary result set
        self._is_temp_resultset = True
        self._is_set_operation = True
        
        # Additional set operations for chaining (for multi-operation queries)
        self._additional_operations: List[Dict[str, Any]] = []
        
        # Result schema analysis
        self._result_columns = None
        self._column_types = None
        self._analyze_result_schema()
        
        # Reset inherited state since this is a new result set
        self._reset_query_state()
        
        # Subquery alias for JOIN operations
        self._subquery_alias = None
    
    def _reset_query_state(self):
        """
        Reset query state as set operations create a new result set.
        
        Clears all conditions from parent queries but allows new ones
        to be added to the result set.
        """
        self.select_columns = None  # Determined by operand queries
        self.condition_groups = [[]]  # Can add WHERE to result
        self.order_clauses = []  # Can add ORDER BY to result
        self.join_clauses = []  # Cannot JOIN on set operation result directly
        self.limit_count = None  # Can limit result
        self.offset_count = None  # Can offset result
        
        # Aggregate-specific state (from AggregateQueryMixin)
        self._group_columns = []  # Can GROUP BY on result
        self._having_conditions = []  # Can add HAVING on result
        self._expressions = []  # Can add expressions on result
        
        # EXPLAIN state is preserved from BaseQueryMixin
        # No need to reset as it's query-specific
    
    def _analyze_result_schema(self):
        """
        Analyze the result set schema from operand queries.
        
        Validates column compatibility and determines result columns.
        Following SQL standard: result uses left query's column names.
        """
        left_cols = self._extract_columns(self._left_query)
        right_cols = self._extract_columns(self._right_query)
        
        # Validate column count match (SQL requirement)
        if left_cols and right_cols and len(left_cols) != len(right_cols):
            self._log(logging.WARNING,
                f"Column count mismatch in set operation: "
                f"left has {len(left_cols)}, right has {len(right_cols)}")
        
        # Result columns come from left query (SQL standard)
        self._result_columns = left_cols
    
    def _extract_columns(self, query: IQuery) -> Optional[List[str]]:
        """
        Extract column information from a query.
        
        Different query types require different extraction strategies:
        - Basic queries: from select_columns
        - Aggregate queries: from expressions and group columns
        - Set operation queries: from _result_columns
        - CTE queries: from CTE definition
        
        Args:
            query: Query to extract columns from
            
        Returns:
            List of column names or None if not determinable
        """
        if isinstance(query, SetOperationQuery):
            return query._result_columns
        
        # Check for explicit select columns
        if hasattr(query, 'select_columns') and query.select_columns:
            return query.select_columns
        
        # Check for aggregate expressions
        if hasattr(query, '_expressions') and query._expressions:
            columns = []
            # Add group by columns first
            if hasattr(query, '_group_columns'):
                columns.extend(query._group_columns)
            # Add expression aliases
            for expr in query._expressions:
                if hasattr(expr, 'alias') and expr.alias:
                    columns.append(expr.alias)
            return columns if columns else None
        
        # Default: cannot determine columns
        return None
    
    def union(self, other: IQuery[ModelT], all: bool = False) -> 'SetOperationQuery[ModelT]':
        """
        Chain another UNION operation.
        
        Creates: (self) UNION [ALL] (other)
        
        SQL Format:
            ((previous operations)) UNION [ALL] (SELECT ...)
        
        Args:
            other: Query to union with
            all: Whether to keep duplicates
            
        Returns:
            New SetOperationQuery with chained operation
        """
        new_query = SetOperationQuery(
            self, other, SetOperationType.UNION, all, self.model_class
        )
        return new_query
    
    def intersect(self, other: IQuery[ModelT], all: bool = False) -> 'SetOperationQuery[ModelT]':
        """
        Chain an INTERSECT operation.
        
        Creates: (self) INTERSECT [ALL] (other)
        
        SQL Format:
            ((previous operations)) INTERSECT [ALL] (SELECT ...)
        
        Args:
            other: Query to intersect with
            all: Whether to keep duplicates (rarely supported)
            
        Returns:
            New SetOperationQuery with chained operation
        """
        new_query = SetOperationQuery(
            self, other, SetOperationType.INTERSECT, all, self.model_class
        )
        return new_query
    
    def except_(self, other: IQuery[ModelT], all: bool = False) -> 'SetOperationQuery[ModelT]':
        """
        Chain an EXCEPT operation.
        
        Creates: (self) EXCEPT [ALL] (other)
        
        SQL Format:
            ((previous operations)) EXCEPT [ALL] (SELECT ...)
        
        Args:
            other: Query to subtract
            all: Whether to keep duplicates
            
        Returns:
            New SetOperationQuery with chained operation
        """
        new_query = SetOperationQuery(
            self, other, SetOperationType.EXCEPT, all, self.model_class
        )
        return new_query
    
    def minus(self, other: IQuery[ModelT], all: bool = False) -> 'SetOperationQuery[ModelT]':
        """
        Chain a MINUS operation (Oracle-style alias for EXCEPT).
        
        SQL Format:
            ((previous operations)) MINUS [ALL] (SELECT ...)
        
        Args:
            other: Query to subtract
            all: Whether to keep duplicates
            
        Returns:
            New SetOperationQuery with chained operation
        """
        # MINUS is just an alias for EXCEPT in Oracle
        return self.except_(other, all)
    
    def _check_operation_support(self) -> bool:
        """
        Check if the backend supports the requested operation.
        
        Returns:
            True if supported, False otherwise
        """
        dialect = self.model_class.backend().dialect
        
        # Check for set operation handler
        if not hasattr(dialect, 'set_operation_handler'):
            # Default: only UNION is universally supported
            return self._operation == SetOperationType.UNION
        
        handler = dialect.set_operation_handler
        
        # Check specific operation support
        if self._operation == SetOperationType.UNION:
            return handler.supports_union
        elif self._operation == SetOperationType.INTERSECT:
            return handler.supports_intersect
        elif self._operation in (SetOperationType.EXCEPT, SetOperationType.MINUS):
            return handler.supports_except
        
        return False
    
    def build(self) -> Tuple[str, tuple]:
        """
        Build the complete SQL query with parameters.
        
        SQL Format:
            Basic:
                (SELECT ...) UNION [ALL] (SELECT ...) [ORDER BY ...] [LIMIT ...]
            
            With WHERE/GROUP BY on result:
                SELECT * FROM (
                    (SELECT ...) UNION [ALL] (SELECT ...)
                ) AS _set_result
                WHERE ...
                GROUP BY ...
                HAVING ...
                ORDER BY ...
                LIMIT ...
            
            Nested operations:
                ((SELECT ...) UNION (SELECT ...)) INTERSECT (SELECT ...)
            
            With EXPLAIN:
                EXPLAIN [ANALYZE] [FORMAT JSON] (complete query)
        
        Returns:
            Tuple of (sql_query, parameters)
            
        Raises:
            SetOperationNotSupported: If operation not supported by backend
        """
        # Check operation support
        if not self._check_operation_support():
            raise SetOperationNotSupported(
                f"{self._operation.value} not supported by "
                f"{self.model_class.backend().__class__.__name__}"
            )
        
        # Get dialect handler
        dialect = self.model_class.backend().dialect
        if hasattr(dialect, 'set_operation_handler'):
            handler = dialect.set_operation_handler
            sql, params = handler.build_set_operation(
                self._left_query,
                self._right_query,
                self._operation,
                self._all,
                self._build_result_clauses()
            )
        else:
            # Fallback: basic implementation
            sql, params = self._build_basic_set_operation()
        
        # Apply EXPLAIN if enabled (inherited from BaseQueryMixin)
        if hasattr(self, '_explain_enabled') and self._explain_enabled:
            sql = self._build_explain_prefix() + sql
        
        return sql, params
    
    def _build_basic_set_operation(self) -> Tuple[str, tuple]:
        """
        Build basic set operation SQL (fallback implementation).
        
        SQL Format:
            (left_query) OPERATION [ALL] (right_query)
        
        Used when no dialect-specific handler is available.
        
        Returns:
            Tuple of (sql_query, parameters)
        """
        # Build operand queries
        left_sql, left_params = self._wrap_query(self._left_query)
        right_sql, right_params = self._wrap_query(self._right_query)
        
        # Build operation keyword
        op_keyword = self._operation.value
        if self._all:
            op_keyword += " ALL"
        
        # Combine queries
        base_sql = f"{left_sql} {op_keyword} {right_sql}"
        all_params = list(left_params) + list(right_params)
        
        # Apply result clauses
        final_sql, final_params = self._apply_result_clauses(base_sql, all_params)
        
        return final_sql, tuple(final_params)
    
    def _wrap_query(self, query: IQuery) -> Tuple[str, tuple]:
        """
        Wrap a query with parentheses if needed.
        
        Args:
            query: Query to wrap
            
        Returns:
            Tuple of (wrapped_sql, parameters)
        """
        sql, params = query.build()
        
        # Determine if parentheses are needed
        needs_parens = self._needs_parentheses(query, sql)
        
        if needs_parens:
            sql = f"({sql})"
        
        return sql, params
    
    def _needs_parentheses(self, query: IQuery, sql: str) -> bool:
        """
        Determine if a query needs parentheses in set operation.
        
        Rules:
        - Set operations always need parentheses (for nesting)
        - Simple SELECT usually needs parentheses
        - CTEs with WITH clause don't need extra parentheses
        
        Args:
            query: Query object
            sql: Generated SQL string
            
        Returns:
            True if parentheses are needed
        """
        # Set operations always need parentheses for proper nesting
        if isinstance(query, SetOperationQuery):
            return True
        
        # Check if SQL already starts with parenthesis or WITH
        sql_trimmed = sql.strip()
        if sql_trimmed.startswith('(') and sql_trimmed.endswith(')'):
            return False
        if sql_trimmed.upper().startswith('WITH '):
            return False
        
        # Default: add parentheses for safety
        return True
    
    def _build_result_clauses(self) -> Dict[str, Any]:
        """
        Build additional clauses for the result set.
        
        Returns:
            Dictionary with WHERE, GROUP BY, HAVING, ORDER BY, LIMIT clauses
        """
        clauses = {}
        
        # WHERE clause
        if any(group for group in self.condition_groups):
            clauses['where'] = self._build_where()
        else:
            clauses['where'] = (None, [])
        
        # GROUP BY and HAVING
        if self._group_columns or self._having_conditions:
            clauses['group_by'] = self._build_group_by()
        else:
            clauses['group_by'] = (None, [])
        
        # ORDER BY
        clauses['order_by'] = self._build_order() if self.order_clauses else None
        
        # LIMIT/OFFSET
        clauses['limit_offset'] = self._build_limit_offset() if self.limit_count else None
        
        return clauses
    
    def _apply_result_clauses(self, base_sql: str, params: List) -> Tuple[str, List]:
        """
        Apply additional clauses to the set operation result.
        
        SQL Format when WHERE/GROUP BY present:
            SELECT * FROM (base_sql) AS _set_result
            WHERE ...
            GROUP BY ...
            HAVING ...
            ORDER BY ...
            LIMIT ...
        
        Args:
            base_sql: Base set operation SQL
            params: Current parameters
            
        Returns:
            Tuple of (final_sql, final_params)
        """
        clauses = self._build_result_clauses()
        
        # If we have WHERE or GROUP BY, wrap as subquery
        where_sql, where_params = clauses['where']
        group_sql, group_params = clauses['group_by']
        
        if where_sql or group_sql:
            # Need to wrap as subquery
            sql = f"SELECT * FROM ({base_sql}) AS _set_result"
            
            if where_sql:
                sql += f" {where_sql}"
                params.extend(where_params)
            
            if group_sql:
                sql += f" {group_sql}"
                params.extend(group_params)
        else:
            sql = base_sql
        
        # ORDER BY and LIMIT can be applied directly
        if clauses['order_by']:
            sql += f" {clauses['order_by']}"
        
        if clauses['limit_offset']:
            sql += f" {clauses['limit_offset']}"
        
        return sql, params
    
    def get_query_metadata(self) -> Dict[str, Any]:
        """
        Provide metadata about the query for upstream consumers.
        
        Returns:
            Dictionary with query metadata including columns, type, etc.
        """
        return {
            'type': 'set_operation',
            'operation': self._operation.value,
            'columns': self._result_columns,
            'is_temp_resultset': True,
            'supports_model_mapping': False,
            'supports_explain': True,  # Inherited from BaseQueryMixin
            'supports_subquery': True,  # Can be used as subquery
            'has_additional_clauses': any([
                any(self.condition_groups),
                self._group_columns,
                self._having_conditions,
                self.order_clauses,
                self.limit_count
            ])
        }
    
    def as_subquery(self, alias: str) -> str:
        """
        Format this set operation as a subquery for use in other queries.
        
        SQL Format:
            (complete_set_operation_sql) AS alias
        
        This method is essential for using set operation results in JOIN operations.
        
        Args:
            alias: Alias for the subquery
            
        Returns:
            SQL string for use as subquery
            
        Example:
            # Create a set operation
            special_users = active_users.union(premium_users)
            
            # Use in a JOIN
            orders = Order.query()\\
                .join(f"JOIN {special_users.as_subquery('su')} ON orders.user_id = su.id")\\
                .all()
        """
        sql, _ = self.build()
        self._subquery_alias = alias
        return f"({sql}) AS {alias}"
    
    def to_cte(self, name: str, recursive: bool = False) -> Tuple[str, tuple]:
        """
        Convert this set operation to a CTE definition.
        
        SQL Format:
            name AS (complete_set_operation_sql)
        
        Useful for complex queries where the set operation result
        needs to be referenced multiple times.
        
        Args:
            name: CTE name
            recursive: Whether this is part of a recursive CTE
            
        Returns:
            Tuple of (CTE definition SQL, parameters)
            
        Example:
            special_users = active_users.union(premium_users)
            cte_sql, params = special_users.to_cte('special_users')
            
            # Use in a WITH clause
            query = Order.query()\\
                .with_cte('special_users', special_users)\\
                .from_cte('special_users')
        """
        sql, params = self.build()
        
        if recursive:
            return f"{name} AS ({sql})", params
        else:
            return f"{name} AS ({sql})", params
    
    def as_exists_subquery(self) -> Tuple[str, tuple]:
        """
        Format as an EXISTS subquery.
        
        SQL Format:
            (complete_set_operation_sql)
        
        Returns:
            Tuple of (EXISTS clause SQL, parameters)
            
        Example:
            special = active_users.union(premium_users)
            exists_sql, params = special.as_exists_subquery()
            
            # Use in WHERE EXISTS
            orders = Order.query()\\
                .where(f"EXISTS {exists_sql}", params)\\
                .all()
        """
        sql, params = self.build()
        return f"({sql})", params
    
    def as_in_subquery(self, column: str = None) -> Tuple[str, tuple]:
        """
        Format as an IN subquery.
        
        SQL Format:
            (complete_set_operation_sql)
        
        Args:
            column: Column to select for IN clause (defaults to first column)
            
        Returns:
            Tuple of (IN subquery SQL, parameters)
            
        Example:
            special = active_users.union(premium_users).select('id')
            in_sql, params = special.as_in_subquery()
            
            # Use in WHERE IN
            orders = Order.query()\\
                .where(f"user_id IN {in_sql}", params)\\
                .all()
        """
        # If specific column requested, modify selection
        if column and self._result_columns:
            # Create a copy to avoid modifying original
            import copy
            query_copy = copy.copy(self)
            query_copy.select_columns = [column]
            sql, params = query_copy.build()
        else:
            sql, params = self.build()
        
        return f"({sql})", params
    
    def all(self) -> Union[List[Dict[str, Any]], str]:
        """
        Execute query and return all results.
        
        Set operations return dictionaries by default since results
        may not map cleanly to model instances.
        
        If EXPLAIN is enabled, returns the execution plan instead.
        
        Returns:
            List of result dictionaries or execution plan string
        """
        sql, params = self.build()
        
        # Check if EXPLAIN is enabled (inherited from BaseQueryMixin)
        if hasattr(self, '_explain_enabled') and self._explain_enabled:
            self._log(logging.INFO, f"Executing EXPLAIN for set operation: {sql}")
            return self._execute_with_explain(sql, params)
        
        self._log(logging.INFO, f"Executing set operation: {sql}")
        return self.model_class.backend().fetch_all(sql, params)
    
    def one(self) -> Union[Optional[Dict[str, Any]], str]:
        """
        Execute query and return first result as dictionary.
        
        If EXPLAIN is enabled, returns the execution plan instead.
        
        Returns:
            First result dictionary or None if no results
            Execution plan string if EXPLAIN is enabled
        """
        # Temporarily set limit
        original_limit = self.limit_count
        self.limit(1)
        
        results = self.all()
        
        # Restore original limit
        self.limit_count = original_limit
        
        # Handle EXPLAIN results
        if isinstance(results, str):
            return results
        
        return results[0] if results else None
    
    def count(self) -> Union[int, str]:
        """
        Count the number of rows in the set operation result.
        
        SQL Format:
            SELECT COUNT(*) AS cnt FROM (set_operation_sql) AS _count_subq
        
        If EXPLAIN is enabled, returns the execution plan instead.
        
        Returns:
            Row count or execution plan string
        """
        # Wrap the set operation as a subquery for counting
        base_sql, params = self.build()
        count_sql = f"SELECT COUNT(*) AS cnt FROM ({base_sql}) AS _count_subq"
        
        # Handle EXPLAIN
        if hasattr(self, '_explain_enabled') and self._explain_enabled:
            explain_sql = self._build_explain_prefix() + count_sql
            self._log(logging.INFO, f"Executing EXPLAIN for COUNT: {explain_sql}")
            return self.model_class.backend().fetch_one(explain_sql, params)
        
        self._log(logging.INFO, f"Executing COUNT on set operation: {count_sql}")
        result = self.model_class.backend().fetch_one(count_sql, params)
        return result['cnt'] if result else 0
    
    def exists(self) -> Union[bool, str]:
        """
        Check if the set operation returns any results.
        
        If EXPLAIN is enabled, returns the execution plan instead.
        
        Returns:
            True if results exist, False otherwise
            Execution plan string if EXPLAIN is enabled
        """
        # Use LIMIT 1 for efficiency
        original_limit = self.limit_count
        self.limit(1)
        
        result = self.one()
        
        # Restore original limit
        self.limit_count = original_limit
        
        # Handle EXPLAIN results
        if isinstance(result, str):
            return result
        
        return result is not None
    
    def to_dict(self, **kwargs) -> 'SetOperationQuery':
        """
        Compatibility method - set operations already return dictionaries.
        
        Returns:
            Self (no-op for set operations)
        """
        return self


class SetOperationQueryMixin(BaseQueryMixin[ModelT]):
    """
    Mixin to add set operation methods to queries.
    
    Allows any query to initiate set operations that produce
    independent SetOperationQuery instances.
    
    All queries support EXPLAIN through inheritance from BaseQueryMixin,
    and set operations can be used as subqueries for JOIN operations.
    """
    
    def union(self, other: IQuery[ModelT], all: bool = False) -> SetOperationQuery[ModelT]:
        """
        Create a UNION with another query.
        
        SQL Format:
            (this_query) UNION [ALL] (other_query)
        
        The result is a new SetOperationQuery that represents the
        union of this query and the other, independent of both.
        
        Args:
            other: Query to union with
            all: If True, keeps duplicates (UNION ALL)
            
        Returns:
            New SetOperationQuery instance
        """
        return SetOperationQuery(self, other, SetOperationType.UNION, all)
    
    def intersect(self, other: IQuery[ModelT], all: bool = False) -> SetOperationQuery[ModelT]:
        """
        Create an INTERSECT with another query.
        
        SQL Format:
            (this_query) INTERSECT [ALL] (other_query)
        
        Returns only rows that appear in both queries.
        
        Args:
            other: Query to intersect with
            all: If True, keeps duplicate intersections (rarely supported)
            
        Returns:
            New SetOperationQuery instance
        """
        return SetOperationQuery(self, other, SetOperationType.INTERSECT, all)
    
    def except_(self, other: IQuery[ModelT], all: bool = False) -> SetOperationQuery[ModelT]:
        """
        Create an EXCEPT with another query.
        
        SQL Format:
            (this_query) EXCEPT [ALL] (other_query)
        
        Returns rows from this query that don't appear in the other.
        
        Args:
            other: Query to subtract
            all: If True, keeps duplicates in result
            
        Returns:
            New SetOperationQuery instance
        """
        return SetOperationQuery(self, other, SetOperationType.EXCEPT, all)
    
    def minus(self, other: IQuery[ModelT], all: bool = False) -> SetOperationQuery[ModelT]:
        """
        Create a MINUS with another query (Oracle-style).
        
        SQL Format:
            (this_query) MINUS [ALL] (other_query)
        
        Alias for except_() to support Oracle syntax.
        
        Args:
            other: Query to subtract
            all: If True, keeps duplicates in result
            
        Returns:
            New SetOperationQuery instance
        """
        return SetOperationQuery(self, other, SetOperationType.MINUS, all)


class SetOperationHandler(ABC):
    """
    Abstract base class for database-specific set operation handling.
    
    Each database backend should implement this to handle:
    - Operation support detection
    - Dialect-specific syntax generation
    - Workarounds for unsupported operations
    - EXPLAIN support for set operations
    """
    
    @property
    @abstractmethod
    def supports_union(self) -> bool:
        """Check if UNION is supported (usually True)."""
        pass
    
    @property
    @abstractmethod
    def supports_intersect(self) -> bool:
        """Check if INTERSECT is supported."""
        pass
    
    @property
    @abstractmethod
    def supports_except(self) -> bool:
        """Check if EXCEPT/MINUS is supported."""
        pass
    
    @abstractmethod
    def build_set_operation(self,
                          left_query: IQuery,
                          right_query: IQuery,
                          operation: SetOperationType,
                          all: bool,
                          result_clauses: Dict[str, Any]) -> Tuple[str, tuple]:
        """
        Build database-specific set operation SQL.
        
        Args:
            left_query: Left operand query
            right_query: Right operand query
            operation: Type of set operation
            all: Whether to keep duplicates
            result_clauses: Additional clauses for result set
            
        Returns:
            Tuple of (sql, parameters)
        """
        pass
    
    def format_operation(self, operation: SetOperationType, all: bool) -> str:
        """
        Format the operation keyword for this database.
        
        Args:
            operation: Operation type
            all: Whether to add ALL keyword
            
        Returns:
            Formatted operation keyword
        """
        keyword = operation.value
        
        # Handle MINUS vs EXCEPT
        if operation == SetOperationType.EXCEPT and self.use_minus_keyword:
            keyword = "MINUS"
        
        if all:
            keyword += " ALL"
        
        return keyword
    
    @property
    def use_minus_keyword(self) -> bool:
        """Whether to use MINUS instead of EXCEPT (e.g., Oracle)."""
        return False
    
    def supports_explain_analyze(self) -> bool:
        """Check if EXPLAIN ANALYZE is supported for set operations."""
        return True  # Most modern databases support this