# Query Optimization

This guide covers techniques for optimizing queries in RhoSocial ActiveRecord to achieve better performance. We'll explore various optimization strategies using practical examples.

## Basic Optimization Techniques 

### Select Only Required Fields

```python
# Instead of
users = User.query().all()

# Select only needed fields
users = User.query()\
    .select('id', 'username', 'email')\
    .all()

# E-commerce example
orders = Order.query()\
    .select('id', 'total', 'status', 'created_at')\
    .all()
```

### Use Indexes Effectively

```python
# Create appropriate indexes
"""
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_posts_user_created ON posts(user_id, created_at);
CREATE INDEX idx_orders_user_status ON orders(user_id, status);
"""

# Query using indexed fields
user = User.query()\
    .where('email = ?', ('john@example.com',))\
    .one()

# Use compound indexes
recent_posts = Post.query()\
    .where('user_id = ?', (1,))\
    .order_by('created_at DESC')\
    .all()

# E-commerce: Use indexes for order lookup
user_orders = Order.query()\
    .where('user_id = ?', (1,))\
    .where('status = ?', ('pending',))\
    .order_by('created_at DESC')\
    .all()
```

### Eager Loading for Related Records

```python
# Instead of this (N+1 problem)
posts = Post.query().all()
for post in posts:
    author = post.author  # Additional query for each post

# Use eager loading
posts = Post.query()\
    .with_('author')\
    .all()

# E-commerce: Load orders with related data
orders = Order.query()\
    .with_('user', 'items.product')\
    .where('status = ?', ('pending',))\
    .all()
```

## Advanced Optimization

### Batch Processing

```python
# Process records in batches
def process_large_dataset():
    batch_size = 1000
    offset = 0
    
    while True:
        # Get batch
        users = User.query()\
            .limit(batch_size)\
            .offset(offset)\
            .all()
        
        if not users:
            break
        
        # Process batch
        for user in users:
            process_user(user)
        
        offset += batch_size

# E-commerce: Batch order processing
def process_pending_orders():
    batch_size = 100
    
    Order.query()\
        .where('status = ?', ('pending',))\
        .batch(batch_size, lambda orders: [
            process_order(order) for order in orders
        ])
```

### Query Caching

```python
from functools import lru_cache
from datetime import timedelta

class CachedQuery:
    @lru_cache(maxsize=100)
    def get_active_users(self):
        return User.query()\
            .where('status = ?', ('active',))\
            .all()
    
    @lru_cache(maxsize=1000)
    def get_product_by_id(self, product_id: int):
        return Product.query()\
            .where('id = ?', (product_id,))\
            .one()
```

### Query Planning

```python
# Analyze query execution plan
query = Order.query()\
    .where('status = ?', ('pending',))\
    .where('total > ?', (Decimal('100.00'),))\
    .order_by('created_at DESC')

# Get execution plan
plan = query.explain()
print(plan)

# Get generated SQL
sql, params = query.to_sql()
print(f"SQL: {sql}")
print(f"Parameters: {params}")
```

## Complex Query Optimization

### Subqueries

```python
# Find users with high-value orders
users = User.query()\
    .where_exists(
        Order.query()
            .where('orders.user_id = users.id')
            .where('orders.total > ?', (Decimal('1000.00'),))
    )\
    .all()

# Find products in recent orders
products = Product.query()\
    .where_exists(
        OrderItem.query()
            .join('orders ON orders.id = order_items.order_id')
            .where('order_items.product_id = products.id')
            .where('orders.created_at > ?', (one_week_ago,))
    )\
    .all()
```

### Optimized Aggregations

```python
# Instead of loading all records
total_posts = len(Post.query().all())

# Use count
total_posts = Post.query().count()

# Efficient aggregation
stats = User.query()\
    .select(
        'COUNT(*) as user_count',
        'AVG(CASE WHEN status = ? THEN 1 ELSE 0 END) as active_ratio',
        'MAX(created_at) as latest_signup'
    )\
    .where('created_at > ?', (one_month_ago,))\
    .one()

# E-commerce: Sales statistics
sales_stats = Order.query()\
    .select(
        'status',
        'COUNT(*) as order_count',
        'SUM(total) as total_sales',
        'AVG(total) as average_order'
    )\
    .where('created_at > ?', (start_date,))\
    .group_by('status')\
    .all()
```

### Join Optimization

```python
# Optimize complex joins
user_activity = User.query()\
    .select(
        'users.id',
        'users.username',
        'COUNT(DISTINCT posts.id) as post_count',
        'COUNT(DISTINCT comments.id) as comment_count'
    )\
    .join('LEFT JOIN posts ON posts.user_id = users.id')\
    .join('LEFT JOIN comments ON comments.user_id = users.id')\
    .group_by('users.id', 'users.username')\
    .having('post_count > 0')\
    .all()

# E-commerce: Product performance
product_metrics = Product.query()\
    .select(
        'products.id',
        'products.name',
        'COUNT(order_items.id) as times_ordered',
        'SUM(order_items.quantity) as units_sold',
        'SUM(order_items.quantity * order_items.price) as revenue'
    )\
    .join('LEFT JOIN order_items ON order_items.product_id = products.id')\
    .join('LEFT JOIN orders ON orders.id = order_items.order_id')\
    .where('orders.status = ?', ('completed',))\
    .group_by('products.id', 'products.name')\
    .having('units_sold > ?', (0,))\
    .order_by('revenue DESC')\
    .all()
```

## Best Practices

1. **Index Strategy**
   - Create indexes for frequently queried columns
   - Use compound indexes for common query patterns
   - Monitor index usage and performance

2. **Query Optimization**
   - Select only needed columns
   - Use eager loading for relationships
   - Process large datasets in batches
   - Optimize complex joins

3. **Performance Monitoring**
   - Use query explain plans
   - Monitor query execution time
   - Track database metrics
   - Identify slow queries

4. **Caching Strategy**
   - Cache frequently accessed data
   - Use appropriate cache duration
   - Implement cache invalidation
   - Monitor cache hit rates

5. **Database Design**
   - Normalize data appropriately
   - Choose correct field types
   - Define proper constraints
   - Plan for scalability

## Next Steps

1. Learn about [Connection Pooling](connection_pooling.md)
2. Study [Memory Management](memory_management.md)
3. Explore [Performance Testing](performance_testing.md)