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

class SetOperationCapability(Flag):
    """Set operation capabilities.
    
    Represents different SQL set operations like UNION, INTERSECT, etc.
    """
    NONE = 0
    UNION = auto()
    UNION_ALL = auto()
    INTERSECT = auto()
    INTERSECT_ALL = auto()
    EXCEPT = auto()
    EXCEPT_ALL = auto()

class WindowFunctionCapability(Flag):
    """Window function capabilities.
    
    Represents different window functions that may be supported by a database.
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
    """Advanced grouping capabilities.
    
    Represents advanced SQL grouping operations like CUBE, ROLLUP, etc.
    """
    NONE = 0
    CUBE = auto()
    ROLLUP = auto()
    GROUPING_SETS = auto()

class CTECapability(Flag):
    """Common Table Expression capabilities.
    
    Represents different CTE features that may be supported.
    """
    NONE = 0
    BASIC_CTE = auto()
    RECURSIVE_CTE = auto()
    COMPOUND_RECURSIVE_CTE = auto()
    CTE_IN_DML = auto()
    MATERIALIZED_CTE = auto()

class JSONCapability(Flag):
    """JSON operation capabilities.
    
    Represents different JSON operations that may be supported by a database.
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

class ReturningCapability(Flag):
    """RETURNING clause capabilities.
    
    Represents different RETURNING clause features that may be supported.
    """
    NONE = 0
    BASIC_RETURNING = auto()
    RETURNING_EXPRESSIONS = auto()
    RETURNING_ALIASES = auto()

class TransactionCapability(Flag):
    """Transaction feature capabilities.
    
    Represents different transaction features that may be supported.
    """
    NONE = 0
    SAVEPOINT = auto()
    ISOLATION_LEVELS = auto()
    READ_ONLY_TRANSACTIONS = auto()

class BulkOperationCapability(Flag):
    """Bulk operation capabilities.
    
    Represents different bulk operation features that may be supported.
    """
    NONE = 0
    MULTI_ROW_INSERT = auto()
    BATCH_OPERATIONS = auto()

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
        # Additional capability categories would be added here
    
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