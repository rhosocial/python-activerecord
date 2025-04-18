# Window Functions

Window functions are a powerful feature of SQL that allow you to perform calculations across a set of rows that are related to the current row, without collapsing the result into a single row like aggregate functions do. rhosocial ActiveRecord provides comprehensive support for window functions through its query API.

## Introduction to Window Functions

Window functions perform calculations across a "window" of rows defined by the OVER clause. They're particularly useful for analytical queries where you need to compare each row with related rows or compute running totals, moving averages, and rankings.

```python
# Basic window function example: Rank products by price within each category
ranked_products = Product.query()\
    .select('id', 'name', 'category', 'price')\
    .window(
        FunctionExpression('RANK'),
        partition_by=['category'],
        order_by=['price DESC'],
        alias='price_rank'
    )\
    .order_by('category', 'price_rank')\
    .all()
```

## Window Function Components

A window function in rhosocial ActiveRecord consists of several components:

1. **Base function**: The function to apply (e.g., RANK, SUM, AVG)
2. **PARTITION BY**: Divides rows into groups (optional)
3. **ORDER BY**: Determines the order of rows within each partition (optional)
4. **Frame specification**: Defines which rows to include in the window (optional)

## Supported Window Functions

rhosocial ActiveRecord supports various types of window functions:

### Ranking Functions

```python
# ROW_NUMBER: Assigns a unique sequential number to each row
Product.query()\
    .select('category', 'name', 'price')\
    .window(
        FunctionExpression('ROW_NUMBER'),
        partition_by=['category'],
        order_by=['price DESC'],
        alias='row_num'
    )\
    .all()

# RANK: Assigns the same rank to ties, with gaps
Product.query()\
    .select('category', 'name', 'price')\
    .window(
        FunctionExpression('RANK'),
        partition_by=['category'],
        order_by=['price DESC'],
        alias='price_rank'
    )\
    .all()

# DENSE_RANK: Assigns the same rank to ties, without gaps
Product.query()\
    .select('category', 'name', 'price')\
    .window(
        FunctionExpression('DENSE_RANK'),
        partition_by=['category'],
        order_by=['price DESC'],
        alias='dense_price_rank'
    )\
    .all()

# NTILE: Divides rows into a specified number of groups
Product.query()\
    .select('category', 'name', 'price')\
    .window(
        FunctionExpression('NTILE', '4'),  # Divide into quartiles
        partition_by=['category'],
        order_by=['price DESC'],
        alias='price_quartile'
    )\
    .all()
```

### Aggregate Window Functions

```python
# SUM: Running total of sales by date
Order.query()\
    .select('date', 'amount')\
    .window(
        FunctionExpression('SUM', 'amount'),
        order_by=['date'],
        alias='running_total'
    )\
    .order_by('date')\
    .all()

# AVG: Moving average of sales
Order.query()\
    .select('date', 'amount')\
    .window(
        FunctionExpression('AVG', 'amount'),
        order_by=['date'],
        frame_type='ROWS',
        frame_start='6 PRECEDING',
        frame_end='CURRENT ROW',
        alias='moving_avg_7days'
    )\
    .order_by('date')\
    .all()

# COUNT: Count of orders per customer with running total
Order.query()\
    .select('customer_id', 'date', 'amount')\
    .window(
        FunctionExpression('COUNT', '*'),
        partition_by=['customer_id'],
        order_by=['date'],
        alias='order_number'
    )\
    .window(
        FunctionExpression('SUM', 'amount'),
        partition_by=['customer_id'],
        order_by=['date'],
        alias='customer_running_total'
    )\
    .order_by('customer_id', 'date')\
    .all()
```

### Value Functions

```python
# FIRST_VALUE: First price in each category
Product.query()\
    .select('category', 'name', 'price')\
    .window(
        FunctionExpression('FIRST_VALUE', 'price'),
        partition_by=['category'],
        order_by=['price DESC'],
        alias='highest_price'
    )\
    .all()

# LAST_VALUE: Last price in each category
Product.query()\
    .select('category', 'name', 'price')\
    .window(
        FunctionExpression('LAST_VALUE', 'price'),
        partition_by=['category'],
        order_by=['price DESC'],
        frame_type='ROWS',
        frame_start='UNBOUNDED PRECEDING',
        frame_end='UNBOUNDED FOLLOWING',  # Important for LAST_VALUE
        alias='lowest_price'
    )\
    .all()

# LAG: Previous price in the ordered sequence
Product.query()\
    .select('category', 'name', 'price')\
    .window(
        FunctionExpression('LAG', 'price', '1'),  # Offset by 1 row
        partition_by=['category'],
        order_by=['price DESC'],
        alias='next_lower_price'
    )\
    .all()

# LEAD: Next price in the ordered sequence
Product.query()\
    .select('category', 'name', 'price')\
    .window(
        FunctionExpression('LEAD', 'price', '1'),  # Offset by 1 row
        partition_by=['category'],
        order_by=['price DESC'],
        alias='next_higher_price'
    )\
    .all()
```

## Window Frame Specifications

Window frames define which rows to include in the window relative to the current row:

```python
# Default frame (RANGE UNBOUNDED PRECEDING AND CURRENT ROW)
Order.query()\
    .select('date', 'amount')\
    .window(
        FunctionExpression('SUM', 'amount'),
        order_by=['date'],
        alias='running_total'
    )\
    .all()

# Rows-based frame: Last 7 rows including current row
Order.query()\
    .select('date', 'amount')\
    .window(
        FunctionExpression('AVG', 'amount'),
        order_by=['date'],
        frame_type='ROWS',
        frame_start='6 PRECEDING',
        frame_end='CURRENT ROW',
        alias='moving_avg_7days'
    )\
    .all()

# Range-based frame: All rows with the same value
Employee.query()\
    .select('department', 'salary')\
    .window(
        FunctionExpression('AVG', 'salary'),
        partition_by=['department'],
        order_by=['salary'],
        frame_type='RANGE',
        frame_start='CURRENT ROW',
        frame_end='CURRENT ROW',
        alias='avg_for_same_salary'
    )\
    .all()

# Unbounded frame: All rows in the partition
Product.query()\
    .select('category', 'name', 'price')\
    .window(
        FunctionExpression('AVG', 'price'),
        partition_by=['category'],
        frame_type='ROWS',
        frame_start='UNBOUNDED PRECEDING',
        frame_end='UNBOUNDED FOLLOWING',
        alias='category_avg_price'
    )\
    .all()
```

## Named Windows

You can define named windows for reuse in multiple window functions:

```python
# Define a named window
query = Product.query()\
    .select('category', 'name', 'price')\
    .define_window(
        'category_window',
        partition_by=['category'],
        order_by=['price DESC']
    )

# Use the named window in multiple functions
results = query\
    .window(
        FunctionExpression('ROW_NUMBER'),
        window_name='category_window',
        alias='row_num'
    )\
    .window(
        FunctionExpression('RANK'),
        window_name='category_window',
        alias='price_rank'
    )\
    .window(
        FunctionExpression('PERCENT_RANK'),
        window_name='category_window',
        alias='percent_rank'
    )\
    .all()
```

## Practical Examples

### Percentile Calculations

```python
# Calculate percentile rank of each product's price within its category
product_percentiles = Product.query()\
    .select('category', 'name', 'price')\
    .window(
        FunctionExpression('PERCENT_RANK'),
        partition_by=['category'],
        order_by=['price'],
        alias='price_percentile'
    )\
    .order_by('category', 'price_percentile')\
    .all()
```

### Time Series Analysis

```python
# Calculate month-over-month growth rate
monthly_sales = Order.query()\
    .select(
        'EXTRACT(YEAR FROM date) as year',
        'EXTRACT(MONTH FROM date) as month',
        'SUM(amount) as monthly_total'
    )\
    .group_by('EXTRACT(YEAR FROM date)', 'EXTRACT(MONTH FROM date)')\
    .order_by('year', 'month')\
    .window(
        FunctionExpression('LAG', 'monthly_total', '1'),
        order_by=['year', 'month'],
        alias='previous_month'
    )\
    .select('(monthly_total - previous_month) / previous_month * 100 as growth_rate')\
    .aggregate()
```

### Cumulative Distribution

```python
# Calculate cumulative distribution of salaries
salary_distribution = Employee.query()\
    .select('department', 'salary')\
    .window(
        FunctionExpression('CUME_DIST'),
        partition_by=['department'],
        order_by=['salary'],
        alias='salary_percentile'
    )\
    .order_by('department', 'salary')\
    .all()
```

## Database Compatibility

Window function support varies by database:

- **PostgreSQL**: Full support for all window functions and frame specifications
- **MySQL**: Basic support from version 8.0+
- **MariaDB**: Basic support from version 10.2+
- **SQLite**: Basic support from version 3.25+

rhosocial ActiveRecord checks database compatibility at runtime and raises appropriate exceptions when unsupported features are used:

```python
# This will raise WindowFunctionNotSupportedError on older database versions
try:
    results = Product.query()\
        .select('category', 'name', 'price')\
        .window(
            FunctionExpression('RANK'),
            partition_by=['category'],
            order_by=['price DESC'],
            alias='price_rank'
        )\
        .all()
except WindowFunctionNotSupportedError as e:
    print(f"Window functions not supported: {e}")
    # Fallback to non-window implementation
```

## Performance Considerations

- Window functions can be resource-intensive, especially with large datasets
- Use appropriate indexes on columns used in PARTITION BY and ORDER BY clauses
- Limit the window frame size when possible (e.g., use ROWS BETWEEN 10 PRECEDING AND CURRENT ROW instead of UNBOUNDED PRECEDING)
- Consider materializing intermediate results for complex multi-window queries
- Test window function queries with EXPLAIN to understand their execution plan