# Custom Expressions

rhosocial ActiveRecord provides a powerful expression system that allows you to build complex SQL expressions for your queries. These expressions can be used in SELECT clauses, WHERE conditions, HAVING clauses, and other parts of your queries.

## Expression Types

The following expression types are available in rhosocial ActiveRecord:

| Expression Type | Description | Class |
|-----------------|-------------|-------|
| Arithmetic | Mathematical operations | `ArithmeticExpression` |
| Function | SQL function calls | `FunctionExpression` |
| Case | Conditional logic | `CaseExpression` |
| Conditional | COALESCE, NULLIF, etc. | `ConditionalExpression` |
| Subquery | Nested queries | `SubqueryExpression` |
| Grouping Set | CUBE, ROLLUP, GROUPING SETS | `GroupingSetExpression` |
| JSON | JSON operations | `JsonExpression` |
| Window | Window functions | `WindowExpression` |
| Aggregate | Aggregate functions | `AggregateExpression` |

## Arithmetic Expressions

Arithmetic expressions allow you to perform mathematical operations in your queries:

```python
from rhosocial.activerecord.query.expression import ArithmeticExpression

# Calculate profit margin
product_margins = Product.query()\
    .select('id', 'name', 'price', 'cost')\
    .select_expr(
        ArithmeticExpression(
            ArithmeticExpression('price', '-', 'cost'),
            '/',
            'price',
            'profit_margin'
        )
    )\
    .select_expr(
        ArithmeticExpression(
            ArithmeticExpression('price', '-', 'cost'),
            '*',
            '100',
            'profit_percentage'
        )
    )\
    .all()

# Calculate total value
inventory_value = Product.query()\
    .select('id', 'name')\
    .select_expr(
        ArithmeticExpression('price', '*', 'stock', 'inventory_value')
    )\
    .all()
```

Supported operators include `+`, `-`, `*`, `/`, and `%` (modulo).

## Function Expressions

Function expressions allow you to call SQL functions:

```python
from rhosocial.activerecord.query.expression import FunctionExpression

# String functions
user_data = User.query()\
    .select('id')\
    .select_expr(FunctionExpression('UPPER', 'name', alias='upper_name'))\
    .select_expr(FunctionExpression('LOWER', 'email', alias='lower_email'))\
    .select_expr(FunctionExpression('LENGTH', 'name', alias='name_length'))\
    .all()

# Date functions
order_dates = Order.query()\
    .select('id')\
    .select_expr(FunctionExpression('YEAR', 'created_at', alias='year'))\
    .select_expr(FunctionExpression('MONTH', 'created_at', alias='month'))\
    .select_expr(FunctionExpression('DAY', 'created_at', alias='day'))\
    .all()

# Mathematical functions
product_stats = Product.query()\
    .select('id', 'name', 'price')\
    .select_expr(FunctionExpression('ROUND', 'price', '2', alias='rounded_price'))\
    .select_expr(FunctionExpression('CEIL', 'price', alias='ceiling_price'))\
    .select_expr(FunctionExpression('FLOOR', 'price', alias='floor_price'))\
    .all()
```

Function expressions can be nested and combined with other expressions.

## CASE Expressions

CASE expressions allow you to implement conditional logic in your queries:

```python
from rhosocial.activerecord.query.expression import CaseExpression

# Simple CASE expression
product_categories = Product.query()\
    .select('id', 'name', 'price')\
    .select_expr(
        CaseExpression(
            [
                ('price < 10', 'Budget'),
                ('price BETWEEN 10 AND 50', 'Standard'),
                ('price > 50', 'Premium')
            ],
            'Unknown',  # Default value
            'price_category'
        )
    )\
    .all()

# CASE with parameters
user_status = User.query()\
    .select('id', 'name', 'last_login_at')\
    .select_expr(
        CaseExpression(
            [
                ('last_login_at > ?', 'Active'),
                ('last_login_at IS NULL', 'Never Logged In')
            ],
            'Inactive',  # Default value
            'status',
            params=[(datetime.now() - timedelta(days=30),)]  # Parameters for conditions
        )
    )\
    .all()
```

CASE expressions are particularly useful for categorizing data and implementing business logic directly in your queries.

## Conditional Expressions

Conditional expressions provide shortcuts for common conditional operations:

```python
from rhosocial.activerecord.query.expression import ConditionalExpression

# COALESCE: Return the first non-NULL value
user_display = User.query()\
    .select('id')\
    .select_expr(
        ConditionalExpression.coalesce(
            'display_name', 'username', 'email', 'Anonymous',
            alias='display_name'
        )
    )\
    .all()

# NULLIF: Return NULL if two expressions are equal
product_discount = Product.query()\
    .select('id', 'name', 'price', 'sale_price')\
    .select_expr(
        ConditionalExpression.nullif('price', 'sale_price', alias='discount_exists')
    )\
    .all()

# IF/ELSE (database-specific)
order_status = Order.query()\
    .select('id')\
    .select_expr(
        ConditionalExpression.if_else(
            'paid_at IS NOT NULL',
            'Paid',
            'Unpaid',
            alias='payment_status'
        )
    )\
    .all()
```

These expressions provide a more concise way to express common conditional patterns.

## Subquery Expressions

Subquery expressions allow you to embed one query within another:

```python
from rhosocial.activerecord.query.expression import SubqueryExpression

# Find products with above-average price
products = Product.query()\
    .select('id', 'name', 'price')\
    .select_expr(
        SubqueryExpression(
            Product.query().select('AVG(price)'),
            'avg_price'
        )
    )\
    .where('price > (SELECT AVG(price) FROM products)')\
    .all()

# Count related records
customers = Customer.query()\
    .select('id', 'name')\
    .select_expr(
        SubqueryExpression(
            Order.query()\
                .select('COUNT(*)')\
                .where('customer_id = customers.id'),
            'order_count'
        )
    )\
    .all()
```

Subquery expressions are powerful for complex data analysis and can often replace JOINs for certain use cases.

## Grouping Set Expressions

Grouping set expressions enable advanced aggregation techniques:

```python
from rhosocial.activerecord.query.expression import GroupingSetExpression

# ROLLUP: Hierarchical aggregation
sales_report = Sale.query()\
    .select('year', 'quarter', 'month', 'SUM(amount) as total')\
    .rollup('year', 'quarter', 'month')\
    .aggregate()

# CUBE: Multi-dimensional aggregation
product_analysis = Sale.query()\
    .select('category', 'region', 'SUM(amount) as total')\
    .cube('category', 'region')\
    .aggregate()

# GROUPING SETS: Custom combinations
custom_report = Sale.query()\
    .select('year', 'quarter', 'product', 'SUM(amount) as total')\
    .grouping_sets(
        ['year', 'quarter'],
        ['year', 'product'],
        ['quarter', 'product']
    )\
    .aggregate()
```

These advanced grouping techniques are primarily supported by PostgreSQL, with partial support in MySQL/MariaDB (ROLLUP only) and no support in SQLite.

## Combining Expressions

One of the most powerful features of the expression system is the ability to combine expressions:

```python
from rhosocial.activerecord.query.expression import (
    ArithmeticExpression, FunctionExpression, CaseExpression
)

# Complex pricing calculation
product_pricing = Product.query()\
    .select('id', 'name', 'price', 'cost')\
    .select_expr(
        ArithmeticExpression(
            'price',
            '*',
            CaseExpression(
                [
                    ('category = "Electronics"', '0.9'),
                    ('category = "Clothing"', '0.8'),
                ],
                '0.95',  # Default discount
                None  # No alias for nested expression
            ),
            'discounted_price'
        )
    )\
    .select_expr(
        ArithmeticExpression(
            ArithmeticExpression(
                FunctionExpression('ROUND', 
                    ArithmeticExpression('price', '-', 'cost'),
                    '2'
                ),
                '/',
                'price'
            ),
            '*',
            '100',
            'margin_percentage'
        )
    )\
    .all()
```

## Using Expressions in Different Contexts

Expressions can be used in various parts of your queries:

### In SELECT Clauses

```python
products = Product.query()\
    .select('id', 'name')\
    .select_expr(ArithmeticExpression('price', '*', '1.1', 'price_with_tax'))\
    .all()
```

### In WHERE Clauses

```python
products = Product.query()\
    .where_expr(ArithmeticExpression('price', '*', '0.9', None), '>', '100')\
    .all()
```

### In ORDER BY Clauses

```python
products = Product.query()\
    .select('id', 'name', 'price', 'stock')\
    .select_expr(ArithmeticExpression('price', '*', 'stock', 'inventory_value'))\
    .order_by_expr(ArithmeticExpression('price', '*', 'stock', None), 'DESC')\
    .all()
```

### In HAVING Clauses

```python
category_stats = Product.query()\
    .select('category')\
    .group_by('category')\
    .having_expr(FunctionExpression('AVG', 'price'), '>', '100')\
    .aggregate()
```

## Database Compatibility

Expression support varies by database:

- **PostgreSQL**: Comprehensive support for all expression types
- **MySQL/MariaDB**: Good support for most expressions, with some limitations
- **SQLite**: Basic support for common expressions, with more limitations

rhosocial ActiveRecord will raise appropriate exceptions when unsupported features are used with a particular database backend.

## Performance Considerations

- Complex expressions can impact query performance
- Use appropriate indexes for columns referenced in expressions
- Consider materializing complex calculations for frequently accessed data
- Test queries with EXPLAIN to understand their execution plan
- For very complex expressions, consider using database views or stored procedures