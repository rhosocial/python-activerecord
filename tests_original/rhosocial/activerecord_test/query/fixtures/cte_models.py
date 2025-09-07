# tests/rhosocial/activerecord_test/query/fixtures/cte_models.py
from decimal import Decimal
from typing import Optional, ClassVar

from pydantic import Field

from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin, TimestampMixin
from rhosocial.activerecord.relation import HasMany, BelongsTo
from ...utils import create_active_record_fixture


class Node(IntegerPKMixin, TimestampMixin, ActiveRecord):
    """Node model for tree structure tests (recursive CTEs)."""
    __table_name__ = "nodes"

    id: Optional[int] = None
    name: str
    parent_id: Optional[int] = None
    value: Decimal = Field(default=Decimal('0.00'))

    # Self-referencing relation for tree structure
    parent: ClassVar[BelongsTo['Node']] = BelongsTo(foreign_key='parent_id', inverse_of='children')
    children: ClassVar[HasMany['Node']] = HasMany(foreign_key='parent_id', inverse_of='parent')


# Create test fixture
node_class = create_active_record_fixture(Node)
