# src/rhosocial/activerecord/field/version.py
"""Module providing version control functionality."""
from typing import Any, Dict, List

from ..backend.errors import DatabaseError
from ..backend.expression import SQLPredicate, SQLValueExpression
from ..backend.result import QueryResult
from ..interface import IActiveRecord, ModelEvent
from ..interface.update import IUpdateBehavior


class Version:
    """Represents a version number used for optimistic locking

    Handles version increment logic and SQL condition/expression generation.
    Used as a type hint for pydantic PrivateAttr in models.

    Attributes:
        value: Current version number
        increment_by: Amount to increment version by on each update
        db_column: Database column name for version field
    """

    def __init__(self, value: int = 1, *, increment_by: int = 1, db_column: str = "version"):
        """Initialize version instance

        Args:
            value: Initial version number (default: 1)
            increment_by: Amount to increment version by on each update
            db_column: Database column name (default: "version")

        Raises:
            ValueError: If value or increment_by is not positive or db_column is empty
        """
        if value <= 0:
            raise ValueError("Version value must be positive")
        if increment_by <= 0:
            raise ValueError("increment_by must be positive")
        if not db_column or not db_column.strip():
            raise ValueError("db_column cannot be empty")

        self.value = value
        self.increment_by = increment_by
        self.db_column = db_column.strip()

    def increment(self) -> None:
        """Increment version number by increment_by"""
        self.value += self.increment_by

    def get_update_condition(self, dialect):
        """Get SQL condition for version check using expression system

        Args:
            dialect: The SQL dialect instance

        Returns:
            Expression object representing the version condition
        """
        from ..backend.expression.core import Column
        # Use operator overloading: Column == value (automatically converted to Literal)
        return Column(dialect, self.db_column) == self.value

    def get_update_expression(self, dialect):
        """Get SQL expression for version update using expression system

        Args:
            dialect: The SQL dialect instance

        Returns:
            Expression object to increment version
        """
        from ..backend.expression.core import Column
        # Use operator overloading: Column + value (automatically converted to Literal)
        return Column(dialect, self.db_column) + self.increment_by

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return (self.value == other.value and
                self.increment_by == other.increment_by and
                self.db_column == other.db_column)

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"Version(value={self.value}, increment_by={self.increment_by}, db_column='{self.db_column}')"


class OptimisticLockMixin(IUpdateBehavior):
    """Optimistic locking mixin that uses Version class

    Uses VersionField (a PrivateAttr) to manage a Version instance.
    The database column name and increment amount can be customized.
    """

    _version: Version = Version(value=1, increment_by=1)

    def __init__(self, **data):
        """Initialize mixin and register event handler"""
        super().__init__(**data)
        version_value = data.get('version', 1)
        self._version = Version(value=version_value, increment_by=1)
        self.on(ModelEvent.AFTER_SAVE, self._handle_version_after_save)

    @property
    def version(self) -> int:
        """Read-only access to current version number"""
        return self._version.value

    def get_update_conditions(self) -> List[SQLPredicate]:
        """Add version check to update conditions using expression system"""
        if not self.is_new_record:
            backend = self.backend()
            condition_expr = self._version.get_update_condition(backend.dialect)
            return [condition_expr]
        return []

    def get_update_expressions(self) -> Dict[str, SQLValueExpression]:
        """Add version increment to update expressions using expression system"""
        if not self.is_new_record:
            backend = self.backend()
            return {
                self._version.db_column: self._version.get_update_expression(backend.dialect)
            }
        return {}

    def _handle_version_after_save(self, instance: 'OptimisticLockMixin', *,
                                   is_new: bool = False, result: 'QueryResult' = None, **kwargs) -> None:
        """Handle version management after save

        Args:
            instance: The model instance
            is_new: Whether this is a new record
            result: The save operation result containing affected_rows and returned data
            **kwargs: Additional event arguments

        Raises:
            DatabaseError: If optimistic lock check fails
        """
        if not is_new:
            if result.affected_rows == 0:
                raise DatabaseError("Record was updated by another process")

            # Check if result has data and contains the version column
            if result.data is not None:
                # If result.data is a list (e.g., from RETURNING clause with multiple rows)
                if isinstance(result.data, list) and len(result.data) > 0:
                    # Take the first row if it's a list of rows
                    first_row = result.data[0]
                    if isinstance(first_row, dict) and self._version.db_column in first_row:
                        new_version = first_row[self._version.db_column]
                        if new_version is not None:
                            self._version = Version(
                                value=new_version,
                                increment_by=self._version.increment_by,
                                db_column=self._version.db_column
                            )
                            return  # Successfully updated from returned data
                # If result.data is a dictionary (single row)
                elif isinstance(result.data, dict) and self._version.db_column in result.data:
                    new_version = result.data[self._version.db_column]
                    if new_version is not None:
                        self._version = Version(
                            value=new_version,
                            increment_by=self._version.increment_by,
                            db_column=self._version.db_column
                        )
                        return  # Successfully updated from returned data

            # If we couldn't get the version from the returned data, increment locally
            self._version.increment()

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Include version in serialized data"""
        data = super().model_dump(**kwargs)
        data[self._version.db_column] = self.version
        return data
