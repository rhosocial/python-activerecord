# Group By Operations

The GROUP BY clause is a fundamental component of aggregate queries that allows you to organize your data into groups before applying aggregate functions. rhosocial ActiveRecord provides a clean and intuitive API for working with GROUP BY operations.

## Basic Grouping

The `group_by()` method allows you to specify one or more columns to group your data by:

```python
# Group users by status and count them
user_counts = User.query()\
    .select('status')\
    .group_by('status')\
    .count('id', 'user_count')\
    .aggregate()

# Result: [{'status': 'active', 'user_count': 42}, {'status': 'inactive', 'user_count': 15}, ...]
```

When you use `group_by()`, you must also select the columns you're grouping by in your `select()` call to include them in the result.

## Multiple Column Grouping

You can group by multiple columns to create more detailed aggregations:

```python
# Group sales by year and month
monthly_sales = Sale.query()\
    .select('YEAR(date) as year', 'MONTH(date) as month')\
    .group_by('YEAR(date)', 'MONTH(date)')\
    .sum('amount', 'total_sales')\
    .aggregate()

# Group products by category and status
product_stats = Product.query()\
    .select('category', 'status')\
    .group_by('category', 'status')\
    .count('id', 'product_count')\
    .aggregate()
```

## Column Aliases in GROUP BY

It's important to note that GROUP BY should use the original column expressions, not aliases. rhosocial ActiveRecord will automatically strip aliases from GROUP BY columns and issue a warning:

```python
# This works but generates a warning
user_stats = User.query()\
    .select('status AS user_status')\
    .group_by('status AS user_status')  # Warning: alias will be stripped\
    .count('id', 'count')\
    .aggregate()

# Better approach
user_stats = User.query()\
    .select('status AS user_status')\
    .group_by('status')\
    .count('id', 'count')\
    .aggregate()
```

## Grouping with Table-Qualified Columns

When working with JOINs, it's important to qualify your columns with table names to avoid ambiguity:

```python
# Group orders by customer
customer_orders = Order.query()\
    .join('JOIN customers ON orders.customer_id = customers.id')\
    .select('customers.id', 'customers.name')\
    .group_by('customers.id', 'customers.name')\
    .count('orders.id', 'order_count')\
    .sum('orders.amount', 'total_amount')\
    .aggregate()
```

## Grouping with Expressions

You can group by SQL expressions, not just simple columns:

```python
# Group by date parts
monthly_stats = Event.query()\
    .select('EXTRACT(YEAR FROM date) as year', 'EXTRACT(MONTH FROM date) as month')\
    .group_by('EXTRACT(YEAR FROM date)', 'EXTRACT(MONTH FROM date)')\
    .count('id', 'event_count')\
    .aggregate()

# Group by calculated values
price_ranges = Product.query()\
    .select('FLOOR(price / 100) * 100 as price_range')\
    .group_by('FLOOR(price / 100) * 100')\
    .count('id', 'product_count')\
    .aggregate()
```

## Handling NULL Values in Grouping

In SQL, NULL values are grouped together when using GROUP BY. This behavior is preserved in rhosocial ActiveRecord:

```python
# Group users by optional fields
user_groups = User.query()\
    .select('department')\
    .group_by('department')\
    .count('id', 'user_count')\
    .aggregate()

# Result might include a group where department is None
```

If you want to handle NULL values differently, you can use COALESCE or IFNULL in your query:

```python
# Replace NULL departments with 'Unassigned'
user_groups = User.query()\
    .select('COALESCE(department, "Unassigned") as department')\
    .group_by('COALESCE(department, "Unassigned")')\
    .count('id', 'user_count')\
    .aggregate()
```

## Advanced Grouping Techniques

### Grouping with HAVING

Combine GROUP BY with HAVING to filter groups based on aggregate results:

```python
# Find departments with more than 10 employees
large_departments = Employee.query()\
    .select('department')\
    .group_by('department')\
    .count('id', 'employee_count')\
    .having('COUNT(id) > ?', (10,))\
    .aggregate()
```

### Grouping with ORDER BY

You can order the grouped results using ORDER BY:

```python
# Group by category and order by count descending
category_counts = Product.query()\
    .select('category')\
    .group_by('category')\
    .count('id', 'product_count')\
    .order_by('product_count DESC')\
    .aggregate()
```

### Grouping with LIMIT

You can limit the number of groups returned:

```python
# Get top 5 categories by product count
top_categories = Product.query()\
    .select('category')\
    .group_by('category')\
    .count('id', 'product_count')\
    .order_by('product_count DESC')\
    .limit(5)\
    .aggregate()
```

## Performance Considerations

- GROUP BY operations can be resource-intensive on large datasets
- Add indexes on columns used in GROUP BY clauses for better performance
- Filter data with WHERE before grouping to reduce the amount of data processed
- Consider using HAVING only for conditions that must be applied after grouping

## Database Compatibility

The basic GROUP BY functionality is supported by all database backends. However, some advanced grouping features may have different syntax or limitations depending on the database:

- **SQLite**: Supports basic GROUP BY operations but has limited support for complex expressions
- **MySQL/MariaDB**: Supports GROUP BY with extensions like WITH ROLLUP
- **PostgreSQL**: Offers the most comprehensive GROUP BY support, including CUBE and GROUPING SETS

rhosocial ActiveRecord abstracts these differences where possible, providing a consistent API across different database backends.