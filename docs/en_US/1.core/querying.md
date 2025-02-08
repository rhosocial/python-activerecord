# Query Building

This guide covers the comprehensive query building capabilities of RhoSocial ActiveRecord. We'll explore how to construct efficient and complex queries using practical examples from both social media and e-commerce applications.

## Query Builder Overview

The query builder provides a fluent interface for constructing SQL queries:

```python
# Basic query structure
User.query()\
    .where('status = ?', ('active',))\
    .order_by('created_at DESC')\
    .limit(10)\
    .all()
```

## Basic Queries

### Simple Conditions

```python
# Social Media Example
# Find active users
users = User.query()\
    .where('status = ?', ('active',))\
    .all()

# Find recent posts
posts = Post.query()\
    .where('created_at > ?', (one_day_ago,))\
    .order_by('created_at DESC')\
    .all()

# E-commerce Example
# Find products in stock
products = Product.query()\
    .where('stock > 0')\
    .order_by('price ASC')\
    .all()

# Find pending orders
orders = Order.query()\
    .where('status = ?', ('pending',))\
    .all()
```

### Multiple Conditions

```python
# Find active users with verified email
users = User.query()\
    .where('status = ?', ('active',))\
    .where('email_verified = ?', (True,))\
    .all()

# Find products by category and price range
products = Product.query()\
    .where('category_id = ?', (1,))\
    .where('price >= ?', (Decimal('10.00'),))\
    .where('price <= ?', (Decimal('50.00'),))\
    .all()
```

### OR Conditions

```python
# Find users by username or email
users = User.query()\
    .where('username = ?', ('john_doe',))\
    .or_where('email = ?', ('john@example.com',))\
    .all()

# Find orders by status
orders = Order.query()\
    .where('status = ?', ('pending',))\
    .or_where('status = ?', ('processing',))\
    .all()
```

### Complex Conditions

```python
# Find posts with complex criteria
posts = Post.query()\
    .where('user_id = ?', (1,))\
    .start_or_group()\
        .where('status = ?', ('public',))\
        .or_where('featured = ?', (True,))\
    .end_or_group()\
    .where('deleted_at IS NULL')\
    .all()

# Find orders with multiple conditions
orders = Order.query()\
    .where('total > ?', (Decimal('100.00'),))\
    .start_or_group()\
        .where('status = ?', ('pending',))\
        .or_where('status = ?', ('processing',))\
    .end_or_group()\
    .where('created_at > ?', (one_week_ago,))\
    .all()
```

## Advanced Queries

### Range Queries

```python
# Find products in price range
products = Product.query()\
    .between('price', Decimal('10.00'), Decimal('50.00'))\
    .all()

# Find orders by date range
orders = Order.query()\
    .between('created_at', start_date, end_date)\
    .all()
```

### List Queries

```python
# Find users by ID list
users = User.query()\
    .in_list('id', [1, 2, 3])\
    .all()

# Find products by category
products = Product.query()\
    .in_list('category_id', category_ids)\
    .all()

# Exclude certain statuses
orders = Order.query()\
    .not_in('status', ['cancelled', 'refunded'])\
    .all()
```

### Pattern Matching

```python
# Search users by username pattern
users = User.query()\
    .like('username', 'john%')\
    .all()

# Search products by name
products = Product.query()\
    .like('name', '%phone%')\
    .all()

# Find comments not containing word
comments = Comment.query()\
    .not_like('content', '%spam%')\
    .all()
```

### NULL Checks

```python
# Find users without phone number
users = User.query()\
    .is_null('phone')\
    .all()

# Find active orders
orders = Order.query()\
    .is_null('cancelled_at')\
    .all()

# Find verified users
users = User.query()\
    .is_not_null('verified_at')\
    .all()
```

### Ordering

```python
# Order by single column
users = User.query()\
    .order_by('created_at DESC')\
    .all()

# Order by multiple columns
posts = Post.query()\
    .order_by('featured DESC', 'created_at DESC')\
    .all()

# Complex ordering
products = Product.query()\
    .order_by('category_id ASC', 'price DESC')\
    .all()
```

### Pagination

```python
# Basic pagination
page_size = 20
page = 1

users = User.query()\
    .order_by('created_at DESC')\
    .limit(page_size)\
    .offset((page - 1) * page_size)\
    .all()

# Implement paginated results
def get_paginated_results(query, page: int, page_size: int):
    total = query.count()
    items = query\
        .limit(page_size)\
        .offset((page - 1) * page_size)\
        .all()
    
    return {
        'items': items,
        'total': total,
        'page': page,
        'pages': (total + page_size - 1) // page_size
    }

# Usage
results = get_paginated_results(
    Product.query().where('stock > 0'),
    page=1,
    page_size=20
)
```

## Aggregate Queries

### Basic Aggregates

```python
# Count total users
total_users = User.query().count()

# Get sum of order totals
total_sales = Order.query()\
    .where('status = ?', ('completed',))\
    .sum('total')

# Get average product price
avg_price = Product.query().avg('price')

# Get highest and lowest prices
max_price = Product.query().max('price')
min_price = Product.query().min('price')
```

### Grouped Aggregates

```python
# Count posts by user
post_counts = Post.query()\
    .group_by('user_id')\
    .select('user_id', 'COUNT(*) as post_count')\
    .all()

# Sum order totals by status
sales_by_status = Order.query()\
    .group_by('status')\
    .select('status', 'SUM(total) as total_sales')\
    .all()

# Average price by category
avg_prices = Product.query()\
    .group_by('category_id')\
    .select('category_id', 'AVG(price) as avg_price')\
    .all()
```

### Complex Aggregates

```python
# Get user engagement metrics
user_metrics = User.query()\
    .select(
        'users.id',
        'COUNT(DISTINCT posts.id) as post_count',
        'COUNT(DISTINCT comments.id) as comment_count'
    )\
    .join('LEFT JOIN posts ON posts.user_id = users.id')\
    .join('LEFT JOIN comments ON comments.user_id = users.id')\
    .group_by('users.id')\
    .having('post_count > 0')\
    .all()

# Get product sales metrics
product_metrics = Product.query()\
    .select(
        'products.id',
        'products.name',
        'COUNT(order_items.id) as times_ordered',
        'SUM(order_items.quantity) as units_sold',
        'SUM(order_items.quantity * order_items.price) as total_revenue'
    )\
    .join('LEFT JOIN order_items ON order_items.product_id = products.id')\
    .group_by('products.id', 'products.name')\
    .having('units_sold > ?', (0,))\
    .order_by('total_revenue DESC')\
    .all()
```

## Eager Loading

### Basic Eager Loading

```python
# Load posts with author
posts = Post.query()\
    .with_('author')\
    .all()

# Load orders with items
orders = Order.query()\
    .with_('items')\
    .all()
```

### Nested Eager Loading

```python
# Load posts with author and comments
posts = Post.query()\
    .with_('author', 'comments.author')\
    .all()

# Load orders with items and products
orders = Order.query()\
    .with_('items.product', 'user')\
    .all()

# Access eager loaded relations
for order in orders:
    print(f"Order #{order.id} by {order.user.name}")
    for item in order.items:
        print(f"- {item.quantity}x {item.product.name}")
```

### Conditional Eager Loading

```python
# Load active users with recent posts
users = User.query()\
    .with_(
        ('posts', lambda q: q.where('created_at > ?', (one_week_ago,)))
    )\
    .where('status = ?', ('active',))\
    .all()

# Load orders with specific items
orders = Order.query()\
    .with_(
        ('items', lambda q: q
            .where('quantity > ?', (1,))
            .order_by('quantity DESC')
        )
    )\
    .all()
```

## Query Optimization

### Selecting Specific Columns

```python
# Select only needed fields
users = User.query()\
    .select('id', 'username', 'email')\
    .all()

# Select with calculated fields
products = Product.query()\
    .select(
        'id',
        'name',
        'price',
        'stock',
        '(price * stock) as inventory_value'
    )\
    .all()
```

### Using Indexes

```python
# Query using indexed columns
user = User.query()\
    .where('email = ?', ('john@example.com',))\
    .one()

# Compound index usage
orders = Order.query()\
    .where('user_id = ?', (1,))\
    .where('status = ?', ('pending',))\
    .order_by('created_at DESC')\
    .all()
```

### Query Explanation

```python
# Get query execution plan
query = Product.query()\
    .where('category_id = ?', (1,))\
    .order_by('price DESC')

plan = query.explain()
print(plan)

# Get generated SQL
sql, params = query.to_sql()
print(f"SQL: {sql}")
print(f"Parameters: {params}")
```

## Advanced Features

### Raw Queries

```python
# Execute raw SQL
users = User.query()\
    .raw_sql(
        "SELECT * FROM users WHERE reputation > ? ORDER BY reputation DESC",
        (1000,)
    )\
    .all()

# Complex raw query
popular_posts = Post.query()\
    .raw_sql("""
        SELECT 
            posts.*,
            COUNT(comments.id) as comment_count
        FROM posts
        LEFT JOIN comments ON comments.post_id = posts.id
        GROUP BY posts.id
        HAVING comment_count > ?
        ORDER BY comment_count DESC
    """, (10,))\
    .all()
```

### Subqueries

```python
# Find users with popular posts
users = User.query()\
    .where_exists(
        Post.query()
            .where('posts.user_id = users.id')
            .where('posts.likes > ?', (100,))
    )\
    .all()

# Find products with recent orders
products = Product.query()\
    .where_exists(
        OrderItem.query()
            .join('orders ON orders.id = order_items.order_id')
            .where('order_items.product_id = products.id')
            .where('orders.created_at > ?', (one_month_ago,))
    )\
    .all()
```

### Custom Query Scopes

```python
class User(ActiveRecord):
    @classmethod
    def active(cls) -> 'Query':
        return cls.query().where('status = ?', ('active',))
    
    @classmethod
    def with_posts(cls) -> 'Query':
        return cls.query()\
            .with_('posts')\
            .where_exists(
                Post.query().where('posts.user_id = users.id')
            )

# Usage
active_users = User.active().all()
users_with_posts = User.with_posts().all()
```

## Best Practices

1. **Use Eager Loading**: Avoid N+1 query problems by using `with_()` for related records
2. **Index Usage**: Design queries to utilize database indexes
3. **Select Specific Columns**: Only select needed columns to reduce data transfer
4. **Batch Processing**: Use pagination for large result sets
5. **Query Optimization**: Use `explain()` to understand and optimize query performance

## Next Steps

1. Study [Relationships](relationships.md) for advanced relationship queries
2. Learn about [Transactions](../2.features/transactions.md) for data consistency
3. Explore [Performance](../5.performance/query_optimization.md) for optimization tips