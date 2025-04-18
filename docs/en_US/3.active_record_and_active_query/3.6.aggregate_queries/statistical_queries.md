# Statistical Queries

rhosocial ActiveRecord provides capabilities for performing statistical analysis directly in your database queries. This document covers how to use aggregate functions and expressions to perform various statistical calculations.

## Basic Statistical Functions

Most databases support a set of basic statistical functions that can be used in aggregate queries:

```python
# Basic statistics for product prices
product_stats = Product.query()\
    .select(
        'COUNT(price) as count',
        'AVG(price) as mean',
        'MIN(price) as minimum',
        'MAX(price) as maximum',
        'SUM(price) as sum',
        'MAX(price) - MIN(price) as range'
    )\
    .aggregate()

# Statistics by category
category_stats = Product.query()\
    .select('category')\
    .group_by('category')\
    .select(
        'COUNT(price) as count',
        'AVG(price) as mean',
        'MIN(price) as minimum',
        'MAX(price) as maximum',
        'SUM(price) as sum',
        'MAX(price) - MIN(price) as range'
    )\
    .aggregate()
```

## Variance and Standard Deviation

Many databases support variance and standard deviation calculations:

```python
# Calculate variance and standard deviation
from rhosocial.activerecord.query.expression import FunctionExpression

product_stats = Product.query()\
    .select('category')\
    .group_by('category')\
    .select_expr(FunctionExpression('STDDEV', 'price', alias='std_dev'))\
    .select_expr(FunctionExpression('VARIANCE', 'price', alias='variance'))\
    .aggregate()
```

Database-specific function names may vary:

- PostgreSQL: `STDDEV`, `STDDEV_POP`, `STDDEV_SAMP`, `VAR_POP`, `VAR_SAMP`
- MySQL/MariaDB: `STD`, `STDDEV`, `STDDEV_POP`, `STDDEV_SAMP`, `VARIANCE`, `VAR_POP`, `VAR_SAMP`
- SQLite: Limited built-in support, but can be calculated using expressions

## Percentiles and Distributions

For databases that support window functions, you can calculate percentiles and distributions:

```python
# Calculate median (50th percentile) using window functions
median_price = Product.query()\
    .select('category')\
    .group_by('category')\
    .window(
        FunctionExpression('PERCENTILE_CONT', '0.5'),
        partition_by=['category'],
        order_by=['price'],
        alias='median_price'
    )\
    .aggregate()

# Calculate various percentiles
percentiles = Product.query()\
    .select('category')\
    .group_by('category')\
    .window(
        FunctionExpression('PERCENTILE_CONT', '0.25'),
        partition_by=['category'],
        order_by=['price'],
        alias='percentile_25'
    )\
    .window(
        FunctionExpression('PERCENTILE_CONT', '0.5'),
        partition_by=['category'],
        order_by=['price'],
        alias='percentile_50'
    )\
    .window(
        FunctionExpression('PERCENTILE_CONT', '0.75'),
        partition_by=['category'],
        order_by=['price'],
        alias='percentile_75'
    )\
    .window(
        FunctionExpression('PERCENTILE_CONT', '0.9'),
        partition_by=['category'],
        order_by=['price'],
        alias='percentile_90'
    )\
    .aggregate()
```

For databases without direct percentile functions, you can approximate using window functions and row numbering:

```python
# Approximate median using ROW_NUMBER
from rhosocial.activerecord.query.expression import FunctionExpression

# First, get the count of products in each category
category_counts = Product.query()\
    .select('category', 'COUNT(*) as count')\
    .group_by('category')\
    .aggregate()

# Then, for each category, find the middle row
for category_data in category_counts:
    category = category_data['category']
    count = category_data['count']
    middle_position = (count + 1) // 2
    
    median = Product.query()\
        .where('category = ?', (category,))\
        .select('price')\
        .window(
            FunctionExpression('ROW_NUMBER'),
            order_by=['price'],
            alias='row_num'
        )\
        .having(f'row_num = {middle_position}')\
        .aggregate()
```

## Correlation and Regression

Some databases support correlation and regression analysis:

```python
# Calculate correlation between price and rating
from rhosocial.activerecord.query.expression import FunctionExpression

correlation = Product.query()\
    .select_expr(FunctionExpression('CORR', 'price', 'rating', alias='price_rating_correlation'))\
    .aggregate()

# Linear regression
regression = Product.query()\
    .select(
        'REGR_SLOPE(sales, advertising_spend) as slope',
        'REGR_INTERCEPT(sales, advertising_spend) as intercept',
        'REGR_R2(sales, advertising_spend) as r_squared'
    )\
    .aggregate()
```

These functions are primarily available in PostgreSQL and some versions of MySQL/MariaDB.

## Custom Statistical Calculations

For more complex statistical calculations or when working with databases that don't support certain functions, you can use expressions:

```python
# Calculate coefficient of variation (CV = standard deviation / mean)
from rhosocial.activerecord.query.expression import ArithmeticExpression, FunctionExpression

cv = Product.query()\
    .select('category')\
    .group_by('category')\
    .select_expr(
        ArithmeticExpression(
            FunctionExpression('STDDEV', 'price'),
            '/',
            FunctionExpression('AVG', 'price'),
            'coefficient_of_variation'
        )
    )\
    .aggregate()

# Z-scores for prices within each category
z_scores = Product.query()\
    .select('id', 'name', 'category', 'price')\
    .window(
        FunctionExpression('AVG', 'price'),
        partition_by=['category'],
        alias='category_avg'
    )\
    .window(
        FunctionExpression('STDDEV', 'price'),
        partition_by=['category'],
        alias='category_stddev'
    )\
    .select('(price - category_avg) / category_stddev as z_score')\
    .all()
```

## Frequency Distributions

You can create frequency distributions using GROUP BY and COUNT:

```python
# Simple frequency distribution
rating_distribution = Product.query()\
    .select('rating', 'COUNT(*) as count')\
    .group_by('rating')\
    .order_by('rating')\
    .aggregate()

# Binned frequency distribution for continuous data
price_distribution = Product.query()\
    .select('FLOOR(price / 100) * 100 as price_bin', 'COUNT(*) as count')\
    .group_by('FLOOR(price / 100) * 100')\
    .order_by('price_bin')\
    .aggregate()
```

## Moving Averages and Trends

You can calculate moving averages and trends using window functions:

```python
# 7-day moving average of sales
moving_avg = Order.query()\
    .select('date', 'amount')\
    .window(
        FunctionExpression('AVG', 'amount'),
        order_by=['date'],
        frame_type='ROWS',
        frame_start='6 PRECEDING',
        frame_end='CURRENT ROW',
        alias='moving_avg_7day'
    )\
    .order_by('date')\
    .all()

# Exponential moving average (EMA) approximation
# Note: True EMA is typically calculated in application code
ema = Order.query()\
    .select('date', 'amount')\
    .order_by('date')\
    .all()

# Calculate EMA in Python (alpha = 0.2 for example)
alpha = 0.2
results = []
ema_value = ema[0]['amount'] if ema else 0

for row in ema:
    ema_value = alpha * row['amount'] + (1 - alpha) * ema_value
    results.append({
        'date': row['date'],
        'amount': row['amount'],
        'ema': ema_value
    })
```

## Seasonal Analysis

You can analyze seasonal patterns using GROUP BY with date parts:

```python
# Monthly sales analysis
monthly_sales = Order.query()\
    .select(
        'EXTRACT(YEAR FROM date) as year',
        'EXTRACT(MONTH FROM date) as month',
        'SUM(amount) as total_sales',
        'COUNT(*) as order_count',
        'AVG(amount) as avg_order_value'
    )\
    .group_by('EXTRACT(YEAR FROM date)', 'EXTRACT(MONTH FROM date)')\
    .order_by('year', 'month')\
    .aggregate()

# Day-of-week analysis
dow_analysis = Order.query()\
    .select(
        'EXTRACT(DOW FROM date) as day_of_week',
        'AVG(amount) as avg_sales',
        'COUNT(*) as order_count'
    )\
    .group_by('EXTRACT(DOW FROM date)')\
    .order_by('day_of_week')\
    .aggregate()
```

## Database Compatibility

Statistical function support varies by database:

- **PostgreSQL**: Comprehensive support for statistical functions
- **MySQL/MariaDB**: Good support for basic statistical functions
- **SQLite**: Limited built-in statistical functions

rhosocial ActiveRecord provides a consistent API where possible, but some advanced statistical functions may require database-specific approaches or post-processing in Python.

## Performance Considerations

- Statistical calculations can be resource-intensive on large datasets
- Consider using appropriate indexes on columns used in calculations
- For very complex statistical analysis, consider using specialized tools or libraries
- When possible, filter data before performing statistical calculations
- For time-series data, consider pre-aggregating data at appropriate intervals