# Custom ActiveQuery Classes

This document explains how to create and use custom ActiveQuery classes to extend the query functionality for specific models.

## Introduction

While the default `ActiveQuery` class provides comprehensive query capabilities, you may need to add model-specific query methods or customize query behavior for particular models. Custom ActiveQuery classes allow you to encapsulate model-specific query logic in a dedicated class.

## Creating a Custom ActiveQuery Class

To create a custom ActiveQuery class, extend the base `ActiveQuery` class and add your specialized methods:

```python
from rhosocial.activerecord.query import ActiveQuery

class UserQuery(ActiveQuery):
    """Custom query class for User model with specialized query methods."""
    
    def active(self):
        """Find only active users."""
        return self.where('status = ?', 'active')
    
    def by_role(self, role):
        """Find users with a specific role."""
        return self.where('role = ?', role)
    
    def with_recent_orders(self, days=30):
        """Include users who placed orders in the last N days."""
        return self.join('JOIN orders ON users.id = orders.user_id')\  
                  .where('orders.created_at > NOW() - INTERVAL ? DAY', days)\  
                  .group_by('users.id')
```

## Configuring a Model to Use a Custom Query Class

To use your custom query class with a specific model, set the `__query_class__` attribute in your model class:

```python
from rhosocial.activerecord import ActiveRecord
from .queries import UserQuery

class User(ActiveRecord):
    """User model with custom query class."""
    
    __table__ = 'users'
    __query_class__ = UserQuery  # Specify the custom query class
    
    # Model definition continues...
```

With this configuration, calling `User.query()` will return an instance of `UserQuery` instead of the default `ActiveQuery`.

## Using Custom Query Methods

Once configured, you can use your custom query methods directly:

```python
# Find active users
active_users = User.query().active().all()

# Find administrators
admins = User.query().by_role('admin').all()

# Find users with recent orders
recent_customers = User.query().with_recent_orders(7).all()

# Chain custom and standard methods
results = User.query()\  
    .active()\  
    .by_role('customer')\  
    .with_recent_orders()\  
    .order_by('name')\  
    .limit(10)\  
    .all()
```

## Best Practices

1. **Maintain Method Chaining**: Always return `self` from your custom query methods to support method chaining.

2. **Document Query Methods**: Provide clear docstrings for your custom query methods to explain their purpose and parameters.

3. **Keep Methods Focused**: Each query method should have a single responsibility and clear purpose.

4. **Consider Query Composition**: Design methods that can be combined effectively with other query methods.

5. **Reuse Common Patterns**: If multiple models share similar query patterns, consider using mixins instead of duplicating code.

## Advanced Example: Query Class Hierarchy

For complex applications, you might create a hierarchy of query classes:

```python
# Base query class with common methods
class AppBaseQuery(ActiveQuery):
    def active_records(self):
        return self.where('is_active = ?', True)

# Department-specific query class
class DepartmentQuery(AppBaseQuery):
    def with_manager(self):
        return self.join('JOIN users ON departments.manager_id = users.id')\  
                  .select('departments.*', 'users.name AS manager_name')

# User-specific query class
class UserQuery(AppBaseQuery):
    def by_department(self, department_id):
        return self.where('department_id = ?', department_id)
```

Then configure your models to use the appropriate query classes:

```python
class Department(ActiveRecord):
    __query_class__ = DepartmentQuery
    # ...

class User(ActiveRecord):
    __query_class__ = UserQuery
    # ...
```

## Conclusion

Custom ActiveQuery classes provide a powerful way to organize and encapsulate model-specific query logic. By creating dedicated query classes, you can make your code more maintainable, improve readability, and provide a more intuitive API for working with your models.