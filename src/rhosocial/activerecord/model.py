# src/rhosocial/activerecord/model.py
# Define the main ActiveRecord class by combining mixins
# This approach keeps the class definition clean and modular
from .base import BaseActiveRecord, QueryMixin
from .relation import RelationManagementMixin

class ActiveRecord(
    RelationManagementMixin,
    # FieldMixin, # import when needed
    QueryMixin,
    BaseActiveRecord,
):
    """Complete ActiveRecord implementation combining core features.

    Inherits functionality from:

    - BaseActiveRecord: Core CRUD operations
    - RelationalModelMixin: Relationship handling
    - QueryMixin: Query builder
    """
    ...

__all__ = [
    'ActiveRecord',
]