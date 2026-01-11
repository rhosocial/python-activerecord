# src/rhosocial/activerecord/interface/update.py
"""
Interface for model update behavior customization.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any


class IUpdateBehavior(ABC):
    """
    Interface for defining custom model update behavior.

    This interface allows models to add custom conditions and expressions during
    UPDATE operations. It's particularly useful for implementing advanced features
    like optimistic locking, version tracking, audit trails, and conditional updates.

    Models that implement this interface can control exactly what conditions must
    be met for an update to occur and what additional expressions should be included
    in the UPDATE statement.
    """

    @abstractmethod
    def get_update_conditions(self) -> List[Tuple[str, Optional[tuple]]]:
        """
        Get additional WHERE conditions to include in UPDATE operations.

        This method allows adding extra conditions to the WHERE clause of UPDATE
        statements, which is crucial for features like optimistic locking where
        you need to ensure the record hasn't been modified since it was last read.

        Each condition should be provided as a tuple containing:
        - A SQL condition string with placeholders (usually '?')
        - A tuple of parameter values for the placeholders, or None if no parameters

        Returns:
            List[Tuple[str, Optional[tuple]]]: List of (condition_sql, params) tuples
            where:
            - condition_sql: SQL condition string with '?' placeholders
            - params: Tuple of parameter values, or None if no parameters

        Example:
            def get_update_conditions(self):
                return [
                    ('version = ?', (self.version,)),  # Optimistic locking
                    ('updated_at <= ?', (self.updated_at,))  # Ensure consistency
                ]

        Note:
            All conditions returned by this method will be combined with AND logic
            in the final UPDATE statement's WHERE clause.
        """
        pass

    @abstractmethod
    def get_update_expressions(self) -> Dict[str, Any]:
        """
        Get additional field expressions to include in UPDATE SET clause.

        This method allows specifying additional fields and their values to be
        updated in addition to the model's changed fields. This is useful for
        automatically updating timestamp fields, incrementing version counters,
        or setting audit information.

        Returns:
            Dict[str, Any]: Mapping of field names to their new values or expressions.
            The values can be:
            - Literal values (strings, numbers, etc.)
            - SQL expressions (as strings)
            - Calculated values based on current model state

        Example:
            def get_update_expressions(self):
                return {
                    'version': self.version + 1,  # Increment version
                    'updated_at': 'CURRENT_TIMESTAMP',  # SQL function
                    'last_modified_by': self.last_modified_by_id  # Use current value
                }

        Note:
            These expressions will be added to the SET clause of the UPDATE statement
            alongside any fields that have been marked as dirty in the model.
        """
        pass
