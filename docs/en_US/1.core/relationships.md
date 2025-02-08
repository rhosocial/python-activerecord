# Model Relationships

RhoSocial ActiveRecord provides robust support for defining and working with relationships between models. This guide covers all aspects of model relationships.

## Types of Relationships

### One-to-One (HasOne/BelongsTo)

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.relations import HasOne, BelongsTo

class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    name: str
    
    # One-to-one relationship
    profile: 'Profile' = HasOne('Profile', foreign_key='user_id')

class Profile(ActiveRecord):
    __table_name__ = 'profiles'
    
    id: int
    user_id: int
    bio: str
    avatar_url: str
    
    # Inverse relationship
    user: User = BelongsTo('User', foreign_key='user_id')

# Usage
user = User.find_one(1)
profile = user.profile  # Access related profile
print(profile.user.name)  # Access back to user
```

### One-to-Many (HasMany/BelongsTo)

```python
class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    name: str
    
    # One-to-many relationship
    posts: List['Post'] = HasMany('Post', foreign_key='user_id')
    comments: List['Comment'] = HasMany('Comment', foreign_key='user_id')

class Post(ActiveRecord):
    __table_name__ = 'posts'
    
    id: int
    user_id: int
    content: str
    
    # Inverse relationship
    author: User = BelongsTo('User', foreign_key='user_id')
    # One-to-many for comments
    comments: List['Comment'] = HasMany('Comment', foreign_key='post_id')

class Comment(ActiveRecord):
    __table_name__ = 'comments'
    
    id: int
    user_id: int
    post_id: int
    content: str
    
    # Multiple belongs-to relationships
    author: User = BelongsTo('User', foreign_key='user_id')
    post: Post = BelongsTo('Post', foreign_key='post_id')
```

## E-commerce Example

```python
from decimal import Decimal
from datetime import datetime

class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    email: str
    name: str
    
    # Relationships
    orders: List['Order'] = HasMany('Order', foreign_key='user_id')
    cart: 'ShoppingCart' = HasOne('ShoppingCart', foreign_key='user_id')

class Product(ActiveRecord):
    __table_name__ = 'products'
    
    id: int
    name: str
    price: Decimal
    stock: int
    
    # Relationships
    category: 'Category' = BelongsTo('Category', foreign_key='category_id')
    order_items: List['OrderItem'] = HasMany('OrderItem', foreign_key='product_id')

class Order(ActiveRecord):
    __table_name__ = 'orders'
    
    id: int
    user_id: int
    total: Decimal
    status: str
    created_at: datetime
    
    # Relationships
    user: User = BelongsTo('User', foreign_key='user_id')
    items: List['OrderItem'] = HasMany('OrderItem', foreign_key='order_id')
    shipping_address: 'Address' = HasOne('Address', foreign_key='order_id')

class OrderItem(ActiveRecord):
    __table_name__ = 'order_items'
    
    id: int
    order_id: int
    product_id: int
    quantity: int
    price: Decimal
    
    # Relationships
    order: Order = BelongsTo('Order', foreign_key='order_id')
    product: Product = BelongsTo('Product', foreign_key='product_id')
```

## Working with Relationships

### Eager Loading

```python
# Load user with related orders and their items
user = User.query()\
    .with_('orders.items.product')\
    .find_one(1)

# Access eagerly loaded relationships
for order in user.orders:
    print(f"Order #{order.id}")
    for item in order.items:
        print(f"- {item.quantity}x {item.product.name}")

# Load orders with multiple relations
orders = Order.query()\
    .with_('user', 'items.product', 'shipping_address')\
    .where('status = ?', ('pending',))\
    .all()
```

### Relationship Queries

```python
# Query through relationships
user = User.find_one(1)

# Get user's recent orders
recent_orders = user.orders_query()\
    .where('created_at > ?', (one_week_ago,))\
    .order_by('created_at DESC')\
    .all()

# Find products in user's orders
ordered_products = Product.query()\
    .join('order_items')\
    .join('orders')\
    .where('orders.user_id = ?', (user.id,))\
    .all()
```

### Creating Related Records

```python
# Create user with profile
user = User(name="John Doe")
user.save()

profile = Profile(
    user_id=user.id,
    bio="Python developer",
    avatar_url="path/to/avatar.jpg"
)
profile.save()

# Create order with items
def create_order(user: User, items: List[tuple[Product, int]]) -> Order:
    with Order.transaction():
        # Create order
        order = Order(
            user_id=user.id,
            total=Decimal('0'),
            status='pending',
            created_at=datetime.now()
        )
        order.save()
        
        # Add items
        total = Decimal('0')
        for product, quantity in items:
            item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=quantity,
                price=product.price
            )
            item.save()
            total += product.price * quantity
        
        # Update order total
        order.total = total
        order.save()
        
        return order
```

### Relationship Conditions

```python
from rhosocial.activerecord.relations import HasMany

class User(ActiveRecord):
    # Get only active orders
    active_orders: List['Order'] = HasMany(
        'Order',
        foreign_key='user_id',
        conditions={'status': 'active'}
    )
    
    # Get orders by type with ordering
    premium_orders: List['Order'] = HasMany(
        'Order',
        foreign_key='user_id',
        conditions={'type': 'premium'},
        order_by='created_at DESC'
    )
```

### Relationship Events

```python
class Order(ActiveRecord):
    def __init__(self, **data):
        super().__init__(**data)
        # Update totals when items change
        self.on(ModelEvent.AFTER_SAVE, self._update_totals)
    
    def _update_totals(self, instance: 'Order', is_new: bool):
        if hasattr(self, 'items'):
            self.total = sum(item.price * item.quantity for item in self.items)
            self.save()
```

## Best Practices

1. **Eager Loading**: Use eager loading to avoid N+1 query problems
2. **Transactions**: Use transactions when creating related records
3. **Validation**: Include relationship validation in models
4. **Naming**: Use clear, descriptive names for relationships
5. **Documentation**: Document relationship constraints and assumptions

## Next Steps

1. Learn about [Basic Operations](basic_operations.md)
2. Study [Querying](querying.md)
3. Understand [Transactions](../2.features/transactions.md)