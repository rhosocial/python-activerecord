# Raw SQL Integration

This document explains how to integrate raw SQL queries with ActiveRecord when you need more control or specific database features.

## Introduction

While ActiveRecord's query builder provides a comprehensive interface for most database operations, there are scenarios where you might need to use raw SQL:

- Complex queries that are difficult to express with the query builder
- Database-specific features not directly supported by ActiveRecord
- Performance optimization for critical queries
- Legacy SQL that needs to be integrated with your ActiveRecord models

ActiveRecord provides several ways to incorporate raw SQL into your application while still benefiting from the ORM's features.

## Using Raw SQL in Where Conditions

The simplest way to use raw SQL is within standard query methods:

```python
from rhosocial.activerecord import ActiveRecord

class Product(ActiveRecord):
    __table__ = 'products'

# Using raw SQL in a WHERE clause
products = Product.query().where('price > 100 AND category_id IN (1, 2, 3)').all()

# Using raw SQL with parameters for safety
min_price = 100
categories = [1, 2, 3]
products = Product.query().where(
    'price > ? AND category_id IN (?, ?, ?)', 
    min_price, *categories
).all()
```

## Raw SQL in Joins

You can use raw SQL in join clauses for more complex join conditions:

```python
# Complex join with raw SQL
results = Product.query()\
    .join('JOIN categories ON products.category_id = categories.id')\
    .join('LEFT JOIN inventory ON products.id = inventory.product_id')\
    .where('categories.active = ? AND inventory.stock > ?', True, 0)\
    .all()
```

## Executing Raw SQL Queries

For complete control, you can execute raw SQL queries directly:

```python
# Execute a raw SQL query
sql = """
    SELECT p.*, c.name as category_name 
    FROM products p
    JOIN categories c ON p.category_id = c.id
    WHERE p.price > ? AND c.active = ?
    ORDER BY p.created_at DESC
    LIMIT 10
"""

results = Product.query().execute_raw(sql, 100, True)
```

The `execute_raw` method executes the SQL and returns the results as model instances when possible.

## Raw SQL for Specific Database Features

Raw SQL is particularly useful for database-specific features:

```python
# PostgreSQL-specific full-text search
sql = """
    SELECT * FROM products
    WHERE to_tsvector('english', name || ' ' || description) @@ to_tsquery('english', ?)
    ORDER BY ts_rank(to_tsvector('english', name || ' ' || description), to_tsquery('english', ?)) DESC
"""

search_term = 'wireless headphones'
results = Product.query().execute_raw(sql, search_term, search_term)
```

## Combining Raw SQL with Query Builder

You can combine raw SQL with the query builder for maximum flexibility:

```python
# Start with the query builder
query = Product.query()
    .select('products.*', 'categories.name AS category_name')
    .join('JOIN categories ON products.category_id = categories.id')

# Add raw SQL for complex conditions
if complex_search_needed:
    query = query.where('EXISTS (SELECT 1 FROM product_tags pt JOIN tags t ON pt.tag_id = t.id WHERE pt.product_id = products.id AND t.name IN (?, ?))', 'featured', 'sale')

# Continue with the query builder
results = query.order_by('products.created_at DESC').limit(20).all()
```

## Using Raw SQL for Subqueries

Raw SQL is useful for complex subqueries:

```python
# Find products that have at least 3 reviews with an average rating above 4
sql = """
    SELECT p.* FROM products p
    WHERE (
        SELECT COUNT(*) FROM reviews r 
        WHERE r.product_id = p.id
    ) >= 3
    AND (
        SELECT AVG(rating) FROM reviews r 
        WHERE r.product_id = p.id
    ) > 4
"""

highly_rated_products = Product.query().execute_raw(sql)
```

## Best Practices

1. **Use Parameters**: Always use parameterized queries with placeholders (`?`) instead of string concatenation to prevent SQL injection.

2. **Isolate Raw SQL**: Keep raw SQL in dedicated methods or classes to improve maintainability.

3. **Document Complex Queries**: Add comments explaining the purpose and logic of complex raw SQL queries.

4. **Consider Query Reusability**: For frequently used raw SQL, create helper methods or custom query classes.

5. **Test Thoroughly**: Raw SQL bypasses some of ActiveRecord's safeguards, so test it carefully across different database systems.

6. **Monitor Performance**: Raw SQL can be more efficient, but it can also introduce performance issues if not carefully crafted.

## Security Considerations

When using raw SQL, security becomes your responsibility:

```python
# UNSAFE - vulnerable to SQL injection
user_input = request.args.get('sort_column')
unsafe_query = f"SELECT * FROM products ORDER BY {user_input}"  # NEVER DO THIS

# SAFE - use a whitelist approach
allowed_columns = {'name', 'price', 'created_at'}
user_input = request.args.get('sort_column')

if user_input in allowed_columns:
    # Safe because we validated against a whitelist
    products = Product.query().order_by(user_input).all()
else:
    # Default safe ordering
    products = Product.query().order_by('name').all()
```

## Conclusion

Raw SQL integration provides an escape hatch when ActiveRecord's query builder isn't sufficient for your needs. By combining the power of raw SQL with ActiveRecord's ORM features, you can build sophisticated database interactions while still maintaining the benefits of working with model objects.