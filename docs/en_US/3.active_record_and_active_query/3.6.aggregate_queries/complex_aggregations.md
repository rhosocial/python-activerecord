# Complex Aggregations

rhosocial ActiveRecord provides powerful capabilities for building complex aggregate queries that go beyond basic grouping and simple aggregate functions. This document explores advanced aggregation techniques that allow you to solve sophisticated data analysis problems.

## Combining Multiple Aggregate Functions

One of the most powerful features of aggregate queries is the ability to combine multiple aggregate functions in a single query:

```python
# Comprehensive product statistics by category
category_stats = Product.query()\
    .select('category')\
    .group_by('category')\
    .count('id', 'product_count')\
    .sum('stock', 'total_stock')\
    .avg('price', 'avg_price')\
    .min('price', 'min_price')\
    .max('price', 'max_price')\
    .aggregate()

# Result:
# [
#   {
#     'category': 'Electronics',
#     'product_count': 42,
#     'total_stock': 1250,
#     'avg_price': 299.99,
#     'min_price': 19.99,
#     'max_price': 1999.99
#   },
#   ...
# ]
```

This approach is much more efficient than running multiple separate queries, as it requires only a single database roundtrip.

## Conditional Aggregations

You can use CASE expressions within aggregate functions to perform conditional aggregations:

```python
# Count orders by status
order_stats = Order.query()\
    .select(
        'COUNT(CASE WHEN status = "pending" THEN 1 END) as pending_count',
        'COUNT(CASE WHEN status = "processing" THEN 1 END) as processing_count',
        'COUNT(CASE WHEN status = "shipped" THEN 1 END) as shipped_count',
        'COUNT(CASE WHEN status = "delivered" THEN 1 END) as delivered_count',
        'COUNT(CASE WHEN status = "cancelled" THEN 1 END) as cancelled_count'
    )\
    .aggregate()

# Calculate revenue by product category
revenue_by_category = Order.query()\
    .join('JOIN order_items ON orders.id = order_items.order_id')\
    .join('JOIN products ON order_items.product_id = products.id')\
    .select('products.category')\
    .group_by('products.category')\
    .select(
        'SUM(CASE WHEN orders.status = "completed" THEN order_items.price * order_items.quantity ELSE 0 END) as completed_revenue',
        'SUM(CASE WHEN orders.status = "cancelled" THEN order_items.price * order_items.quantity ELSE 0 END) as cancelled_revenue'
    )\
    .aggregate()
```

## Subqueries in Aggregations

You can use subqueries to create more complex aggregations:

```python
# Find products with above-average price in their category
from rhosocial.activerecord.query.expression import SubqueryExpression

# First, create a subquery that calculates average price by category
avg_price_subquery = Product.query()\
    .select('category', 'AVG(price) as avg_category_price')\
    .group_by('category')

# Then use it in the main query
premium_products = Product.query()\
    .join(f'JOIN ({avg_price_subquery.to_sql()[0]}) as category_avg ON products.category = category_avg.category')\
    .where('products.price > category_avg.avg_category_price')\
    .select('products.*', 'category_avg.avg_category_price')\
    .all()
```

Alternatively, you can use the SubqueryExpression class for more complex scenarios:

```python
# Find departments with above-average employee count
avg_dept_size = Employee.query().count() / Department.query().count()

large_departments = Department.query()\
    .select('departments.name')\
    .select_expr(SubqueryExpression(
        Employee.query()\
            .select('COUNT(*)')\
            .where('department_id = departments.id'),
        'employee_count'
    ))\
    .having(f'employee_count > {avg_dept_size}')\
    .order_by('employee_count DESC')\
    .aggregate()
```

## Aggregate Functions with Expressions

You can use expressions within aggregate functions for more complex calculations:

```python
# Calculate weighted average
weighted_avg = Order.query()\
    .select('SUM(price * quantity) / SUM(quantity) as weighted_avg_price')\
    .aggregate()

# Calculate percentage of total
product_share = Product.query()\
    .select('category')\
    .group_by('category')\
    .select_expr(ArithmeticExpression(
        FunctionExpression('SUM', 'price * stock'),
        '/',
        SubqueryExpression(Product.query().select('SUM(price * stock)')),
        'revenue_share'
    ))\
    .select('SUM(price * stock) * 100.0 / (SELECT SUM(price * stock) FROM products) as percentage')\
    .aggregate()
```

## Multi-Level Aggregations

You can create multi-level aggregations by combining subqueries:

```python
# First level: Calculate monthly sales by product
monthly_product_sales = Order.query()\
    .join('JOIN order_items ON orders.id = order_items.order_id')\
    .select(
        'EXTRACT(YEAR FROM orders.created_at) as year',
        'EXTRACT(MONTH FROM orders.created_at) as month',
        'order_items.product_id',
        'SUM(order_items.quantity) as units_sold',
        'SUM(order_items.price * order_items.quantity) as revenue'
    )\
    .where('orders.status = ?', ('completed',))\
    .group_by(
        'EXTRACT(YEAR FROM orders.created_at)',
        'EXTRACT(MONTH FROM orders.created_at)',
        'order_items.product_id'
    )

# Second level: Find top-selling product each month
top_products_by_month = f"""
    SELECT year, month, product_id, units_sold, revenue
    FROM ({monthly_product_sales.to_sql()[0]}) as monthly_sales
    WHERE (year, month, units_sold) IN (
        SELECT year, month, MAX(units_sold)
        FROM ({monthly_product_sales.to_sql()[0]}) as max_sales
        GROUP BY year, month
    )
    ORDER BY year, month
"""

# Execute the raw SQL query
top_products = Product.query().execute_raw(top_products_by_month)
```

## Pivot Tables and Cross-Tabulation

You can create pivot tables using conditional aggregations:

```python
# Create a pivot table of sales by product category and month
pivot_table = Order.query()\
    .join('JOIN order_items ON orders.id = order_items.order_id')\
    .join('JOIN products ON order_items.product_id = products.id')\
    .select('products.category')\
    .group_by('products.category')\
    .select(
        'SUM(CASE WHEN EXTRACT(MONTH FROM orders.created_at) = 1 THEN order_items.price * order_items.quantity ELSE 0 END) as jan_sales',
        'SUM(CASE WHEN EXTRACT(MONTH FROM orders.created_at) = 2 THEN order_items.price * order_items.quantity ELSE 0 END) as feb_sales',
        'SUM(CASE WHEN EXTRACT(MONTH FROM orders.created_at) = 3 THEN order_items.price * order_items.quantity ELSE 0 END) as mar_sales',
        # ... and so on for other months
    )\
    .aggregate()
```

## Hierarchical Aggregations

For databases that support it, you can use ROLLUP for hierarchical aggregations:

```python
# Sales by year, month, and day with subtotals
sales_report = Order.query()\
    .select(
        'EXTRACT(YEAR FROM created_at) as year',
        'EXTRACT(MONTH FROM created_at) as month',
        'EXTRACT(DAY FROM created_at) as day',
        'SUM(amount) as total_sales'
    )\
    .rollup(
        'EXTRACT(YEAR FROM created_at)',
        'EXTRACT(MONTH FROM created_at)',
        'EXTRACT(DAY FROM created_at)'
    )\
    .aggregate()

# This will include rows for:
# - Each specific day
# - Monthly subtotals (day is NULL)
# - Yearly subtotals (month and day are NULL)
# - Grand total (year, month, and day are all NULL)
```

## Performance Considerations

- Complex aggregations can be resource-intensive, especially on large datasets
- Use appropriate indexes on columns used in JOIN, WHERE, and GROUP BY clauses
- Consider materializing intermediate results for multi-step aggregations
- Test complex queries with EXPLAIN to understand their execution plan
- For very complex aggregations, consider using database-specific features or stored procedures

## Database Compatibility

Complex aggregation support varies by database:

- **PostgreSQL** offers the most comprehensive support for complex aggregations
- **MySQL/MariaDB** support most features but may have limitations with certain expressions
- **SQLite** has more limited support for advanced features

rhosocial ActiveRecord will raise appropriate exceptions when unsupported features are used with a particular database backend.