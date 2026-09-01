# src/rhosocial/activerecord/interface/update.py
"""
Interface for model update behavior customization.
"""

from abc import ABC
from typing import Any, Dict, List
from ..backend.expression import SQLValueExpression, SQLPredicate


class IUpdateBehavior(ABC):
    """
    Interface for defining custom model update behavior.

    This interface allows models to add custom conditions and expressions during
    UPDATE operations. It's particularly useful for implementing advanced features
    like optimistic locking, version tracking, audit trails, and conditional updates.

    Classes that implement this interface can control exactly what conditions must
    be met for an update to occur and what additional expressions should be included
    in the UPDATE statement.

    Note: This is an abstract base class interface that requires explicit inheritance.
    Classes must inherit from this interface to be recognized as implementing it.

    IMPORTANT: IUpdateBehavior should be used as a base class for ActiveRecord mixins.
    The _update_internal method will only recognize classes that directly inherit
    from IUpdateBehavior.
    BOTH METHODS MUST BE IMPLEMENTED when inheriting from IUpdateBehavior.
    If a particular method is not needed, it should return an empty list/dict
    or None, which will be automatically skipped during updates.
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
            If no additional conditions are needed, return None,
            which will be automatically skipped during updates.

        Example:
            The framework ships a complete implementation:
            ``DefaultOptimisticLockMixin`` (``field/version.py``) uses this
            hook to reject concurrent updates via a version column — prefer
            mixing it in over hand-rolling a lock.

            For a custom behaviour, return predicates built from expression
            objects or the field proxy::

                def get_update_conditions(self):
                    # Field proxy (c) generates ComparisonPredicate objects
                    return [
                        (self.__class__.c.status == 'active'),      # Ensure status is active
                        (self.__class__.c.locked_until < 'NOW()'),  # Ensure not locked
                    ]

        Note:
            All conditions returned by this method will be combined with AND logic
            in the final UPDATE statement's WHERE clause.
            This method does not need to return meaningful data if conditions are not needed.
            Only classes that directly inherit from IUpdateBehavior will be recognized
            by the _update_internal method.
        """
        return None  # Return None by default if not overridden

    def get_update_expressions(self) -> Dict[str, SQLValueExpression]:
        """
        Get additional field expressions to include in UPDATE SET clause.

        This method allows specifying additional fields and their expressions to be
        updated in addition to the model's changed fields. This is useful for
        automatically updating timestamp fields, incrementing version counters,
        or setting audit information.

        Returns:
            Dict[str, SQLValueExpression]: Mapping of field names to SQL expression objects.
            If no additional expressions are needed, return an empty dict or None,
            which will be automatically skipped during updates.

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

            # Method 1: Using explicit expression objects (shown above)

            Method 2: Using field proxy (if your model uses field_proxy)
            The field proxy is more commonly used in conditions (get_update_conditions)
            For expressions, you can still use field proxy for the column reference:
            def get_update_expressions(self):
                # This generates SQLValueExpression objects automatically
                return {
                    'version': (self.__class__.c.version + 1),  # Uses field proxy for arithmetic
                    'updated_at': 'CURRENT_TIMESTAMP',  # SQL function string
                    'last_modified_by': self.last_modified_by_id
                }

            Method 3: More complex field proxy example for expressions
            def get_update_expressions(self):
                # Using field proxy for complex expressions
                return {
                    'version': (self.__class__.c.version + 1),           # Increment version
                    'updated_at': 'CURRENT_TIMESTAMP',                  # Set current timestamp
                    'update_count': (self.__class__.c.update_count + 1)  # Increment update counter
                }

        Note:
            These expressions will be added to the SET clause of the UPDATE statement
            alongside any fields that have been marked as dirty in the model.
            This method does not need to return meaningful data if expressions are not needed.
            Only classes that directly inherit from IUpdateBehavior will be recognized
            by the _update_internal method.
        """
        return None  # Return None by default if not overridden


class IDeleteBehavior(ABC):
    """Interface for model deletion behavior customization.

    Implementing this interface (e.g. ``SoftDeleteMixin``) tells the
    framework that ``delete()`` should be routed through
    :meth:`prepare_delete` instead of issuing a hard DELETE.

    Implementors return the update payload (field -> value) describing the
    soft-deleted state; the framework wraps it in an UPDATE with the
    primary-key WHERE predicate.
    """

    def prepare_delete(self) -> Dict[str, Any]:
        """Return the update payload for the soft delete.

        Returns:
            Dict[str, Any]: Field-name -> value mapping applied via UPDATE.
        """
        raise NotImplementedError


class IDataPreparationBehavior(ABC):
    """Interface for hooking into save-data preparation.

    Implementors (e.g. ``UUIDMixin``) may adjust the field payload right
    before persistence — filling generated values, normalizing types, etc.
    """

    def prepare_save_data(self, data: Dict[str, Any], is_new: bool) -> Dict[str, Any]:
        """Adjust the payload prepared for INSERT/UPDATE.

        Args:
            data: The field payload about to be persisted.
            is_new: True when the record is about to be inserted.

        Returns:
            Dict[str, Any]: The (possibly modified) payload.
        """
        return data
