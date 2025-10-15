# Async Access

> **❌ NOT IMPLEMENTED**: The async access feature described in this document is currently **not implemented**. This documentation describes the planned functionality and is provided for future reference only. Current users should rely on synchronous operations only. This feature may be developed in future releases with no guaranteed timeline. The API described in this document is subject to significant changes when implementation begins.

This document explains how to use asynchronous database operations with ActiveRecord to improve performance in I/O-bound applications. **Note: This is currently aspirational documentation and does not reflect implemented functionality.**

## Introduction

Asynchronous programming allows your application to perform other tasks while waiting for database operations to complete, which can significantly improve performance and responsiveness in I/O-bound applications. ActiveRecord plans to provide support for asynchronous database operations through compatible async database drivers.

## When to Use Async Access

Asynchronous database access is particularly beneficial in these scenarios:

1. **Web Applications**: Handling multiple concurrent requests efficiently
2. **API Servers**: Processing numerous database operations in parallel
3. **Data Processing**: Working with large datasets where operations can be parallelized
4. **Microservices**: Managing multiple service interactions with databases

## Setting Up Async Database Connections

To use async database access, you need to configure ActiveRecord with an async-compatible database driver:

```python
from rhosocial.activerecord import ActiveRecord

# Configure ActiveRecord with an async driver
ActiveRecord.configure({
    'default': {
        'driver': 'pgsql',  # PostgreSQL with asyncpg
        'driver_type': 'asyncpg',  # Specify the async driver
        'host': 'localhost',
        'database': 'myapp',
        'username': 'user',
        'password': 'password',
        'async_mode': True  # Enable async mode
    }
})
```

## Basic Async Operations

Once configured, you can use async versions of standard ActiveRecord methods:

```python
import asyncio
from rhosocial.activerecord import ActiveRecord

class User(ActiveRecord):
    __table_name__ = 'users'

async def get_users():
    # Async query execution
    users = await User.query().async_all()
    return users

async def create_user(data):
    user = User()
    user.attributes = data
    # Async save operation
    success = await user.async_save()
    return user if success else None

# Run in an async context
asyncio.run(get_users())
```

## Async Query Methods

ActiveRecord provides async versions of all standard query methods:

```python
async def example_async_queries():
    # Find by primary key
    user = await User.async_find(1)
    
    # Find with conditions
    active_users = await User.query().where('status = ?', 'active').async_all()
    
    # Find first record
    first_admin = await User.query().where('role = ?', 'admin').async_first()
    
    # Count records
    user_count = await User.query().async_count()
    
    # Aggregations
    avg_age = await User.query().async_average('age')
```

## Async Transactions

You can also use transactions asynchronously:

```python
async def transfer_funds(from_account_id, to_account_id, amount):
    async with Account.async_transaction() as transaction:
        try:
            from_account = await Account.async_find(from_account_id)
            to_account = await Account.async_find(to_account_id)
            
            from_account.balance -= amount
            to_account.balance += amount
            
            await from_account.async_save()
            await to_account.async_save()
            
            # Commit happens automatically if no exceptions occur
        except Exception as e:
            # Rollback happens automatically on exception
            print(f"Transaction failed: {e}")
            raise
```

## Parallel Async Operations

One of the key benefits of async access is the ability to perform multiple database operations in parallel:

```python
async def process_data():
    # Execute multiple queries in parallel
    users_task = User.query().async_all()
    products_task = Product.query().async_all()
    orders_task = Order.query().where('status = ?', 'pending').async_all()
    
    # Wait for all queries to complete
    users, products, orders = await asyncio.gather(
        users_task, products_task, orders_task
    )
    
    # Now process the results
    return {
        'users': users,
        'products': products,
        'orders': orders
    }
```

## Async Relationships

You can also work with relationships asynchronously:

```python
async def get_user_with_orders(user_id):
    # Get user and related orders asynchronously
    user = await User.query().with_('orders').async_find(user_id)
    
    # Access the loaded relationship
    for order in user.orders:
        print(f"Order #{order.id}: {order.total}")
    
    return user
```

## Mixing Sync and Async Code

It's important to maintain a clear separation between synchronous and asynchronous code:

```python
# Synchronous context
def sync_function():
    # This is correct - using sync methods in sync context
    users = User.query().all()
    
    # This is INCORRECT - never call async methods directly from sync code
    # users = User.query().async_all()  # This will not work!
    
    # Instead, use an async runner if you need to call async from sync
    users = asyncio.run(User.query().async_all())
    return users

# Asynchronous context
async def async_function():
    # This is correct - using async methods in async context
    users = await User.query().async_all()
    
    # This is INCORRECT - blocking the async event loop with sync methods
    # users = User.query().all()  # Avoid this in async code
    
    return users
```

## Best Practices

1. **Consistent Async Style**: Use async methods consistently throughout an async context to avoid blocking the event loop.

2. **Error Handling**: Implement proper error handling for async operations, as exceptions propagate differently.

3. **Connection Management**: Be mindful of connection pooling and limits when executing many parallel operations.

4. **Avoid Blocking Operations**: Ensure all I/O operations in an async context are also async to prevent blocking the event loop.

5. **Testing**: Test async code thoroughly, as it can introduce different timing and concurrency issues.

## Limitations

- Not all database drivers support async operations
- Some complex features may have limited async support
- Debugging async code can be more challenging

## Conclusion

Asynchronous database access in ActiveRecord provides a powerful way to improve application performance by allowing concurrent database operations. By leveraging async capabilities, you can build more responsive and efficient applications, especially in scenarios with high concurrency or I/O-bound workloads.