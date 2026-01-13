# src/rhosocial/activerecord/interface/update.py
"""
Protocol for model update behavior customization.
"""
from typing import Protocol, Dict, List
from typing import runtime_checkable
from ..backend.expression import SQLValueExpression, SQLPredicate


@runtime_checkable
class IUpdateBehavior(Protocol):
    """
    Protocol for defining custom model update behavior.

    This protocol allows models to add custom conditions and expressions during
    UPDATE operations. It's particularly useful for implementing advanced features
    like optimistic locking, version tracking, audit trails, and conditional updates.

    Classes that implement this protocol can control exactly what conditions must
    be met for an update to occur and what additional expressions should be included
    in the UPDATE statement.

    Note: Unlike an abstract base class, this is a structural protocol.
    Any class that has the required methods automatically satisfies this protocol,
    without needing to explicitly inherit from it.
    """

    def get_update_conditions(self) -> List[SQLPredicate]:
        """
        Get additional WHERE conditions to include in UPDATE operations.

        This method allows adding extra conditions to the WHERE clause of UPDATE
        statements, which is crucial for features like optimistic locking where
        you need to ensure the record hasn't been modified since it was last read.

        Returns:
            List[SQLPredicate]: List of SQL predicate objects that will be
            combined with AND logic in the final UPDATE statement's WHERE clause.

        Example:
            def get_update_conditions(self):
                from ..backend.expression import ComparisonPredicate, Column, Literal
                # Method 1: Using explicit expression objects
                return [
                    # Optimistic locking: ensure version hasn't changed
                    ComparisonPredicate(
                        self.backend().dialect,
                        "=",
                        Column(self.backend().dialect, "version"),
                        Literal(self.backend().dialect, self.version)
                    ),
                    # Ensure updated_at hasn't changed since last read
                    ComparisonPredicate(
                        self.backend().dialect,
                        "<=",
                        Column(self.backend().dialect, "updated_at"),
                        Literal(self.backend().dialect, self.updated_at)
                    )
                ]

            # Method 2: Using field proxy (if your model uses field_proxy)
            # Assuming your model has a field proxy like: c = FieldProxy()
            # def get_update_conditions(self):
            #     # This generates ComparisonPredicate objects automatically
            #     return [
            #         (self.__class__.c.version == self.version),  # Generates ComparisonPredicate
            #         (self.__class__.c.updated_at <= self.updated_at)  # Generates ComparisonPredicate
            #     ]

            # Method 3: More complex field proxy example with multiple conditions
            # def get_update_conditions(self):
            #     # Using field proxy for complex conditions
            #     return [
            #         (self.__class__.c.version == self.version),  # Optimistic locking
            #         (self.__class__.c.status == 'active'),       # Ensure status is active
            #         (self.__class__.c.locked_until < 'NOW()'),   # Ensure not locked
            #     ]

        Note:
            All conditions returned by this method will be combined with AND logic
            in the final UPDATE statement's WHERE clause.
        """
        ...

    def get_update_expressions(self) -> Dict[str, SQLValueExpression]:
        """
        Get additional field expressions to include in UPDATE SET clause.

        This method allows specifying additional fields and their expressions to be
        updated in addition to the model's changed fields. This is useful for
        automatically updating timestamp fields, incrementing version counters,
        or setting audit information.

        Returns:
            Dict[str, SQLValueExpression]: Mapping of field names to SQL expression objects.

        Example:
            def get_update_expressions(self):
                from ..backend.expression import Column, Literal, FunctionCall
                from ..backend.expression.operators import BinaryArithmeticExpression
                # Method 1: Using explicit expression objects
                return {
                    # Increment version in database (for optimistic locking)
                    'version': BinaryArithmeticExpression(
                        self.backend().dialect,
                        '+',
                        Column(self.backend().dialect, 'version'),
                        Literal(self.backend().dialect, 1)
                    ),
                    # Set updated_at to current timestamp using SQL function
                    'updated_at': FunctionCall(
                        self.backend().dialect,
                        'CURRENT_TIMESTAMP'
                    ),
                    # Set last_modified_by using current instance value
                    'last_modified_by': Literal(
                        self.backend().dialect,
                        self.last_modified_by_id
                    )
                }

            # Method 2: Using field proxy (if your model uses field_proxy)
            # The field proxy is more commonly used in conditions (get_update_conditions)
            # For expressions, you can still use field proxy for the column reference:
            # def get_update_expressions(self):
            #     # This generates SQLValueExpression objects automatically
            #     return {
            #         'version': (self.__class__.c.version + 1),  # Uses field proxy for arithmetic
            #         'updated_at': 'CURRENT_TIMESTAMP',  # SQL function string
            #         'last_modified_by': self.last_modified_by_id
            #     }

            # Method 3: More complex field proxy example for expressions
            # def get_update_expressions(self):
            #     # Using field proxy for complex expressions
            #     return {
            #         'version': (self.__class__.c.version + 1),           # Increment version
            #         'updated_at': 'CURRENT_TIMESTAMP',                  # Set current timestamp
            #         'update_count': (self.__class__.c.update_count + 1)  # Increment update counter
            #     }

        Note:
            These expressions will be added to the SET clause of the UPDATE statement
            alongside any fields that have been marked as dirty in the model.
        """
        ...
