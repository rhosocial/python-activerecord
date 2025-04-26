# Basic Aggregate Functions

rhosocial ActiveRecord provides a comprehensive set of basic aggregate functions that allow you to perform calculations across rows in your database. These functions are essential for data analysis and reporting.

## Available Aggregate Functions

The following basic aggregate functions are available in all database backends:

| Function | Description | Method |
|----------|-------------|--------|
| COUNT | Counts the number of rows or non-NULL values | `count()` |
| SUM | Calculates the sum of values in a column | `sum()` |
| AVG | Calculates the average of values in a column | `avg()` |
| MIN | Finds the minimum value in a column | `min()` |
| MAX | Finds the maximum value in a column | `max()` |

## Using Aggregate Functions

Aggregate functions can be used in two ways:

1. **Scalar mode**: Execute immediately and return a single value
2. **Aggregate query mode**: Add to a query with GROUP BY for more complex aggregations

### Scalar Mode

In scalar mode, the aggregate function executes immediately and returns a single value:

```python
# Count all users
total_users = User.query().count()

# Sum of all order amounts
total_amount = Order.query().sum('amount')

# Average product price
avg_price = Product.query().avg('price')

# Minimum and maximum prices
min_price = Product.query().min('price')
max_price = Product.query().max('price')
```

You can combine aggregate functions with WHERE conditions:

```python
# Count active users
active_count = User.query().where('status = ?', (1,)).count()

# Sum of completed order amounts
completed_total = Order.query()\
    .where('status = ?', ('completed',))\
    .sum('amount')
```

### Using DISTINCT

The `count()` method supports a `distinct` parameter to count only distinct values:

```python
# Count distinct categories
category_count = Product.query().count('category', distinct=True)
```

## Aggregate Query Mode

In aggregate query mode, you can combine multiple aggregate functions with GROUP BY clauses:

```python
# Group by department and calculate statistics
dept_stats = Employee.query()\
    .select('department')\
    .group_by('department')\
    .count('id', 'employee_count')\
    .sum('salary', 'total_salary')\
    .avg('salary', 'avg_salary')\
    .min('salary', 'min_salary')\
    .max('salary', 'max_salary')\
    .aggregate()

# Results will be a list of dictionaries:
# [
#   {'department': 'Engineering', 'employee_count': 42, 'total_salary': 4200000, 'avg_salary': 100000, ...},
#   {'department': 'Marketing', 'employee_count': 18, 'total_salary': 1440000, 'avg_salary': 80000, ...},
#   ...
# ]
```

In aggregate query mode, the query is not executed until you call the `aggregate()` method, which returns the results as a list of dictionaries.

## Aliasing Results

You can provide an alias for the aggregate result column:

```python
# With alias
user_stats = User.query()\
    .select('status')\
    .group_by('status')\
    .count('id', 'user_count')\
    .aggregate()

# Without alias (default column name will be the function name)
user_stats = User.query()\
    .select('status')\
    .group_by('status')\
    .count('id')\
    .aggregate()
```

## NULL Handling

Aggregate functions handle NULL values according to SQL standard behavior:

- COUNT(*) includes all rows
- COUNT(column) excludes NULL values in that column
- SUM, AVG, MIN, MAX ignore NULL values
- If all values are NULL, SUM and AVG return NULL, while COUNT returns 0

```python
# Count all rows including those with NULL values in the email column
total_users = User.query().count()

# Count only rows with non-NULL email values
users_with_email = User.query().count('email')
```

## Combining with Joins

Aggregate functions can be combined with JOINs for more complex queries:

```python
# Count orders per customer
customer_orders = Order.query()\
    .join('JOIN customers ON orders.customer_id = customers.id')\
    .select('customers.name')\
    .group_by('customers.name')\
    .count('orders.id', 'order_count')\
    .sum('orders.amount', 'total_spent')\
    .aggregate()
```

## Error Handling

Aggregate functions handle errors gracefully:

- If the query fails, appropriate exceptions will be raised
- For scalar queries, NULL results are converted to None in Python
- Type conversion is handled automatically based on the database column type

## Performance Considerations

- Aggregate functions are executed on the database server, not in Python
- For large datasets, consider adding appropriate indexes on columns used in GROUP BY clauses
- When possible, filter data with WHERE before aggregating to reduce the amount of data processed