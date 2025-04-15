# Dynamic Query Building

This document explains how to dynamically construct queries at runtime using ActiveRecord's query builder interface.

## Introduction

Dynamic query building allows you to construct database queries programmatically based on runtime conditions, user input, or application state. This is particularly useful for implementing flexible search features, complex filtering, or when the exact query structure isn't known until runtime.

## Basic Dynamic Query Construction

ActiveRecord's query builder is designed to support dynamic construction through method chaining. You can start with a base query and conditionally add clauses:

```python
from rhosocial.activerecord import ActiveRecord

class Product(ActiveRecord):
    __table_name__ = 'products'

def search_products(filters):
    """Search products with dynamic filters."""
    # Start with a base query
    query = Product.query()
    
    # Conditionally add filters
    if 'category' in filters:
        query = query.where('category_id = ?', filters['category'])
    
    if 'min_price' in filters:
        query = query.where('price >= ?', filters['min_price'])
    
    if 'max_price' in filters:
        query = query.where('price <= ?', filters['max_price'])
    
    if 'search_term' in filters:
        search_term = f'%{filters["search_term"]}%'
        query = query.where('name LIKE ? OR description LIKE ?', 
                           search_term, search_term)
    
    # Add sorting if specified
    if 'sort_by' in filters:
        direction = 'DESC' if filters.get('sort_desc', False) else 'ASC'
        query = query.order_by(f'{filters["sort_by"]} {direction}')
    
    # Apply pagination
    page = int(filters.get('page', 1))
    per_page = int(filters.get('per_page', 20))
    query = query.limit(per_page).offset((page - 1) * per_page)
    
    return query.all()

# Usage
results = search_products({
    'category': 5,
    'min_price': 10.00,
    'search_term': 'wireless',
    'sort_by': 'price',
    'sort_desc': True,
    'page': 2
})
```

## Handling Dynamic WHERE Conditions

For more complex filtering scenarios, you might need to build WHERE conditions dynamically:

```python
def advanced_search(filters):
    query = User.query()
    
    # Build WHERE conditions dynamically
    where_conditions = []
    params = []
    
    if filters.get('name'):
        where_conditions.append('name LIKE ?')
        params.append(f'%{filters["name"]}%')
    
    if filters.get('status'):
        where_conditions.append('status = ?')
        params.append(filters['status'])
    
    if filters.get('min_age'):
        where_conditions.append('age >= ?')
        params.append(filters['min_age'])
    
    if filters.get('max_age'):
        where_conditions.append('age <= ?')
        params.append(filters['max_age'])
    
    # Apply all conditions if any exist
    if where_conditions:
        # Join conditions with AND
        combined_condition = ' AND '.join(where_conditions)
        query = query.where(combined_condition, *params)
    
    return query.all()
```

## Dynamic Joins and Relationships

You can also dynamically include joins and relationships:

```python
def get_orders(filters, include_relations=None):
    query = Order.query()
    
    # Dynamically add joins/relations
    if include_relations:
        for relation in include_relations:
            if relation == 'customer':
                query = query.with_('customer')
            elif relation == 'items':
                query = query.with_('items')
            elif relation == 'items.product':
                query = query.with_('items.product')
    
    # Add filters
    if 'status' in filters:
        query = query.where('status = ?', filters['status'])
    
    if 'date_from' in filters:
        query = query.where('created_at >= ?', filters['date_from'])
    
    if 'date_to' in filters:
        query = query.where('created_at <= ?', filters['date_to'])
    
    return query.all()

# Usage
orders = get_orders(
    {'status': 'processing', 'date_from': '2023-01-01'}, 
    include_relations=['customer', 'items.product']
)
```

## Dynamic Field Selection

You can dynamically select which fields to retrieve:

```python
def get_users(fields=None):
    query = User.query()
    
    if fields:
        # Convert list of fields to comma-separated string
        # and ensure proper quoting of identifiers
        query = query.select(*fields)
    
    return query.all()

# Usage
users = get_users(fields=['id', 'username', 'email'])
```

## Building Complex Queries with Dictionaries

For highly dynamic queries, you can use dictionaries to define the query structure:

```python
def build_query_from_dict(model_class, query_dict):
    query = model_class.query()
    
    # Apply where conditions
    if 'where' in query_dict:
        for condition in query_dict['where']:
            field = condition['field']
            operator = condition.get('operator', '=')
            value = condition['value']
            
            # Handle different operators
            if operator == 'LIKE':
                query = query.where(f'{field} LIKE ?', f'%{value}%')
            elif operator == 'IN':
                placeholders = ', '.join(['?'] * len(value))
                query = query.where(f'{field} IN ({placeholders})', *value)
            else:
                query = query.where(f'{field} {operator} ?', value)
    
    # Apply joins
    if 'joins' in query_dict:
        for join in query_dict['joins']:
            query = query.join(join)
    
    # Apply ordering
    if 'order_by' in query_dict:
        for order in query_dict['order_by']:
            field = order['field']
            direction = order.get('direction', 'ASC')
            query = query.order_by(f'{field} {direction}')
    
    # Apply grouping
    if 'group_by' in query_dict:
        query = query.group_by(*query_dict['group_by'])
    
    # Apply limit and offset
    if 'limit' in query_dict:
        query = query.limit(query_dict['limit'])
    
    if 'offset' in query_dict:
        query = query.offset(query_dict['offset'])
    
    return query

# Usage
query_definition = {
    'where': [
        {'field': 'status', 'value': 'active'},
        {'field': 'created_at', 'operator': '>=', 'value': '2023-01-01'},
        {'field': 'category_id', 'operator': 'IN', 'value': [1, 2, 3]}
    ],
    'joins': [
        'JOIN categories ON products.category_id = categories.id'
    ],
    'order_by': [
        {'field': 'created_at', 'direction': 'DESC'}
    ],
    'limit': 20,
    'offset': 0
}

results = build_query_from_dict(Product, query_definition).all()
```

## Handling User Input Safely

When building queries dynamically from user input, always be careful about security:

```python
def safe_search(user_input):
    query = Product.query()
    
    # Whitelist of allowed fields for filtering and sorting
    allowed_filter_fields = {'category_id', 'brand_id', 'is_active'}
    allowed_sort_fields = {'price', 'name', 'created_at'}
    
    # Apply filters (only for allowed fields)
    for field, value in user_input.get('filters', {}).items():
        if field in allowed_filter_fields:
            query = query.where(f'{field} = ?', value)
    
    # Apply sorting (only for allowed fields)
    sort_field = user_input.get('sort_field')
    if sort_field and sort_field in allowed_sort_fields:
        direction = 'DESC' if user_input.get('sort_desc') else 'ASC'
        query = query.order_by(f'{sort_field} {direction}')
    
    return query.all()
```

## Best Practices

1. **Validate Input**: Always validate and sanitize user input before using it to build queries.

2. **Use Parameterized Queries**: Never directly interpolate values into SQL strings; always use parameterized queries with placeholders.

3. **Whitelist Fields**: When accepting field names from user input, validate them against a whitelist of allowed fields.

4. **Handle Edge Cases**: Consider what happens when filters are empty or invalid.

5. **Optimize Performance**: Be mindful of how dynamic queries might affect performance, especially with complex joins or large datasets.

6. **Test Thoroughly**: Test your dynamic query builders with various input combinations to ensure they generate correct SQL.

## Conclusion

Dynamic query building is a powerful feature of ActiveRecord that enables you to create flexible, adaptable database queries. By leveraging the query builder's method chaining interface, you can construct complex queries programmatically based on runtime conditions, making your application more responsive to user needs while maintaining clean, maintainable code.