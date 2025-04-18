# Report Generation with rhosocial ActiveRecord

Report generation is a common requirement in data analysis applications. rhosocial ActiveRecord provides powerful features that make it easy to generate reports from your database data. This document explores various approaches to report generation using ActiveRecord.

## Basic Report Generation

### Aggregating Data for Reports

ActiveRecord's aggregate query capabilities are particularly useful for report generation. Here's a simple example of generating a sales summary report:

```python
# Generate a monthly sales report
monthly_sales = Order.query()\
    .select('EXTRACT(MONTH FROM order_date) as month')\
    .select('EXTRACT(YEAR FROM order_date) as year')\
    .sum('total_amount', 'monthly_total')\
    .count('id', 'order_count')\
    .group_by('year', 'month')\
    .order_by('year', 'month')\
    .aggregate()

# The result is a list of dictionaries, each representing a row in the report
for row in monthly_sales:
    print(f"Year: {row['year']}, Month: {row['month']}, "
          f"Total: ${row['monthly_total']}, Orders: {row['order_count']}")
```

### Using Window Functions for Comparative Analysis

Window functions are powerful tools for comparative analysis in reports:

```python
# Sales report with month-over-month growth percentage
sales_growth = Order.query()\
    .select('EXTRACT(MONTH FROM order_date) as month')\
    .select('EXTRACT(YEAR FROM order_date) as year')\
    .sum('total_amount', 'monthly_total')\
    .window_function(
        'LAG(SUM(total_amount), 1) OVER (ORDER BY EXTRACT(YEAR FROM order_date), EXTRACT(MONTH FROM order_date))',
        'previous_month_total'
    )\
    .window_function(
        'CASE WHEN LAG(SUM(total_amount), 1) OVER (ORDER BY EXTRACT(YEAR FROM order_date), EXTRACT(MONTH FROM order_date)) > 0 '
        'THEN (SUM(total_amount) - LAG(SUM(total_amount), 1) OVER (ORDER BY EXTRACT(YEAR FROM order_date), '
        'EXTRACT(MONTH FROM order_date))) / LAG(SUM(total_amount), 1) OVER (ORDER BY EXTRACT(YEAR FROM order_date), '
        'EXTRACT(MONTH FROM order_date)) * 100 ELSE NULL END',
        'growth_percentage'
    )\
    .group_by('year', 'month')\
    .order_by('year', 'month')\
    .aggregate()
```

## Advanced Report Generation Techniques

### Cross-tabulation Reports

Cross-tabulation (pivot tables) can be implemented using conditional aggregation:

```python
# Product sales by category and region
product_sales_pivot = OrderItem.query()\
    .join('JOIN orders ON order_items.order_id = orders.id')\
    .join('JOIN products ON order_items.product_id = products.id')\
    .select('products.category')\
    .select_expr(FunctionExpression('SUM', 
                                   CaseExpression('orders.region', 
                                                 {'North': 'order_items.quantity'}, 
                                                 '0'), 
                                   alias='north_sales'))\
    .select_expr(FunctionExpression('SUM', 
                                   CaseExpression('orders.region', 
                                                 {'South': 'order_items.quantity'}, 
                                                 '0'), 
                                   alias='south_sales'))\
    .select_expr(FunctionExpression('SUM', 
                                   CaseExpression('orders.region', 
                                                 {'East': 'order_items.quantity'}, 
                                                 '0'), 
                                   alias='east_sales'))\
    .select_expr(FunctionExpression('SUM', 
                                   CaseExpression('orders.region', 
                                                 {'West': 'order_items.quantity'}, 
                                                 '0'), 
                                   alias='west_sales'))\
    .group_by('products.category')\
    .aggregate()
```

### Time Series Analysis

Time series reports can help identify trends over time:

```python
# Daily active users with 7-day moving average
user_activity = UserActivity.query()\
    .select('activity_date')\
    .count('DISTINCT user_id', 'daily_active_users')\
    .window_function(
        'AVG(COUNT(DISTINCT user_id)) OVER (ORDER BY activity_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)',
        'seven_day_average'
    )\
    .group_by('activity_date')\
    .order_by('activity_date')\
    .aggregate()
```

## Integrating with Reporting Tools

### Exporting to CSV/Excel

ActiveRecord query results can be easily exported to CSV or Excel for further analysis:

```python
import csv
import pandas as pd

# Export to CSV
report_data = SalesData.query()\
    .select('product_name', 'category', 'region')\
    .sum('amount', 'total_sales')\
    .group_by('product_name', 'category', 'region')\
    .aggregate()

# Using CSV module
with open('sales_report.csv', 'w', newline='') as csvfile:
    fieldnames = ['product_name', 'category', 'region', 'total_sales']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for row in report_data:
        writer.writerow(row)

# Using pandas for Excel export
df = pd.DataFrame(report_data)
df.to_excel('sales_report.xlsx', index=False)
```

### Integration with Data Visualization Libraries

ActiveRecord can be seamlessly integrated with popular data visualization libraries:

```python
import matplotlib.pyplot as plt
import seaborn as sns

# Get data for visualization
monthly_revenue = Order.query()\
    .select('EXTRACT(MONTH FROM order_date) as month')\
    .sum('total_amount', 'revenue')\
    .group_by('month')\
    .order_by('month')\
    .aggregate()

# Convert to lists for plotting
months = [row['month'] for row in monthly_revenue]
revenue = [row['revenue'] for row in monthly_revenue]

# Create visualization
plt.figure(figsize=(10, 6))
sns.barplot(x=months, y=revenue)
plt.title('Monthly Revenue')
plt.xlabel('Month')
plt.ylabel('Revenue ($)')
plt.tight_layout()
plt.savefig('monthly_revenue.png')
plt.show()
```

## Real-time Dashboards

ActiveRecord can be used to power real-time dashboards:

```python
from flask import Flask, jsonify
from datetime import datetime, timedelta

app = Flask(__name__)

@app.route('/api/dashboard/sales-today')
def sales_today():
    today = datetime.now().date()
    sales_data = Order.query()\
        .filter('order_date >= ?', (today,))\
        .sum('total_amount', 'total_sales')\
        .count('id', 'order_count')\
        .select_expr(FunctionExpression('AVG', 'total_amount', alias='average_order_value'))\
        .aggregate()[0]  # Get the first (and only) row
    
    return jsonify(sales_data)

@app.route('/api/dashboard/sales-by-hour')
def sales_by_hour():
    today = datetime.now().date()
    sales_by_hour = Order.query()\
        .filter('order_date >= ?', (today,))\
        .select('EXTRACT(HOUR FROM order_time) as hour')\
        .sum('total_amount', 'hourly_sales')\
        .group_by('hour')\
        .order_by('hour')\
        .aggregate()
    
    return jsonify(sales_by_hour)

if __name__ == '__main__':
    app.run(debug=True)
```

## Best Practices for Report Generation

### Optimizing Report Queries

1. **Use Appropriate Indexes**: Ensure that columns used in GROUP BY, ORDER BY, and WHERE clauses are properly indexed.

2. **Limit Data Transfer**: Select only the columns you need for the report.

3. **Consider Materialized Views**: For complex, frequently-run reports, consider using database materialized views.

4. **Batch Processing**: For large datasets, process data in batches to avoid memory issues:

```python
def generate_large_report(start_date, end_date, batch_size=1000):
    offset = 0
    results = []
    
    while True:
        batch = Order.query()\
            .filter('order_date BETWEEN ? AND ?', (start_date, end_date))\
            .select('customer_id', 'SUM(total_amount) as customer_total')\
            .group_by('customer_id')\
            .order_by('customer_total DESC')\
            .limit(batch_size)\
            .offset(offset)\
            .aggregate()
        
        if not batch:
            break
            
        results.extend(batch)
        offset += batch_size
        
    return results
```

### Caching Report Results

For reports that don't require real-time data, implement caching:

```python
import redis
import json
from datetime import datetime, timedelta

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def get_monthly_sales_report(year, month, force_refresh=False):
    cache_key = f"monthly_sales:{year}:{month}"
    
    # Try to get from cache first
    if not force_refresh:
        cached_report = redis_client.get(cache_key)
        if cached_report:
            return json.loads(cached_report)
    
    # Generate report from database
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)
    
    report_data = Order.query()\
        .filter('order_date BETWEEN ? AND ?', (start_date, end_date))\
        .select('product_category')\
        .sum('total_amount', 'category_sales')\
        .group_by('product_category')\
        .order_by('category_sales DESC')\
        .aggregate()
    
    # Cache the result (expire after 1 hour)
    redis_client.setex(
        cache_key,
        3600,  # 1 hour in seconds
        json.dumps(report_data)
    )
    
    return report_data
```

## Conclusion

rhosocial ActiveRecord provides a powerful and flexible foundation for report generation in data analysis applications. By leveraging its aggregate query capabilities, window functions, and expression support, you can create sophisticated reports without writing complex SQL. The integration with Python's rich ecosystem of data processing and visualization libraries further enhances its utility for reporting purposes.

Whether you're building simple summary reports, complex cross-tabulations, or real-time dashboards, ActiveRecord's intuitive API and performance optimization features make it an excellent choice for report generation tasks.