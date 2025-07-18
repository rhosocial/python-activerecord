# tests/rhosocial/activerecord_test/query/fixtures/extended_models.py
from decimal import Decimal
from typing import Optional, ClassVar

from pydantic import Field, EmailStr

from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin, TimestampMixin
from rhosocial.activerecord.relation import HasMany, BelongsTo
from ...utils import create_active_record_fixture


class User(IntegerPKMixin, TimestampMixin, ActiveRecord):
    """User model with basic relations."""
    __table_name__ = "users"

    id: Optional[int] = None
    username: str
    email: EmailStr
    age: Optional[int] = Field(..., ge=0, le=100)
    balance: float = 0.0
    is_active: bool = True

    orders: ClassVar[HasMany['ExtendedOrder']] = HasMany(foreign_key='user_id', inverse_of='user')


class ExtendedOrder(IntegerPKMixin, TimestampMixin, ActiveRecord):
    """Extended Order model with additional fields for advanced grouping tests."""
    __table_name__ = "extended_orders"

    id: Optional[int] = None
    user_id: int
    order_number: str
    total_amount: Decimal = Field(default=Decimal('0'))
    status: str = 'pending'  # pending, paid, shipped, completed, cancelled

    # Additional fields for CUBE, ROLLUP, GROUPING SETS tests
    priority: str = 'medium'  # high, medium, low
    region: str = 'default'  # North, South, East, West, etc.
    category: str = ''  # For product categories
    product: str = ''  # For product types
    department: str = ''  # For organizational department
    year: str = ''  # For year-based grouping
    quarter: str = ''  # For quarter-based grouping

    items: ClassVar[HasMany['ExtendedOrderItem']] = HasMany(foreign_key='order_id', inverse_of='order')
    user: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id', inverse_of='orders')


class ExtendedOrderItem(IntegerPKMixin, TimestampMixin, ActiveRecord):
    """Extended Order item model with basic relations."""
    __table_name__ = "extended_order_items"

    id: Optional[int] = None
    order_id: int
    product_name: str
    quantity: int = Field(ge=1)
    price: Decimal

    # Additional fields for joining in advanced tests
    category: str = ''
    region: str = ''

    order: ClassVar[BelongsTo['ExtendedOrder']] = BelongsTo(foreign_key='order_id', inverse_of='items')


# Create test fixtures
extended_user_class = create_active_record_fixture(User)
extended_order_class = create_active_record_fixture(ExtendedOrder)
extended_order_item_class = create_active_record_fixture(ExtendedOrderItem)


def create_extended_order_fixtures():
    """Create test fixtures for extended order-related tables.

    Creates tables in dependency order:
    1. users
    2. extended_orders
    3. extended_order_items

    Returns:
        pytest fixture for the extended models
    """
    from ..utils import create_table_fixture

    model_classes = [User, ExtendedOrder, ExtendedOrderItem]

    # Define schema mapping
    schema_map = {
        User.__table_name__: "users.sql",
        ExtendedOrder.__table_name__: "extended_orders.sql",
        ExtendedOrderItem.__table_name__: "extended_order_items.sql"
    }

    return create_table_fixture(model_classes, schema_map)
