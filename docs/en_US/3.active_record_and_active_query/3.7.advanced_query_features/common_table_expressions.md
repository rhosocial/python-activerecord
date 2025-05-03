# Common Table Expressions (CTEs)

This section covers the Common Table Expressions (CTEs) feature in ActiveRecord, which allows you to write more readable and maintainable complex queries.

## Overview

Common Table Expressions (CTEs) are temporary named result sets that you can reference within a SELECT, INSERT, UPDATE, or DELETE statement. They are defined using the WITH clause in SQL and exist only for the duration of the query execution. CTEs make complex queries more readable by breaking them down into simpler, named components.

ActiveRecord provides comprehensive support for CTEs through the `CTEQueryMixin` class, which is included in the standard `ActiveQuery` implementation.

## Key Features

- Define CTEs using SQL strings or ActiveQuery instances
- Support for recursive CTEs for hierarchical data queries
- Support for materialization hints (when the database supports it)
- Support for multiple CTEs in a single query
- Chain method calls for building complex queries incrementally

## Basic Usage

### Defining a Simple CTE

```python
# Define a CTE that selects active users
query = User.query().with_cte(
    'active_users',
    "SELECT * FROM users WHERE status = 'active'"
).from_cte('active_users').all()
```

### Using an ActiveQuery Instance for CTE Definition

Using ActiveQuery instances for CTE definitions is recommended for security as it properly parameterizes values:

```python
# Define the subquery using ActiveQuery
subquery = User.query().where('status = ?', ('active',))

# Use the subquery in a CTE
query = User.query().with_cte(
    'active_users',
    subquery
).from_cte('active_users').order_by('name').all()
```

### Using CTEs with Column Aliases

```python
# Define a CTE with explicit column names
query = Order.query().with_cte(
    'order_summary',
    "SELECT order_number, total_amount FROM orders",
    columns=['order_no', 'amount']  # Rename columns in the CTE
).from_cte('order_summary')

# Select all columns from the CTE
query.select('order_summary.*')

# Since we're bypassing the model, use dict query for results
results = query.to_dict(direct_dict=True).all()
```

### Multiple CTEs in a Single Query

```python
# Define multiple CTEs
query = Order.query()

# First CTE: active orders
query.with_cte(
    'active_orders',
    "SELECT * FROM orders WHERE status IN ('pending', 'paid')"
)

# Second CTE: expensive orders
query.with_cte(
    'expensive_orders',
    "SELECT * FROM active_orders WHERE total_amount > 300.00"
)

# Use the second CTE
query.from_cte('expensive_orders')

results = query.all()
```

## Recursive CTEs

Recursive CTEs are particularly useful for querying hierarchical data, such as organizational charts, category trees, or bill of materials.

### Basic Recursive CTE

```python
# Define a recursive CTE to traverse a tree structure
recursive_sql = """
                SELECT id, name, parent_id, 1 as level \
                FROM nodes \
                WHERE id = 1
                UNION ALL
                SELECT n.id, n.name, n.parent_id, t.level + 1
                FROM nodes n
                         JOIN tree t ON n.parent_id = t.id \
                """

query = Node.query().with_recursive_cte("tree", recursive_sql)
query.from_cte("tree")
query.order_by("level, id")

results = query.to_dict(direct_dict=True).all()
```

### Recursive CTE with Depth Limit

```python
# Define a recursive CTE with max depth limit
recursive_sql = """
                SELECT id, name, parent_id, 1 as level \
                FROM nodes \
                WHERE id = 1
                UNION ALL
                SELECT n.id, n.name, n.parent_id, t.level + 1
                FROM nodes n
                         JOIN tree t ON n.parent_id = t.id
                WHERE t.level < 2 \
                """ #  -- Limit recursion to depth 2

query = Node.query().with_recursive_cte("tree", recursive_sql)
query.from_cte("tree")
query.order_by("level, id")

results = query.to_dict(direct_dict=True).all()
```

### Finding Paths in Hierarchical Data

```python
# Find path from root to a specific node
recursive_sql = """
                -- Anchor member: start with target node
                SELECT id, name, parent_id, CAST(id AS TEXT) as path
                FROM nodes
                WHERE id = 5

                UNION ALL

                -- Recursive member: add parent nodes
                SELECT n.id, n.name, n.parent_id, CAST(n.id AS TEXT) || ',' || t.path
                FROM nodes n
                         JOIN path_finder t ON n.id = t.parent_id \
                """

query = Node.query().with_recursive_cte("path_finder", recursive_sql)
query.from_cte("path_finder")
query.order_by("length(path) DESC")  # Longest path first (complete path)

results = query.to_dict(direct_dict=True).all()
```

## Database Support

ActiveRecord provides methods to check if your database supports various CTE features:

```python
# Check if database supports CTEs
if User.query().supports_cte():
    # Use CTEs
    pass

# Check if database supports recursive CTEs
if User.query().supports_recursive_cte():
    # Use recursive CTEs
    pass

# Check if database supports materialization hints
if User.query().supports_materialized_hint():
    # Use materialization hints
    pass

# Check if database supports multiple CTEs
if User.query().supports_multiple_ctes():
    # Use multiple CTEs
    pass
```

## Materialization Hints

Some databases support materialization hints for CTEs, which can affect how the database processes the CTE:

```python
# CTE with materialization hint
query = User.query().with_cte(
    'active_users',
    "SELECT * FROM users WHERE status = 'active'",
    materialized=True  # Force materialization
).from_cte('active_users').all()

# CTE with NOT MATERIALIZED hint
query = User.query().with_cte(
    'active_users',
    "SELECT * FROM users WHERE status = 'active'",
    materialized=False  # Prevent materialization
).from_cte('active_users').all()
```

## Best Practices

1. **Use ActiveQuery Instances**: When possible, use ActiveQuery instances instead of raw SQL strings to define CTEs for better security and maintainability.

2. **Check Database Support**: Always check if your database supports the CTE features you want to use.

3. **Use Meaningful Names**: Give your CTEs descriptive names that reflect their purpose.

4. **Consider Performance**: CTEs can improve query readability but may not always improve performance. Test and optimize as needed.

5. **Limit Recursion Depth**: For recursive CTEs, always include a condition to limit recursion depth to prevent infinite loops.

## Conclusion

Common Table Expressions provide a powerful way to structure complex queries in a more readable and maintainable format. ActiveRecord's CTE support makes it easy to leverage this SQL feature in your Python applications, especially for hierarchical data queries and complex multi-step operations.