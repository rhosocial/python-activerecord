---
name: user-query-advanced
description: Advanced query techniques for rhosocial-activerecord - CTEs, window functions, aggregations, complex JOINs, and optimization
license: MIT
compatibility: opencode
metadata:
  category: querying
  level: advanced
  audience: users
  order: 4
  prerequisites:
    - user-getting-started
    - user-modeling-guide
---

## What I do

Master advanced query techniques:
- CTEs (Common Table Expressions) including recursive
- Window functions (ROW_NUMBER, RANK, etc.)
- Complex aggregations and GROUP BY
- Multi-table JOINs
- Set operations (UNION, INTERSECT, EXCEPT)
- Query optimization and debugging

## When to use me

- Building complex analytical queries
- Working with hierarchical data
- Need ranking or windowing functions
- Optimizing query performance
- Understanding CTEQuery and SetOperationQuery

## Prerequisites

- Models with FieldProxy configured
- Basic query building knowledge
- Understanding of SQL concepts

## CTEs (Common Table Expressions)

### Basic CTE

```python
from rhosocial.activerecord.query import CTEQuery

# Define CTE
cte = CTEQuery(
    backend=User.backend()
).with_cte(
    'active_users',
    User.query().where(User.c.is_active == True)
).with_cte(
    'recent_orders',
    Order.query().where(Order.c.created_at >= '2024-01-01')
)

# Use CTE in main query
results = cte.query("""
    SELECT u.name, COUNT(o.id) as order_count
    FROM active_users u
    LEFT JOIN recent_orders o ON u.id = o.user_id
    GROUP BY u.id, u.name
""").execute()
```

### Recursive CTE (Hierarchical Data)

```python
from rhosocial.activerecord.query import CTEQuery

# Get all subordinates recursively
org_chart = CTEQuery(backend=Employee.backend()).with_recursive_cte(
    'subordinates',
    anchor=Employee.query().where(Employee.c.id == manager_id),
    recursive=Employee.query().where(Employee.c.manager_id == 'subordinates.id')
)

results = org_chart.query("""
    SELECT * FROM subordinates ORDER BY level
""").execute()
```

## Window Functions

```python
from rhosocial.activerecord.backend.expression.window import Window, RowNumber, Rank, DenseRank

# Rank products by sales within each category
window = Window.partition_by(Product.c.category_id).order_by((Product.c.sales, "DESC"))
rank_col = Rank().over(window).as_('sales_rank')

results = Product.query().select(
    Product.c.name,
    Product.c.category_id,
    Product.c.sales,
    rank_col
).aggregate()

# Running total
window = Window.partition_by(Order.c.user_id).order_by(Order.c.created_at)
running_total = Sum(Order.c.amount).over(window).as_('running_total')

results = Order.query().select(
    Order.c.user_id,
    Order.c.amount,
    running_total
).aggregate()
```

## Aggregations

### GROUP BY with HAVING

```python
from rhosocial.activerecord.backend.expression.aggregates import Count, Sum, Avg, Max, Min

# Count orders per user with totals
results = Order.query().select(
    Order.c.user_id,
    Count().as_('order_count'),
    Sum(Order.c.amount).as_('total_spent'),
    Avg(Order.c.amount).as_('avg_order')
).group_by(
    Order.c.user_id
).having(
    Count() > 5  # Only users with 5+ orders
).aggregate()
```

### Multiple Aggregations

```python
# Complex sales report
results = Order.query().select(
    Order.c.status,
    Order.c.created_at.year().as_('year'),
    Count().as_('count'),
    Sum(Order.c.amount).as_('revenue'),
    Avg(Order.c.amount).as_('avg_value'),
    Max(Order.c.amount).as_('max_value')
).group_by(
    Order.c.status,
    Order.c.created_at.year()
).order_by(
    Order.c.created_at.year()
).aggregate()
```

## Complex JOINs

### Multi-Table Join

```python
# Users with their posts and comments
results = User.query().select(
    User.c.name,
    Post.c.title,
    Comment.c.content
).join(
    Post,
    on=User.c.id == Post.c.user_id
).left_join(
    Comment,
    on=Post.c.id == Comment.c.post_id
).all()
```

### Self Join

```python
# Employees with their managers
Employee.alias('e')  # Create alias
Employee.alias('m')  # Manager alias

results = Employee.query('e').select(
    Employee.c('e').name.as_('employee'),
    Employee.c('m').name.as_('manager')
).left_join(
    Employee.as_('m'),
    on=Employee.c('e').manager_id == Employee.c('m').id
).all()
```

## Set Operations

### UNION

```python
from rhosocial.activerecord.query import ActiveQuery

# Combine active users and recent signups
active_users = User.query().where(User.c.last_login >= '2024-01-01')
recent_signups = User.query().where(User.c.created_at >= '2024-06-01')

all_users = active_users.union(recent_signups).all()
```

### INTERSECT and EXCEPT

```python
# Users who are both premium AND active
premium_users = User.query().where(User.c.is_premium == True)
active_users = User.query().where(User.c.last_login >= '2024-01-01')

premium_and_active = premium_users.intersect(active_users).all()

# Premium users who are NOT active
inactive_premium = premium_users.except_(active_users).all()
```

## Query Optimization

### Select Only Needed Columns

```python
# Bad - SELECT *
users = User.query().all()

# Good - SELECT specific columns
users = User.query().select(
    User.c.id,
    User.c.name,
    User.c.email
).all()
```

### Use EXPLAIN

```python
plan = User.query().where(
    (User.c.age >= 18) & (User.c.status == 'active')
).explain()

print(plan)
# Shows query execution plan for optimization
```

### Eager Loading

```python
# Bad - N+1 problem
for user in User.query().all():
    for post in user.posts():  # Each iteration queries database
        print(post.title)

# Good - Eager load
for user in User.query().with_('posts').all():
    for post in user.posts():  # Already loaded
        print(post.title)
```

## Debugging Queries

### Inspect SQL

```python
# Any query can show its SQL
query = User.query().where(
    (User.c.age >= 18) & (User.c.status == 'active')
).order_by(User.c.name).limit(10)

sql, params = query.to_sql()
print(f"SQL: {sql}")
print(f"Params: {params}")
# Output: SELECT id, name, ... FROM users 
#         WHERE (age >= ? AND status = ?) 
#         ORDER BY name LIMIT ?
#         Params: (18, 'active', 10)
```

### Check Backend Capabilities

```python
# Check if backend supports CTEs
if User.backend().dialect.supports_cte():
    # Use CTE query
    results = CTEQuery(...)
else:
    # Fallback to regular query
    results = User.query().where(...)
```

## Full Documentation

- **ActiveQuery:** `docs/en_US/querying/active_query.md`
- **CTE Query:** `docs/en_US/querying/cte_query.md`
- **Set Operations:** `docs/en_US/querying/set_operation_query.md`
- **Window Functions:** `docs/en_US/querying/window_functions.md`
