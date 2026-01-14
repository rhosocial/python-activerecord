# src/rhosocial/activerecord/field/soft_delete.py
"""Module providing soft delete functionality."""
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pydantic import Field

from ..query import ActiveQuery
from ..interface import IActiveRecord, ModelEvent
from ..backend.expression.core import Column, Literal
from ..backend.expression.predicates import IsNullPredicate


class SoftDeleteMixin(IActiveRecord):
    """Implements soft delete functionality.

    Instead of actual deletion, marks records as deleted using timestamp.
    Provides methods to:
    - Soft delete records
    - Query including/excluding deleted records
    - Restore deleted records
    """
    deleted_at: Optional[datetime] = Field(default=None)

    def __init__(self, **data):
        super().__init__(**data)
        self.on(ModelEvent.BEFORE_DELETE, self._mark_as_deleted)

    def _mark_as_deleted(self, instance: 'SoftDeleteMixin', **kwargs):
        """Mark record as soft deleted by setting deleted_at timestamp."""
        instance.deleted_at = datetime.now(timezone.utc)

    def prepare_delete(self) -> Dict[str, Any]:
        """Prepare soft delete data"""
        if self.deleted_at is None:
            raise ValueError("deleted_at not set, ensure BEFORE_DELETE event is triggered")
        return {'deleted_at': self.deleted_at}

    @classmethod
    def query(cls) -> 'ActiveQuery':
        """Return query builder excluding soft-deleted records using expression system."""
        backend = cls.backend()
        # Use is_not_null() method from ComparisonMixin to check for non-deleted records
        non_deleted_condition = Column(backend.dialect, "deleted_at").is_not_null()
        return super().query().where(non_deleted_condition)

    @classmethod
    def query_with_deleted(cls) -> 'ActiveQuery':
        """Return query including all records (no soft delete filter)"""
        return super().query()

    @classmethod
    def query_only_deleted(cls) -> 'ActiveQuery':
        """Return query for only soft-deleted records using expression system."""
        backend = cls.backend()
        # Use is_null() method from ComparisonMixin to check for deleted records
        deleted_condition = Column(backend.dialect, "deleted_at").is_null()
        return super().query().where(deleted_condition)

    def restore(self) -> int:
        """Restore a soft-deleted record using expression system."""
        if self.deleted_at is None:
            return 0

        # Get the backend
        backend = self.backend()

        # Create the condition using expression system
        pk_column = Column(backend.dialect, self.primary_key())
        pk_value = getattr(self, self.primary_key())
        condition_expr = pk_column == pk_value

        # Use UpdateOptions for the update operation
        from ..backend.options import UpdateOptions
        update_options = UpdateOptions(
            table=self.table_name(),
            data={'deleted_at': None},
            where=condition_expr
        )

        result = backend.update(update_options)

        if result.affected_rows > 0:
            self.deleted_at = None
            self.reset_tracking()

        return result.affected_rows
