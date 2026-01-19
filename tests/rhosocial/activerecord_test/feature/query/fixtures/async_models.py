# tests/rhosocial/activerecord_test/feature/query/fixtures/async_models.py
from decimal import Decimal
from typing import Optional, ClassVar

from pydantic import Field, EmailStr

from rhosocial.activerecord.model import AsyncActiveRecord
from rhosocial.activerecord.base.field_proxy import FieldProxy
from rhosocial.activerecord.field import IntegerPKMixin, TimestampMixin
from rhosocial.activerecord.relation import HasMany, BelongsTo


class AsyncUser(IntegerPKMixin, TimestampMixin, AsyncActiveRecord):
    """Async User model with basic relations."""
    __table_name__ = "users"
    c: ClassVar[FieldProxy] = FieldProxy()

    id: Optional[int] = None
    username: str
    email: EmailStr
    age: Optional[int] = Field(..., ge=0, le=100)
    balance: float = 0.0
    is_active: bool = True

    orders: ClassVar[HasMany['AsyncOrder']] = HasMany(foreign_key='user_id', inverse_of='user')


class AsyncOrder(IntegerPKMixin, TimestampMixin, AsyncActiveRecord):
    """Async Order model with basic relations."""
    __table_name__ = "orders"
    c: ClassVar[FieldProxy] = FieldProxy()

    id: Optional[int] = None
    user_id: int
    order_number: str
    total_amount: Decimal = Field(default=Decimal('0'))
    status: str = 'pending'

    items: ClassVar[HasMany['AsyncOrderItem']] = HasMany(foreign_key='order_id', inverse_of='order')
    user: ClassVar[BelongsTo['AsyncUser']] = BelongsTo(foreign_key='user_id', inverse_of='orders')


class AsyncOrderItem(IntegerPKMixin, TimestampMixin, AsyncActiveRecord):
    """Async Order item model with basic relations."""
    __table_name__ = "order_items"
    c: ClassVar[FieldProxy] = FieldProxy()

    id: Optional[int] = None
    order_id: int
    product_name: str
    quantity: int = Field(ge=1)
    unit_price: Decimal
    subtotal: Decimal = Field(default=Decimal('0'))

    order: ClassVar[BelongsTo['AsyncOrder']] = BelongsTo(foreign_key='order_id', inverse_of='items')
