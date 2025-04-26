# Having Clauses

The HAVING clause is used to filter groups in aggregate queries based on aggregate conditions. While the WHERE clause filters rows before they are grouped, the HAVING clause filters groups after aggregation has been performed. rhosocial ActiveRecord provides a clean API for working with HAVING clauses.

## Basic Usage

The `having()` method allows you to specify conditions that apply to groups after aggregation:

```python
# Find departments with more than 5 employees
large_departments = Employee.query()\
    .select('department')\
    .group_by('department')\
    .count('id', 'employee_count')\
    .having('COUNT(id) > ?', (5,))\
    .aggregate()

# Find products with average price greater than 100
expensive_categories = Product.query()\
    .select('category')\
    .group_by('category')\
    .avg('price', 'avg_price')\
    .having('AVG(price) > ?', (100,))\
    .aggregate()
```

## Parameterized HAVING Conditions

Like the WHERE clause, the HAVING clause supports parameterized queries to prevent SQL injection:

```python
# Find customers who have spent more than a certain amount
big_spenders = Order.query()\
    .select('customer_id')\
    .group_by('customer_id')\
    .sum('amount', 'total_spent')\
    .having('SUM(amount) > ?', (1000,))\
    .aggregate()
```

## Multiple HAVING Conditions

You can chain multiple `having()` calls to apply multiple conditions with AND logic:

```python
# Find product categories with many items and high average price
premium_categories = Product.query()\
    .select('category')\
    .group_by('category')\
    .count('id', 'product_count')\
    .avg('price', 'avg_price')\
    .having('COUNT(id) > ?', (10,))\
    .having('AVG(price) > ?', (50,))\
    .aggregate()
```

## Using Aggregate Functions in HAVING

The HAVING clause typically includes aggregate functions to filter based on group properties:

```python
# Common aggregate functions in HAVING
results = Order.query()\
    .select('customer_id')\
    .group_by('customer_id')\
    .count('id', 'order_count')\
    .sum('amount', 'total_amount')\
    .avg('amount', 'avg_amount')\
    .having('COUNT(id) > ?', (5,))  # More than 5 orders\
    .having('SUM(amount) > ?', (1000,))  # Total spent over 1000\
    .having('AVG(amount) > ?', (200,))  # Average order over 200\
    .aggregate()
```

## Column References in HAVING

It's important to note that HAVING clauses should reference original column expressions, not aliases. This follows SQL standard behavior:

```python
# Incorrect: Using alias in HAVING
user_stats = User.query()\
    .select('status')\
    .group_by('status')\
    .count('id', 'user_count')\
    .having('user_count > ?', (10,))  # This will fail!\
    .aggregate()

# Correct: Using aggregate function in HAVING
user_stats = User.query()\
    .select('status')\
    .group_by('status')\
    .count('id', 'user_count')\
    .having('COUNT(id) > ?', (10,))  # This works\
    .aggregate()
```

rhosocial ActiveRecord will issue a warning if it detects potential alias usage in HAVING clauses.

## Combining WHERE and HAVING

You can use both WHERE and HAVING in the same query for different filtering purposes:

```python
# WHERE filters rows before grouping, HAVING filters groups after aggregation
results = Order.query()\
    .where('status = ?', ('completed',))  # Only completed orders\
    .select('customer_id')\
    .group_by('customer_id')\
    .count('id', 'order_count')\
    .sum('amount', 'total_amount')\
    .having('COUNT(id) > ?', (3,))  # Customers with more than 3 completed orders\
    .having('SUM(amount) > ?', (500,))  # Who spent more than 500\
    .aggregate()
```

## Complex HAVING Conditions

You can use complex conditions in HAVING clauses, including multiple aggregate functions and logical operators:

```python
# Complex HAVING with multiple conditions
results = Product.query()\
    .select('category')\
    .group_by('category')\
    .count('id', 'product_count')\
    .avg('price', 'avg_price')\
    .having('COUNT(id) > 10 AND AVG(price) > 50')\
    .aggregate()

# Using OR in HAVING
results = Customer.query()\
    .select('country')\
    .group_by('country')\
    .count('id', 'customer_count')\
    .sum('lifetime_value', 'total_value')\
    .having('COUNT(id) > 1000 OR SUM(lifetime_value) > 1000000')\
    .aggregate()
```

## HAVING with Joins

HAVING clauses work well with JOINs for complex aggregate queries:

```python
# Find customers who have ordered specific products
results = Order.query()\
    .join('JOIN order_items ON orders.id = order_items.order_id')\
    .join('JOIN products ON order_items.product_id = products.id')\
    .where('products.category = ?', ('electronics',))\
    .select('orders.customer_id')\
    .group_by('orders.customer_id')\
    .count('DISTINCT products.id', 'unique_products')\
    .having('COUNT(DISTINCT products.id) > ?', (3,))  # Ordered more than 3 unique electronics\
    .aggregate()
```

## Performance Considerations

- HAVING clauses are applied after grouping and aggregation, which can be resource-intensive
- Use WHERE to filter rows before grouping whenever possible
- Only use HAVING for conditions that must be applied after aggregation
- Complex HAVING conditions may impact query performance, especially on large datasets

## Database Compatibility

The HAVING clause is supported by all major database backends, but there may be subtle differences in behavior:

- Some databases may allow referencing aliases in HAVING clauses (non-standard SQL)
- Function availability in HAVING clauses may vary by database

rhosocial ActiveRecord follows SQL standard behavior where HAVING clauses should use aggregate functions or columns from the GROUP BY clause, not aliases from the SELECT clause.