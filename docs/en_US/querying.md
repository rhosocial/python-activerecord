# Query Building

## Overview

RhoSocial ActiveRecord provides a fluent query interface that allows you to construct SQL queries in a type-safe and intuitive way.

## Basic Queries

### Simple Selects

```python
from rhosocial.activerecord import ActiveRecord

class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    name: str
    email: str
    status: str
    age: int

# Find all users
users = User.query().all()

# Find one user
user = User.query().one()

# Find by primary key
user = User.find_one(1)
user = User.find_one_or_fail(1)  # Raises RecordNotFound if not found

# Find by conditions
users = User.find_all({'status': 'active'})
user = User.find_one({'email': 'john@example.com'})
```

### WHERE Conditions

```python
# Simple equality
users = User.query()
    .where('status = ?', ('active',))
    .all()

# Multiple conditions
users = User.query()
    .where('age > ?', (18,))
    .where('status = ?', ('active',))
    .all()

# IN clause
users = User.query()
    .in_list('status', ['active', 'pending'])
    .all()

# NOT IN clause
users = User.query()
    .not_in('status', ['deleted', 'banned'])
    .all()

# BETWEEN
users = User.query()
    .between('age', 18, 30)
    .all()

# NULL checks
users = User.query()
    .is_null('deleted_at')
    .all()

users = User.query()
    .is_not_null('email')
    .all()

# LIKE patterns
users = User.query()
    .like('name', 'John%')
    .all()

users = User.query()
    .not_like('email', '%@spam.com')
    .all()
```

### Complex Conditions

```python
# OR conditions
users = User.query()
    .where('status = ?', ('active',))
    .or_where('status = ?', ('pending',))
    .all()

# Grouped conditions
users = User.query()
    .where('status = ?', ('active',))
    .start_or_group()
        .where('age > ?', (18,))
        .or_where('has_parental_consent = ?', (True,))
    .end_or_group()
    .all()
```

### Ordering and Limiting

```python
# Order by single column
users = User.query()
    .order_by('created_at DESC')
    .all()

# Order by multiple columns
users = User.query()
    .order_by('status ASC', 'created_at DESC')
    .all()

# Limit results
users = User.query()
    .limit(10)
    .all()

# Offset for pagination
users = User.query()
    .limit(10)
    .offset(20)  # Get page 3
    .all()
```

## Advanced Queries

### Selecting Specific Columns

```python
# Select specific columns
users = User.query()
    .select('id', 'name', 'email')
    .all()

# Select with aliases
users = User.query()
    .select('id', 'CONCAT(first_name, " ", last_name) as full_name')
    .all()
```

### Aggregations

```python
# Count
total = User.query().count()

# Filtered count
active_count = User.query()
    .where('status = ?', ('active',))
    .count()

# Sum
total_balance = Account.query()
    .sum('balance')

# Average
avg_age = User.query()
    .where('status = ?', ('active',))
    .avg('age')

# Min/Max
newest = User.query()
    .max('created_at')
oldest = User.query()
    .min('created_at')
```

### Group By and Having

```python
# Group by with count
status_counts = User.query()
    .select('status', 'COUNT(*) as count')
    .group_by('status')
    .all()

# Having clause
popular_categories = Category.query()
    .select('name', 'COUNT(*) as product_count')
    .group_by('name')
    .having('COUNT(*) > ?', (10,))
    .all()
```

## Result Handling

### Checking Existence

```python
exists = User.query()
    .where('email = ?', ('test@example.com',))
    .exists()
```

### Converting to Dictionaries

```python
# Get results as dictionaries
users_dict = User.query()
    .to_dict()
    .all()

# Include specific fields
users_dict = User.query()
    .to_dict(include={'id', 'name', 'email'})
    .all()

# Exclude specific fields
users_dict = User.query()
    .to_dict(exclude={'password_hash', 'secret_key'})
    .all()
```

### Error Handling

```python
from rhosocial.activerecord.backend.errors import (
    DatabaseError,
    RecordNotFound,
    QueryError
)

try:
    user = User.find_one_or_fail(999)
except RecordNotFound:
    print("User not found")

try:
    users = User.query()
        .where('invalid_column = ?', (1,))
        .all()
except QueryError as e:
    print(f"Query error: {e}")
except DatabaseError as e:
    print(f"Database error: {e}")
```

## Performance Optimization

### Optimizing Selects

```python
# Select only needed columns
users = User.query()
    .select('id', 'name')  # Only select required fields
    .where('status = ?', ('active',))
    .all()

# Use exists() for checking existence
has_admin = User.query()
    .where('role = ?', ('admin',))
    .exists()
```

### Using Indexes

Ensure your queries utilize database indexes:

```python
# Good - uses index on email
user = User.query()
    .where('email = ?', ('test@example.com',))
    .one()

# Less efficient - can't use index
users = User.query()
    .where('LOWER(email) = ?', ('test@example.com',))
    .all()
```

## Query Debugging

### Examining SQL

```python
# Get generated SQL and parameters
sql, params = User.query()
    .where('status = ?', ('active',))
    .to_sql()

print(f"SQL: {sql}")
print(f"Parameters: {params}")

# Get query execution plan
plan = User.query()
    .where('status = ?', ('active',))
    .explain()
print(plan)
```

## Best Practices

1. **Use Parameter Binding**
   - Always use parameter binding (`?`) for values
   - Never concatenate values into SQL strings

2. **Select Specific Columns**
   - Only select needed columns
   - Use `to_dict()` with `include` for specific fields

3. **Optimize Performance**
   - Use appropriate indexes
   - Limit result sets when possible
   - Use `exists()` for existence checks

4. **Handle Errors**
   - Always handle potential exceptions
   - Use appropriate error types for different scenarios

5. **Use Transactions**
   - Wrap related queries in transactions
   - See [Transactions](transactions.md) for details

## Next Steps

- Learn about [Relationships](relationships.md)
- Understand [Transactions](transactions.md)
- Explore [Caching](caching.md)
- Study [Performance Optimization](performance.md)