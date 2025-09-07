# tests/rhosocial/activerecord_test/query/fixtures/models.py
from decimal import Decimal
from typing import Optional, ClassVar

from pydantic import Field, EmailStr

from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin, TimestampMixin
from rhosocial.activerecord.relation import HasMany, BelongsTo, CacheConfig
from ...utils import create_active_record_fixture


class User(IntegerPKMixin, TimestampMixin, ActiveRecord):
    """User model with basic relations."""
    __table_name__ = "users"

    id: Optional[int] = None  # Primary key, null for new records
    username: str  # Required field
    email: EmailStr  # Required field
    age: Optional[int] = Field(..., ge=0, le=100)  # Optional field
    balance: float = 0.0  # Field with default value
    is_active: bool = True  # Field with default value
    # created_at: Optional[str] = None  # Optional field, usually set automatically by database
    # updated_at: Optional[str] = None  # Optional field, usually set automatically by database

    orders: ClassVar[HasMany['Order']] = HasMany(foreign_key='user_id', inverse_of='user')
    # Add relationships to User model
    posts: ClassVar[HasMany['Post']] = HasMany(
        foreign_key='user_id',
        inverse_of='user'
    )
    comments: ClassVar[HasMany['Comment']] = HasMany(
        foreign_key='user_id',
        inverse_of='user'
    )


class JsonUser(IntegerPKMixin, TimestampMixin, ActiveRecord):
    """User model specialized for JSON testing."""
    __table_name__ = "json_users"

    id: Optional[int] = None
    username: str
    email: EmailStr
    age: Optional[int] = Field(None, ge=0, le=100)

    # JSON fields
    settings: Optional[str] = None  # For theme and notification preferences
    tags: Optional[str] = None  # For user roles as array
    profile: Optional[str] = None  # For address and contact information
    roles: Optional[str] = None  # For admin/editor roles
    scores: Optional[str] = None  # For test scores in different subjects
    subscription: Optional[str] = None  # For subscription type and expiration
    preferences: Optional[str] = None  # For user preferences including region


class Order(IntegerPKMixin, TimestampMixin, ActiveRecord):
    """Order model with basic relations."""
    __table_name__ = "orders"

    id: Optional[int] = None
    user_id: int
    order_number: str
    total_amount: Decimal = Field(default=Decimal('0'))
    status: str = 'pending'  # pending, paid, shipped, completed, cancelled

    items: ClassVar[HasMany['OrderItem']] = HasMany(foreign_key='order_id', inverse_of='order')
    user: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id', inverse_of='orders')


class OrderItem(IntegerPKMixin, TimestampMixin, ActiveRecord):
    """Order item model with basic relations."""
    __table_name__ = "order_items"

    id: Optional[int] = None
    order_id: int
    product_name: str
    quantity: int = Field(ge=1)
    unit_price: Decimal
    subtotal: Decimal = Field(default=Decimal('0'))

    order: ClassVar[BelongsTo['Order']] = BelongsTo(foreign_key='order_id', inverse_of='items')


# Test-specific model variations

class OrderWithCustomCache(Order):
    """Order model with custom TTL cache configuration."""
    __table_name__ = "orders"

    # Override user relation with custom cache TTL
    user: ClassVar[BelongsTo['User']] = BelongsTo(
        foreign_key='user_id',
        cache_config=CacheConfig(ttl=1)  # 1 second TTL
    )


class OrderWithLimitedCache(Order):
    """Order model with limited cache size configuration."""
    __table_name__ = "orders"

    # Override user relation with limited cache size
    user: ClassVar[BelongsTo['User']] = BelongsTo(
        foreign_key='user_id',
        cache_config=CacheConfig(max_size=2)
    )


class OrderWithComplexCache(Order):
    """Order model with complex cache configuration."""
    __table_name__ = "orders"

    # Override relations with different cache settings
    user: ClassVar[BelongsTo['User']] = BelongsTo(
        foreign_key='user_id',
        cache_config=CacheConfig(ttl=300, max_size=100)
    )

    items: ClassVar[HasMany['OrderItem']] = HasMany(
        foreign_key='order_id',
        cache_config=CacheConfig(ttl=60, max_size=1000),
        # order_by=['created_at DESC']
    )


# Create test fixtures
user_class = create_active_record_fixture(User)
order_class = create_active_record_fixture(Order)
order_item_class = create_active_record_fixture(OrderItem)

order_with_custom_cache_class = create_active_record_fixture(OrderWithCustomCache)
order_with_limited_cache_class = create_active_record_fixture(OrderWithLimitedCache)
order_with_complex_cache_class = create_active_record_fixture(OrderWithComplexCache)


class Post(IntegerPKMixin, TimestampMixin, ActiveRecord):
    """Post model with user and comments relations."""
    __table_name__ = "posts"

    id: Optional[int] = None
    user_id: int
    title: str
    content: str
    status: str = 'published'  # draft, published, archived

    user: ClassVar[BelongsTo['User']] = BelongsTo(
        foreign_key='user_id',
        inverse_of='posts'
    )
    comments: ClassVar[HasMany['Comment']] = HasMany(
        foreign_key='post_id',
        inverse_of='post'
    )


class Comment(IntegerPKMixin, TimestampMixin, ActiveRecord):
    """Comment model with user and post relations."""
    __table_name__ = "comments"

    id: Optional[int] = None
    user_id: int
    post_id: int
    content: str
    is_hidden: bool = False

    user: ClassVar[BelongsTo['User']] = BelongsTo(
        foreign_key='user_id',
        inverse_of='comments'
    )
    post: ClassVar[BelongsTo['Post']] = BelongsTo(
        foreign_key='post_id',
        inverse_of='comments'
    )


# # Add relationships to User model  # Note! Relations defined after instantiation have nothing to do with existing instances.
# User.posts: ClassVar[HasMany['Post']] = HasMany(
#     foreign_key='user_id',
#     inverse_of='user'
# )
# User.comments: ClassVar[HasMany['Comment']] = HasMany(
#     foreign_key='user_id',
#     inverse_of='user'
# )

# Create test fixtures
post_class = create_active_record_fixture(Post)
comment_class = create_active_record_fixture(Comment)
