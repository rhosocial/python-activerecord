"""Module providing soft delete functionality."""
from datetime import datetime
from typing import Dict, Any, Optional
import tzlocal
from pydantic import Field

from ..query import ActiveQuery
from ..interface import IActiveRecord, ModelEvent


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
        instance.deleted_at = datetime.now(tzlocal.get_localzone())

    def prepare_delete(self) -> Dict[str, Any]:
        """Prepare soft delete data"""
        if self.deleted_at is None:
            raise ValueError("deleted_at not set, ensure BEFORE_DELETE event is triggered")
        return {'deleted_at': self.deleted_at}

    @classmethod
    def query(cls) -> 'ActiveQuery':
        """Return query builder with soft delete condition"""
        return super().query().where("deleted_at IS NULL")

    @classmethod
    def query_with_deleted(cls) -> 'ActiveQuery':
        """Return query including all records (no soft delete filter)"""
        return super().query()

    @classmethod
    def query_only_deleted(cls) -> 'ActiveQuery':
        """Return query for only deleted records"""
        return super().query().where("deleted_at IS NOT NULL")

    def restore(self) -> int:
        """Restore a soft-deleted record"""
        if self.deleted_at is None:
            return 0

        result = self.backend().update(
            self.table_name(),
            {'deleted_at': None},
            f"{self.primary_key()} = ?",
            (getattr(self, self.primary_key()),)
        )

        if result.affected_rows > 0:
            self.deleted_at = None
            self.reset_tracking()

        return result.affected_rows