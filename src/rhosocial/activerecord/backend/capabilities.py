# src/rhosocial/activerecord/backend/capabilities.py
"""
Capability Negotiation System

This module implements a comprehensive capability negotiation mechanism that allows:
1. Database backends to declare their specific capabilities
2. Tests and application code to check for feature support before using features
3. Fine-grained feature detection based on database version and configuration

The system uses a hierarchical approach with bit flags for efficient capability checking,
and provides both category-level and specific feature-level checks.

Why Capability Negotiation?
---------------------------
Different database systems (SQLite, MySQL, PostgreSQL, etc.) have varying levels of support
for SQL features. Even different versions of the same database may support different features.
Rather than hardcoding version checks throughout the codebase or having tests fail unpredictably,
this system allows each backend to declare exactly what it supports, and the tests and application
code can check for capabilities before using features.

The capability system serves as a "contract" between backends and tests:
- Backends declare what they support
- Tests check for required capabilities before running
- Application code can adapt behavior based on available capabilities

This approach provides several benefits:
1. Single source of truth for feature support
2. Type-safe capability checking
3. Efficient runtime evaluation using bit flags
4. Clear separation between backend implementations and tests
5. Easy extension for new capabilities
"""

from enum import Flag, auto
from typing import Union, List


class CapabilityCategory(Flag):
    """Top-level capability categories.
    
    These represent broad categories of database functionality. Each category
    contains specific capabilities that can be checked individually.
    """
    NONE = 0
    SET_OPERATIONS = auto()
    WINDOW_FUNCTIONS = auto()
    ADVANCED_GROUPING = auto()
    CTE = auto()
    JSON_OPERATIONS = auto()
    RETURNING_CLAUSE = auto()
    TRANSACTION_FEATURES = auto()
    BULK_OPERATIONS = auto()
    CONSTRAINTS = auto()
    PARTITIONING = auto()
    FULL_TEXT_SEARCH = auto()
    SPATIAL_OPERATIONS = auto()
    SECURITY_FEATURES = auto()
    JOIN_OPERATIONS = auto()
    AGGREGATE_FUNCTIONS = auto()
    DATETIME_FUNCTIONS = auto()
    STRING_FUNCTIONS = auto()
    MATHEMATICAL_FUNCTIONS = auto()


class SetOperationCapability(Flag):
    """Represents different SQL set operations.

    This category distinguishes between operations that implicitly remove
    duplicates (e.g., `UNION`, `INTERSECT`) and those that do not
    (e.g., `UNION ALL`, `INTERSECT ALL`). Not all database engines
    support the `ALL` variant for every set operation (e.g., older
    SQLite versions support `UNION ALL` but not `INTERSECT ALL` or
    `EXCEPT ALL`), making fine-grained checks necessary.
    """
    NONE = 0
    UNION = auto()
    UNION_ALL = auto()
    INTERSECT = auto()
    INTERSECT_ALL = auto()
    EXCEPT = auto()
    EXCEPT_ALL = auto()


class WindowFunctionCapability(Flag):
    """Represents support for various SQL window functions.

    Window functions are a significant feature for analytical queries, but they
    were introduced at different times in different databases. For example,
    SQLite added support in version 3.25.0, while older versions of MySQL
    (before 8.0) lacked them entirely. Furthermore, even among databases
    that support window functions, the specific set of available functions
    (e.g., `NTH_VALUE`, `CUME_DIST`) can vary.
    """
    NONE = 0
    ROW_NUMBER = auto()
    RANK = auto()
    DENSE_RANK = auto()
    LAG = auto()
    LEAD = auto()
    FIRST_VALUE = auto()
    LAST_VALUE = auto()
    NTH_VALUE = auto()
    CUME_DIST = auto()
    PERCENT_RANK = auto()
    NTILE = auto()


class AdvancedGroupingCapability(Flag):
    """Represents advanced SQL grouping operations, often used in OLAP.

    These features extend the standard `GROUP BY` clause to allow for more
    complex aggregations. Support is highly database-dependent. For instance,
    PostgreSQL and Oracle have robust support, whereas MySQL introduced `ROLLUP`
    in version 5.7 and `CUBE` only in 8.0. SQLite, being a more lightweight
    database, does not support these at all. This makes checking essential
    before attempting to generate such queries.
    """
    NONE = 0
    CUBE = auto()
    ROLLUP = auto()
    GROUPING_SETS = auto()


class CTECapability(Flag):
    """Represents different features related to Common Table Expressions (CTEs).

    CTEs (defined with the `WITH` clause) are a powerful tool for structuring
    complex queries. While basic CTEs are now common, support for advanced
    features varies. `RECURSIVE` CTEs are not universally available.
    Furthermore, the ability to use CTEs within DML statements (e.g.,
    `WITH ... UPDATE`) or to provide optimizer hints (`MATERIALIZED` vs.
    `NOT MATERIALIZED`) is often specific to particular databases like
    PostgreSQL.
    """
    NONE = 0
    BASIC_CTE = auto()
    RECURSIVE_CTE = auto()
    COMPOUND_RECURSIVE_CTE = auto()
    CTE_IN_DML = auto()
    MATERIALIZED_CTE = auto()


class JSONCapability(Flag):
    """Represents different JSON operations that may be supported by a database.

    JSON support is highly variable across databases. This includes not
    only the availability of specific functions for querying and manipulating
    JSON data, but also support for optimized binary JSON formats (like
    `JSONB` in PostgreSQL or as introduced in SQLite 3.45.0), which can
    significantly impact performance.
    """
    NONE = 0
    JSON_EXTRACT = auto()
    JSON_CONTAINS = auto()
    JSON_EXISTS = auto()
    JSON_SET = auto()
    JSON_INSERT = auto()
    JSON_REPLACE = auto()
    JSON_REMOVE = auto()
    JSON_KEYS = auto()
    JSON_ARRAY = auto()
    JSON_OBJECT = auto()
    JSONB_SUPPORT = auto()


class ReturningCapability(Flag):
    """Represents features of the `RETURNING` clause in DML statements.

    The `RETURNING` clause is highly efficient for obtaining data from rows
    affected by an `INSERT`, `UPDATE`, or `DELETE` statement in a single
    round trip. However, support is inconsistent across databases. PostgreSQL
    has excellent support, while SQLite introduced it in version 3.35.0.
    MySQL notably lacks this feature entirely. This capability allows for
    checking not just for basic support, but also for advanced features like
    returning complex expressions.
    """
    NONE = 0
    BASIC_RETURNING = auto()
    RETURNING_EXPRESSIONS = auto()
    RETURNING_ALIASES = auto()


class TransactionCapability(Flag):
    """Represents different features related to database transactions.

    While all transactional databases support basic `BEGIN`, `COMMIT`, and
    `ROLLBACK` operations, the availability of more advanced transaction
    control features can vary. This includes support for named `SAVEPOINT`s
    for partial rollbacks, the ability to programmatically set transaction
    `ISOLATION_LEVELS` (e.g., `SERIALIZABLE`), and the option to declare
    a transaction as `READ ONLY` for optimization.
    """
    NONE = 0
    SAVEPOINT = auto()
    ISOLATION_LEVELS = auto()
    READ_ONLY_TRANSACTIONS = auto()


class BulkOperationCapability(Flag):
    """Represents features for performing efficient bulk data modifications.

    This category covers different methods for handling large volumes of
    data insertion or modification. `MULTI_ROW_INSERT` refers to the standard
    `INSERT ... VALUES (...), (...)` syntax. `UPSERT` logic is highly
    database-specific (e.g., `ON CONFLICT` in SQLite/PostgreSQL vs.
    `ON DUPLICATE KEY UPDATE` in MySQL). `BATCH_OPERATIONS` refers to the
    backend driver's ability to efficiently process multiple statements,
    such as through `executemany`.
    """
    NONE = 0
    MULTI_ROW_INSERT = auto()
    BATCH_OPERATIONS = auto()
    UPSERT = auto()


class JoinCapability(Flag):
    """Represents different SQL JOIN operations.

    While INNER and LEFT JOINs are almost universally supported, capabilities
    for RIGHT and FULL OUTER JOINs vary significantly across different
    database systems and versions. For example, SQLite only added support
    for RIGHT and FULL OUTER JOIN in version 3.39.0. This capability
    allows for precise testing of join-related logic.
    """
    NONE = 0
    INNER_JOIN = auto()
    LEFT_OUTER_JOIN = auto()
    RIGHT_OUTER_JOIN = auto()
    FULL_OUTER_JOIN = auto()
    CROSS_JOIN = auto()


class ConstraintCapability(Flag):
    """Represents support for various SQL constraints.

    While basic constraints like PRIMARY KEY and NOT NULL are fundamental,
    support for others can differ. For instance, the enforcement of CHECK
    constraints can vary. More notably, some databases introduce unique
    constraint-related features, such as SQLite's `STRICT` tables (added
    in version 3.37.0), which enforce data types more rigorously. This
    category allows for testing these specific behaviors.
    """
    NONE = 0
    PRIMARY_KEY = auto()
    FOREIGN_KEY = auto()
    UNIQUE = auto()
    NOT_NULL = auto()
    CHECK = auto()
    DEFAULT = auto()
    STRICT_TABLES = auto()


class AggregateFunctionCapability(Flag):
    """Represents support for specific aggregate functions.

    While basic aggregates like `SUM` and `COUNT` are universal, more advanced
    or specialized ones are not. A key example is string aggregation, which
    is `STRING_AGG` in PostgreSQL and standard SQL, but `GROUP_CONCAT` in
    SQLite and MySQL, with different syntax and options.
    """
    NONE = 0
    STRING_AGG = auto()
    GROUP_CONCAT = auto()
    JSON_AGG = auto()


class DateTimeFunctionCapability(Flag):
    """Represents support for date and time manipulation functions.

    Date and time handling is notoriously inconsistent across databases.
    This checks for support for standard functions like `EXTRACT` or common,
    de-facto standard functions for formatting (`STRFTIME`) and date
    arithmetic.
    """
    NONE = 0
    EXTRACT = auto()
    STRFTIME = auto()
    DATE_ADD = auto()
    DATE_SUB = auto()


class StringFunctionCapability(Flag):
    """Represents support for common string manipulation functions.

    While basic string operations are common, the exact function names and
    behaviors can vary. This category checks for widely accepted standard
    or de-facto standard functions.
    """
    NONE = 0
    CONCAT = auto()
    CONCAT_WS = auto()
    LOWER = auto()
    UPPER = auto()
    SUBSTRING = auto()
    TRIM = auto()


class MathematicalFunctionCapability(Flag):
    """Represents support for common mathematical and numeric functions.

    Checks for the availability of mathematical functions beyond basic
    arithmetic operators. Support for these can be inconsistent, especially
    in more lightweight databases.
    """
    NONE = 0
    ABS = auto()
    ROUND = auto()
    CEIL = auto()
    FLOOR = auto()
    POWER = auto()
    SQRT = auto()


# Main capability structure that combines all capabilities
class DatabaseCapabilities:
    """Database capability descriptor.
    
    This class represents the complete set of capabilities for a database backend.
    Each backend creates an instance of this class and populates it with the
    capabilities that it supports based on database version and other factors.
    
    The class provides methods to check for both category-level and specific
    feature-level capabilities, allowing for fine-grained feature detection.
    """
    
    def __init__(self):
        """Initialize an empty capability descriptor."""
        self.categories: CapabilityCategory = CapabilityCategory.NONE
        self.set_operations: SetOperationCapability = SetOperationCapability.NONE
        self.window_functions: WindowFunctionCapability = WindowFunctionCapability.NONE
        self.advanced_grouping: AdvancedGroupingCapability = AdvancedGroupingCapability.NONE
        self.cte: CTECapability = CTECapability.NONE
        self.json_operations: JSONCapability = JSONCapability.NONE
        self.returning: ReturningCapability = ReturningCapability.NONE
        self.transactions: TransactionCapability = TransactionCapability.NONE
        self.bulk_operations: BulkOperationCapability = BulkOperationCapability.NONE
        self.join_operations: JoinCapability = JoinCapability.NONE
        self.constraints: ConstraintCapability = ConstraintCapability.NONE
        self.aggregate_functions: AggregateFunctionCapability = AggregateFunctionCapability.NONE
        self.datetime_functions: DateTimeFunctionCapability = DateTimeFunctionCapability.NONE
        self.string_functions: StringFunctionCapability = StringFunctionCapability.NONE
        self.mathematical_functions: MathematicalFunctionCapability = MathematicalFunctionCapability.NONE
    
    def supports_category(self, category: CapabilityCategory) -> bool:
        """Check if a capability category is supported.
        
        Args:
            category: The capability category to check
            
        Returns:
            bool: True if the category is supported, False otherwise
        """
        return bool(self.categories & category)
    
    def supports_set_operation(self, operation: SetOperationCapability) -> bool:
        """Check if a set operation is supported.
        
        Args:
            operation: The set operation to check
            
        Returns:
            bool: True if the operation is supported, False otherwise
        """
        return bool(self.set_operations & operation)
    
    def supports_window_function(self, function: WindowFunctionCapability) -> bool:
        """Check if a window function is supported.
        
        Args:
            function: The window function to check
            
        Returns:
            bool: True if the function is supported, False otherwise
        """
        return bool(self.window_functions & function)
    
    def supports_advanced_grouping(self, grouping: AdvancedGroupingCapability) -> bool:
        """Check if an advanced grouping feature is supported.
        
        Args:
            grouping: The advanced grouping feature to check
            
        Returns:
            bool: True if the feature is supported, False otherwise
        """
        return bool(self.advanced_grouping & grouping)
    
    def supports_cte(self, cte_type: CTECapability) -> bool:
        """Check if a CTE feature is supported.
        
        Args:
            cte_type: The CTE feature to check
            
        Returns:
            bool: True if the feature is supported, False otherwise
        """
        return bool(self.cte & cte_type)
    
    def supports_json(self, json_op: JSONCapability) -> bool:
        """Check if a JSON operation is supported.
        
        Args:
            json_op: The JSON operation to check
            
        Returns:
            bool: True if the operation is supported, False otherwise
        """
        return bool(self.json_operations & json_op)
    
    def supports_returning(self, returning_type: ReturningCapability) -> bool:
        """Check if a RETURNING feature is supported.
        
        Args:
            returning_type: The RETURNING feature to check
            
        Returns:
            bool: True if the feature is supported, False otherwise
        """
        return bool(self.returning & returning_type)
    
    def supports_transaction(self, transaction_feature: TransactionCapability) -> bool:
        """Check if a transaction feature is supported.
        
        Args:
            transaction_feature: The transaction feature to check
            
        Returns:
            bool: True if the feature is supported, False otherwise
        """
        return bool(self.transactions & transaction_feature)
    
    def supports_bulk_operation(self, bulk_op: BulkOperationCapability) -> bool:
        """Check if a bulk operation is supported.
        
        Args:
            bulk_op: The bulk operation to check
            
        Returns:
            bool: True if the operation is supported, False otherwise
        """
        return bool(self.bulk_operations & bulk_op)
    
    def supports_join_operation(self, join_op: JoinCapability) -> bool:
        """Check if a join operation is supported."""
        return bool(self.join_operations & join_op)
    
    def supports_constraint(self, constraint: ConstraintCapability) -> bool:
        """Check if a constraint is supported."""
        return bool(self.constraints & constraint)
    
    def supports_aggregate_function(self, func: AggregateFunctionCapability) -> bool:
        """Check if an aggregate function is supported."""
        return bool(self.aggregate_functions & func)

    def supports_datetime_function(self, func: DateTimeFunctionCapability) -> bool:
        """Check if a date/time function is supported."""
        return bool(self.datetime_functions & func)

    def supports_string_function(self, func: StringFunctionCapability) -> bool:
        """Check if a string function is supported."""
        return bool(self.string_functions & func)

    def supports_mathematical_function(self, func: MathematicalFunctionCapability) -> bool:
        """Check if a mathematical function is supported."""
        return bool(self.mathematical_functions & func)
    
    def add_category(self, category: CapabilityCategory) -> 'DatabaseCapabilities':
        """Add a capability category.
        
        Args:
            category: The category to add
            
        Returns:
            DatabaseCapabilities: This instance for method chaining
        """
        self.categories |= category
        return self
    
    def add_set_operation(self, operation: SetOperationCapability) -> 'DatabaseCapabilities':
        """Add a set operation capability.
        
        Args:
            operation: The set operation to add
            
        Returns:
            DatabaseCapabilities: This instance for method chaining
        """
        self.set_operations |= operation
        self.categories |= CapabilityCategory.SET_OPERATIONS
        return self
    
    def add_window_function(self, function: Union[WindowFunctionCapability, List[WindowFunctionCapability]]) -> 'DatabaseCapabilities':
        """Add a window function capability.
        
        Args:
            function: The window function(s) to add
            
        Returns:
            DatabaseCapabilities: This instance for method chaining
        """
        if isinstance(function, list):
            for f in function:
                self.window_functions |= f
        else:
            self.window_functions |= function
        self.categories |= CapabilityCategory.WINDOW_FUNCTIONS
        return self
    
    def add_advanced_grouping(self, grouping: Union[AdvancedGroupingCapability, List[AdvancedGroupingCapability]]) -> 'DatabaseCapabilities':
        """Add an advanced grouping capability.
        
        Args:
            grouping: The advanced grouping feature(s) to add
            
        Returns:
            DatabaseCapabilities: This instance for method chaining
        """
        if isinstance(grouping, list):
            for g in grouping:
                self.advanced_grouping |= g
        else:
            self.advanced_grouping |= grouping
        self.categories |= CapabilityCategory.ADVANCED_GROUPING
        return self
    
    def add_cte(self, cte_type: Union[CTECapability, List[CTECapability]]) -> 'DatabaseCapabilities':
        """Add a CTE capability.
        
        Args:
            cte_type: The CTE feature(s) to add
            
        Returns:
            DatabaseCapabilities: This instance for method chaining
        """
        if isinstance(cte_type, list):
            for c in cte_type:
                self.cte |= c
        else:
            self.cte |= cte_type
        self.categories |= CapabilityCategory.CTE
        return self
    
    def add_json(self, json_op: Union[JSONCapability, List[JSONCapability]]) -> 'DatabaseCapabilities':
        """Add a JSON operation capability.
        
        Args:
            json_op: The JSON operation(s) to add
            
        Returns:
            DatabaseCapabilities: This instance for method chaining
        """
        if isinstance(json_op, list):
            for j in json_op:
                self.json_operations |= j
        else:
            self.json_operations |= json_op
        self.categories |= CapabilityCategory.JSON_OPERATIONS
        return self
    
    def add_returning(self, returning_type: Union[ReturningCapability, List[ReturningCapability]]) -> 'DatabaseCapabilities':
        """Add a RETURNING capability.
        
        Args:
            returning_type: The RETURNING feature(s) to add
            
        Returns:
            DatabaseCapabilities: This instance for method chaining
        """
        if isinstance(returning_type, list):
            for r in returning_type:
                self.returning |= r
        else:
            self.returning |= returning_type
        self.categories |= CapabilityCategory.RETURNING_CLAUSE
        return self
    
    def add_transaction(self, transaction_feature: Union[TransactionCapability, List[TransactionCapability]]) -> 'DatabaseCapabilities':
        """Add a transaction capability.
        
        Args:
            transaction_feature: The transaction feature(s) to add
            
        Returns:
            DatabaseCapabilities: This instance for method chaining
        """
        if isinstance(transaction_feature, list):
            for t in transaction_feature:
                self.transactions |= t
        else:
            self.transactions |= transaction_feature
        self.categories |= CapabilityCategory.TRANSACTION_FEATURES
        return self
    
    def add_bulk_operation(self, bulk_op: Union[BulkOperationCapability, List[BulkOperationCapability]]) -> 'DatabaseCapabilities':
        """Add a bulk operation capability.
        
        Args:
            bulk_op: The bulk operation(s) to add
            
        Returns:
            DatabaseCapabilities: This instance for method chaining
        """
        if isinstance(bulk_op, list):
            for b in bulk_op:
                self.bulk_operations |= b
        else:
            self.bulk_operations |= bulk_op
        self.categories |= CapabilityCategory.BULK_OPERATIONS
        return self
    
    def add_join_operation(self, join_op: Union[JoinCapability, List[JoinCapability]]) -> 'DatabaseCapabilities':
        """Add a join operation capability."""
        if isinstance(join_op, list):
            for j in join_op:
                self.join_operations |= j
        else:
            self.join_operations |= join_op
        self.categories |= CapabilityCategory.JOIN_OPERATIONS
        return self
    
    def add_constraint(self, constraint: Union[ConstraintCapability, List[ConstraintCapability]]) -> 'DatabaseCapabilities':
        """Add a constraint capability."""
        if isinstance(constraint, list):
            for c in constraint:
                self.constraints |= c
        else:
            self.constraints |= constraint
        self.categories |= CapabilityCategory.CONSTRAINTS
        return self
    
    def add_aggregate_function(self, func: Union[AggregateFunctionCapability, List[AggregateFunctionCapability]]) -> 'DatabaseCapabilities':
        """Add an aggregate function capability."""
        if isinstance(func, list):
            for f in func:
                self.aggregate_functions |= f
        else:
            self.aggregate_functions |= func
        self.categories |= CapabilityCategory.AGGREGATE_FUNCTIONS
        return self

    def add_datetime_function(self, func: Union[DateTimeFunctionCapability, List[DateTimeFunctionCapability]]) -> 'DatabaseCapabilities':
        """Add a date/time function capability."""
        if isinstance(func, list):
            for f in func:
                self.datetime_functions |= f
        else:
            self.datetime_functions |= func
        self.categories |= CapabilityCategory.DATETIME_FUNCTIONS
        return self

    def add_string_function(self, func: Union[StringFunctionCapability, List[StringFunctionCapability]]) -> 'DatabaseCapabilities':
        """Add a string function capability."""
        if isinstance(func, list):
            for f in func:
                self.string_functions |= f
        else:
            self.string_functions |= func
        self.categories |= CapabilityCategory.STRING_FUNCTIONS
        return self

    def add_mathematical_function(self, func: Union[MathematicalFunctionCapability, List[MathematicalFunctionCapability]]) -> 'DatabaseCapabilities':
        """Add a mathematical function capability."""
        if isinstance(func, list):
            for f in func:
                self.mathematical_functions |= f
        else:
            self.mathematical_functions |= func
        self.categories |= CapabilityCategory.MATHEMATICAL_FUNCTIONS
        return self

# Capability constants for common use cases
# These are predefined combinations of capabilities that are commonly supported together

ALL_SET_OPERATIONS = (
    SetOperationCapability.UNION | 
    SetOperationCapability.UNION_ALL | 
    SetOperationCapability.INTERSECT | 
    SetOperationCapability.INTERSECT_ALL | 
    SetOperationCapability.EXCEPT | 
    SetOperationCapability.EXCEPT_ALL
)

ALL_WINDOW_FUNCTIONS = (
    WindowFunctionCapability.ROW_NUMBER |
    WindowFunctionCapability.RANK |
    WindowFunctionCapability.DENSE_RANK |
    WindowFunctionCapability.LAG |
    WindowFunctionCapability.LEAD |
    WindowFunctionCapability.FIRST_VALUE |
    WindowFunctionCapability.LAST_VALUE |
    WindowFunctionCapability.NTH_VALUE |
    WindowFunctionCapability.CUME_DIST |
    WindowFunctionCapability.PERCENT_RANK |
    WindowFunctionCapability.NTILE
)

ALL_CTE_FEATURES = (
    CTECapability.BASIC_CTE |
    CTECapability.RECURSIVE_CTE |
    CTECapability.COMPOUND_RECURSIVE_CTE |
    CTECapability.CTE_IN_DML |
    CTECapability.MATERIALIZED_CTE
)

ALL_JSON_OPERATIONS = (
    JSONCapability.JSON_EXTRACT |
    JSONCapability.JSON_CONTAINS |
    JSONCapability.JSON_EXISTS |
    JSONCapability.JSON_SET |
    JSONCapability.JSON_INSERT |
    JSONCapability.JSON_REPLACE |
    JSONCapability.JSON_REMOVE |
    JSONCapability.JSON_KEYS |
    JSONCapability.JSON_ARRAY |
    JSONCapability.JSON_OBJECT
)

ALL_RETURNING_FEATURES = (
    ReturningCapability.BASIC_RETURNING |
    ReturningCapability.RETURNING_EXPRESSIONS |
    ReturningCapability.RETURNING_ALIASES
)