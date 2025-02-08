# Basic Operations

This guide covers the fundamental database operations (CRUD) supported by RhoSocial ActiveRecord. We'll use practical examples from both a social media application and an e-commerce system.

## CRUD Operations Overview

### Create

Creating new records involves:
1. Instantiating model objects
2. Setting attributes
3. Saving to database

### Read 

Reading records includes:
1. Finding by primary key
2. Finding by conditions 
3. Loading multiple records

### Update

Updating existing records through:
1. Modifying attributes
2. Saving changes
3. Batch updates

### Delete

Deleting records via:
1. Individual deletion
2. Batch deletion
3. Soft deletion (optional)

## Social Media Example

Let's implement basic operations for a social media platform:

```python
from rhosocial.activerecord import ActiveRecord
from datetime import datetime
from typing import Optional, List

# Model Definitions
class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    username: str
    email: str
    created_at: datetime

class Post(ActiveRecord):
    __table_name__ = 'posts'
    
    id: int
    user_id: int
    content: str
    created_at: datetime

class Comment(ActiveRecord):
    __table_name__ = 'comments'
    
    id: int
    post_id: int
    user_id: int
    content: str
    created_at: datetime
```

### Creating Records

```python
# Create a new user
user = User(
    username='john_doe',
    email='john@example.com',
    created_at=datetime.now()
)
user.save()

# Create a post
post = Post(
    user_id=user.id,
    content='Hello, World!',
    created_at=datetime.now()
)
post.save()

# Create a comment
comment = Comment(
    post_id=post.id,
    user_id=user.id,
    content='Great post!',
    created_at=datetime.now()
)
comment.save()
```

### Reading Records

```python
# Find user by ID
user = User.find_one(1)

# Find user by email
user = User.find_one({'email': 'john@example.com'})

# Get all posts for a user
posts = Post.find_all({'user_id': user.id})

# Get recent comments
recent_comments = Comment.query()\
    .where('created_at > ?', (one_day_ago,))\
    .order_by('created_at DESC')\
    .limit(10)\
    .all()
```

### Updating Records

```python
# Update user profile
user = User.find_one(1)
user.username = 'john_smith'
user.save()

# Update post content
post = Post.find_one(1)
post.content = 'Updated content'
post.save()

# Batch update comments
Comment.query()\
    .where('user_id = ?', (user.id,))\
    .update({'updated_at': datetime.now()})
```

### Deleting Records

```python
# Delete a comment
comment = Comment.find_one(1)
comment.delete()

# Delete all posts by user
Post.query()\
    .where('user_id = ?', (user.id,))\
    .delete()
```

## E-Commerce Example

Let's implement operations for an e-commerce system:

```python
from decimal import Decimal

class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    email: str
    name: str

class Order(ActiveRecord):
    __table_name__ = 'orders'
    
    id: int
    user_id: int
    total: Decimal
    status: str
    created_at: datetime

class Product(ActiveRecord):
    __table_name__ = 'products'
    
    id: int
    name: str
    price: Decimal
    stock: int

class OrderItem(ActiveRecord):
    __table_name__ = 'order_items'
    
    id: int
    order_id: int
    product_id: int
    quantity: int
    price: Decimal
```

### Creating Orders

```python
# Create order with items
def create_order(user_id: int, items: List[dict]) -> Order:
    with Order.transaction():
        # Create order
        order = Order(
            user_id=user_id,
            total=Decimal('0'),
            status='pending',
            created_at=datetime.now()
        )
        order.save()
        
        # Add items
        total = Decimal('0')
        for item in items:
            product = Product.find_one(item['product_id'])
            
            # Create order item
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=item['quantity'],
                price=product.price
            )
            order_item.save()
            
            # Update total
            total += product.price * item['quantity']
        
        # Update order total
        order.total = total
        order.save()
        
        return order

# Usage
order = create_order(user_id=1, items=[
    {'product_id': 1, 'quantity': 2},
    {'product_id': 2, 'quantity': 1}
])
```

### Reading Orders

```python
# Get order details
order = Order.find_one(1)

# Get user's orders
user_orders = Order.find_all({'user_id': 1})

# Get order items
items = OrderItem.find_all({'order_id': order.id})

# Get pending orders
pending_orders = Order.query()\
    .where('status = ?', ('pending',))\
    .order_by('created_at DESC')\
    .all()
```

### Updating Orders

```python
# Update order status
order = Order.find_one(1)
order.status = 'processing'
order.save()

# Update product stock
def update_stock(product_id: int, quantity: int):
    with Product.transaction():
        product = Product.find_one_or_fail(product_id)
        product.stock += quantity
        product.save()

# Batch update orders
Order.query()\
    .where('status = ?', ('pending',))\
    .update({'status': 'cancelled'})
```

### Deleting Orders

```python
# Cancel order
def cancel_order(order_id: int):
    with Order.transaction():
        # Delete order items
        OrderItem.query()\
            .where('order_id = ?', (order_id,))\
            .delete()
        
        # Delete order
        order = Order.find_one_or_fail(order_id)
        order.delete()

# Bulk delete old orders
Order.query()\
    .where('created_at < ?', (one_year_ago,))\
    .delete()
```

## Transaction Support

ActiveRecord provides transaction support for atomic operations:

```python
# Simple transaction
with Order.transaction():
    order.status = 'completed'
    order.save()
    
    product.stock -= 1
    product.save()

# Nested transactions
with Order.transaction():
    order.save()
    
    with Product.transaction():
        product.save()
```

## Error Handling

Handle database operations safely:

```python
from rhosocial.activerecord.backend import DatabaseError, RecordNotFound

try:
    user = User.find_one_or_fail(999)
except RecordNotFound:
    print("User not found")

try:
    with Order.transaction():
        order.save()
        raise ValueError("Something went wrong")
except ValueError:
    print("Transaction rolled back")
except DatabaseError as e:
    print(f"Database error: {e}")
```

## Best Practices

1. **Use Transactions**: Wrap related operations in transactions
2. **Batch Operations**: Use batch updates/deletes for multiple records
3. **Error Handling**: Always handle potential database errors
4. **Validation**: Validate data before saving
5. **Query Optimization**: Use eager loading for related records

## Next Steps

1. Learn about [Querying](querying.md) for advanced query operations
2. Study [Relationships](relationships.md) for handling related records
3. Explore [Transactions](../2.features/transactions.md) for more details