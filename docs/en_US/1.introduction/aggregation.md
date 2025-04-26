# Advanced Aggregation Capabilities

rhosocial ActiveRecord provides a powerful and expressive aggregation system that surpasses many competing ORMs in terms of both capabilities and ease of use.

## Rich Expression System

The framework implements a comprehensive SQL expression system that supports a wide range of aggregation operations:

- **Aggregate Functions**: Standard functions (COUNT, SUM, AVG, MIN, MAX) with support for DISTINCT
- **Window Functions**: Complete support for window functions with complex frame specifications
- **CASE Expressions**: Conditional logic within queries
- **Mathematical Expressions**: Arithmetic operations within queries
- **Subqueries**: Complex nested queries
- **JSON Expressions**: Database-agnostic JSON operations

## Advanced Grouping Operations

rhosocial ActiveRecord supports SQL standard advanced grouping operations:

- **CUBE**: Multi-dimensional analysis with all possible grouping combinations
- **ROLLUP**: Hierarchical aggregation with progressive subtotals
- **GROUPING SETS**: Custom aggregation combinations

## Scalar and Aggregate Function Modes

The aggregation API provides two convenient execution modes:

1. **Scalar Function Mode**: For simple aggregations without grouping
   ```python
   # Directly returns the count
   count = User.query().count()
   ```

2. **Aggregate Function Mode**: For complex aggregations with grouping
   ```python
   # Returns results with multiple aggregations
   results = User.query()
       .group_by('department')
       .count('id', 'user_count')
       .sum('salary', 'total_salary')
       .aggregate()
   ```

## Cross-Database Compatibility

The aggregation system automatically adapts to different database dialects, providing a consistent API while generating database-specific SQL.

## Advanced Query Examples

```python
# Multi-dimensional analysis with CUBE
result = User.query()
    .select('department', 'role')
    .cube('department', 'role')
    .count('id', 'count')
    .sum('salary', 'total')
    .aggregate()

# Window functions
result = User.query()
    .select('department')
    .window(
        AggregateExpression('AVG', 'salary'),
        partition_by=['department'],
        order_by=['hire_date'],
        frame_type='ROWS',
        frame_start='UNBOUNDED PRECEDING',
        frame_end='CURRENT ROW',
        alias='avg_salary'
    )
    .all()

# JSON operations with aggregation
result = User.query()
    .json_expr('settings', '$.theme', 'extract', alias='theme')
    .group_by('theme')
    .count('id', 'user_count')
    .aggregate()
```

Compared to other ORMs, rhosocial ActiveRecord's aggregation capabilities offer a balance of power and simplicity:

- More intuitive than SQLAlchemy's aggregation API
- More powerful than Django ORM's limited aggregation functions
- More comprehensive than Peewee's basic aggregation support