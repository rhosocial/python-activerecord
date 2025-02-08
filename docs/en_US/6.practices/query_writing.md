# Query Writing Best Practices

This guide covers best practices for writing efficient and maintainable queries in RhoSocial ActiveRecord.

## Basic Query Structure

### Simple Queries

```python
# Good: Clear and readable
users = User.query()\
    .where('status = ?', ('active',))\
    .order_by('created_at DESC')\
    .limit(10)\
    .all()

# Bad: Hard to read and maintain
users = User.query().where('status = ? AND created_at > ? AND (type = ? OR type = ?)', 
    ('active', one_week_ago, 'admin', 'staff')).order_by('created_at DESC').limit(10).all()
```

### Query Methods

```python
class User(ActiveRecord):
    @classmethod
    def active(cls):
        return cls.query().where('status = ?', ('active',))
    
    @classmethod
    def recent(cls, days: int = 7):
        cutoff = datetime.now() - timedelta(days=days)
        return cls.query().where('created_at > ?', (cutoff,))
    
    @classmethod
    def search(cls, term: str):
        return cls.query()\
            .where('username LIKE ? OR email LIKE ?', 
                  (f"%{term}%", f"%{term}%"))

# Usage
active_recent_users = User.active().recent(30).all()
```

## Complex Queries

### Combining Conditions

```python
# E-commerce: Find high-value orders
def find_valuable_orders(min_amount: Decimal):
    return Order.query()\
        .where('status = ?', ('completed',))\
        .where('total >= ?', (min_amount,))\
        .order_by('total DESC')

# Social media: Find trending posts
def find_trending_posts():
    return Post.query()\
        .select(
            'posts.*',
            'COUNT(likes.id) as like_count',
            'COUNT(comments.id) as comment_count'
        )\
        .join('LEFT JOIN likes ON likes.post_id = posts.id')\
        .join('LEFT JOIN comments ON comments.post_id = posts.id')\
        .where('posts.created_at > ?', (one_day_ago,))\
        .group_by('posts.id')\
        .having('like_count >= ?', (10,))\
        .order_by('like_count DESC')
```

### OR Conditions

```python
# Group related conditions
users = User.query()\
    .where('status = ?', ('active',))\
    .start_or_group()\
        .where('role = ?', ('admin',))\
        .or_where('role = ?', ('moderator',))\
    .end_or_group()\
    .all()

# E-commerce: Search products
def search_products(term: str):
    return Product.query()\
        .where('stock > 0')\
        .start_or_group()\
            .where('name LIKE ?', (f"%{term}%",))\
            .or_where('description LIKE ?', (f"%{term}%",))\
        .end_or_group()\
        .order_by('name ASC')
```

## Relationship Queries

### Eager Loading

```python
# Load necessary relationships
posts = Post.query()\
    .with_('author', 'comments.author')\
    .where('created_at > ?', (one_week_ago,))\
    .all()

# E-commerce: Order details
orders = Order.query()\
    .with_('user', 'items.product')\
    .where('status = ?', ('pending',))\
    .order_by('created_at DESC')\
    .all()
```

### Relationship Conditions

```python
# Find users with recent posts
users = User.query()\
    .where_exists(
        Post.query()
            .where('posts.user_id = users.id')
            .where('posts.created_at > ?', (one_day_ago,))
    )\
    .all()

# E-commerce: Find products in orders
products = Product.query()\
    .where_exists(
        OrderItem.query()
            .join('orders ON orders.id = order_items.order_id')
            .where('order_items.product_id = products.id')
            .where('orders.status = ?', ('completed',))
    )\
    .all()
```

## Performance Optimization

### Select Specific Fields

```python
# Select only needed fields
user_emails = User.query()\
    .select('id', 'email')\
    .where('status = ?', ('active',))\
    .all()

# E-commerce: Order summary
order_summary = Order.query()\
    .select('id', 'total', 'status', 'created_at')\
    .where('user_id = ?', (user_id,))\
    .order_by('created_at DESC')\
    .all()
```

### Batch Processing

```python
def process_users_in_batches(batch_size: int = 1000):
    """Process users in batches to manage memory."""
    processed = 0
    
    while True:
        users = User.query()\
            .where('processed = ?', (False,))\
            .limit(batch_size)\
            .all()
        
        if not users:
            break
        
        for user in users:
            process_user(user)
            processed += 1
    
    return processed
```

## Query Organization

### Query Objects

```python
class OrderQuery:
    @classmethod
    def pending(cls):
        return Order.query().where('status = ?', ('pending',))
    
    @classmethod
    def for_user(cls, user_id: int):
        return Order.query().where('user_id = ?', (user_id,))
    
    @classmethod
    def recent(cls, days: int = 7):
        cutoff = datetime.now() - timedelta(days=days)
        return Order.query().where('created_at > ?', (cutoff,))
    
    @classmethod
    def high_value(cls, amount: Decimal):
        return Order.query().where('total >= ?', (amount,))

# Usage
pending_orders = OrderQuery.pending()\
    .for_user(user_id)\
    .recent()\
    .all()
```

### Scoped Queries

```python
class Post(ActiveRecord):
    @classmethod
    def published(cls):
        return cls.query().where('published = ?', (True,))
    
    @classmethod
    def trending(cls):
        return cls.query()\
            .where('created_at > ?', (one_day_ago,))\
            .where('likes_count >= ?', (100,))
    
    @classmethod
    def by_category(cls, category: str):
        return cls.query().where('category = ?', (category,))

class Product(ActiveRecord):
    @classmethod
    def in_stock(cls):
        return cls.query().where('stock > 0')
    
    @classmethod
    def featured(cls):
        return cls.query().where('featured = ?', (True,))
    
    @classmethod
    def price_range(cls, min_price: Decimal, max_price: Decimal):
        return cls.query()\
            .where('price >= ?', (min_price,))\
            .where('price <= ?', (max_price,))
```

## Best Practices

1. **Query Structure**
   - Write clear, readable queries
   - Break complex queries into methods
   - Use proper indentation
   - Comment complex logic

2. **Performance**
   - Select only needed fields
   - Use eager loading appropriately
   - Process large datasets in batches
   - Monitor query performance

3. **Organization**
   - Create query objects for complex queries
   - Use scoped queries for common filters
   - Maintain consistent naming
   - Document query methods

4. **Relationships**
   - Use eager loading to prevent N+1 queries
   - Join tables appropriately
   - Consider query impact on related models
   - Cache complex relationship queries

5. **Maintenance**
   - Write testable queries
   - Document complex queries
   - Monitor query performance
   - Refactor when needed

## Next Steps

1. Study [Transaction Usage](transaction_usage.md)
2. Learn about [Error Handling](error_handling.md)
3. Review [Testing Strategy](testing_strategy.md)