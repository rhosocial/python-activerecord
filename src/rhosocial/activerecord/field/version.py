"""Module providing version control functionality."""
from typing import Tuple, Any, Dict, List, Optional

from ..backend import DatabaseError, StorageBackend, SQLExpressionBase
from ..interface import IActiveRecord, IUpdateBehavior, ModelEvent


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

    def get_update_condition(self) -> Tuple[str, tuple]:
        """Get SQL condition for version check

        Returns:
            Tuple of (condition_sql, params)
        """
        return f"{self.db_column} = ?", (self.value,)

    def get_update_expression(self, backend: StorageBackend) -> SQLExpressionBase:
        """Get SQL expression for version update

        Args:
            backend: Storage backend instance

        Returns:
            SQL expression to increment version
        """
        return backend.create_expression(f"{self.db_column} + {self.increment_by}")

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


class OptimisticLockMixin(IUpdateBehavior, IActiveRecord):
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

    def get_update_conditions(self) -> List[Tuple[str, Optional[tuple]]]:
        """Add version check to update conditions"""
        if not self.is_new_record:
            condition, params = self._version.get_update_condition()
            return [(condition, params)]
        return []

    def get_update_expressions(self) -> Dict[str, Any]:
        """Add version increment to update expressions"""
        if not self.is_new_record:
            return {
                self._version.db_column: self._version.get_update_expression(self.backend())
            }
        return {}

    def _handle_version_after_save(self, instance: 'OptimisticLockMixin', *,
                               is_new: bool = False, result: Any = None, **kwargs) -> None:
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

            if hasattr(result, 'data') and result.data:
                new_version = result.data.get(self._version.db_column)
                if new_version is not None:
                    self._version = Version(
                        value=new_version,
                        increment_by=self._version.increment_by,
                        db_column=self._version.db_column
                    )
            else:
                self._version.increment()

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Include version in serialized data"""
        data = super().model_dump(**kwargs)
        data[self._version.db_column] = self.version
        return data