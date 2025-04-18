# Transaction Basics

This document covers the fundamentals of database transactions in rhosocial ActiveRecord. Transactions ensure that a series of database operations are executed atomically, meaning they either all succeed or all fail together.

## Understanding Transactions

Transactions are essential for maintaining data integrity in your application. They provide the following guarantees (often referred to as ACID properties):

- **Atomicity**: All operations within a transaction are treated as a single unit. Either all succeed or all fail.
- **Consistency**: A transaction brings the database from one valid state to another.
- **Isolation**: Transactions are isolated from each other until they are completed.
- **Durability**: Once a transaction is committed, its effects are permanent.

## Basic Transaction Usage

### Using the Transaction Context Manager

The simplest way to use transactions is with the `Transaction` context manager:

```python
from rhosocial.activerecord.backend.transaction import Transaction

# Using a transaction with context manager
with Transaction():
    user = User(username="johndoe", email="john@example.com")
    user.save()
    
    profile = Profile(user_id=user.id, bio="New user")
    profile.save()
    
    # If any operation fails, all changes will be rolled back
    # If all operations succeed, changes will be committed
```

### Manual Transaction Control

You can also manually control transactions:

```python
from rhosocial.activerecord.backend.transaction import Transaction

# Manual transaction control
transaction = Transaction()
try:
    transaction.begin()
    
    user = User(username="janedoe", email="jane@example.com")
    user.save()
    
    profile = Profile(user_id=user.id, bio="Another new user")
    profile.save()
    
    transaction.commit()
except Exception as e:
    transaction.rollback()
    print(f"Transaction failed: {e}")
```

## Error Handling in Transactions

When an error occurs within a transaction, all changes are automatically rolled back:

```python
try:
    with Transaction():
        user = User(username="testuser", email="test@example.com")
        user.save()
        
        # This will raise an exception
        invalid_profile = Profile(user_id=user.id, bio="" * 1000)  # Too long
        invalid_profile.save()
        
        # We never reach this point
        print("Transaction succeeded")
except Exception as e:
    # The transaction is automatically rolled back
    print(f"Transaction failed: {e}")
    
    # Verify that the user wasn't saved
    saved_user = User.find_one({"username": "testuser"})
    print(f"User exists: {saved_user is not None}")  # Should print False
```

## Nested Transactions

rhosocial ActiveRecord supports nested transactions. The behavior depends on the database backend, but generally follows the pattern where a nested transaction creates a savepoint:

```python
with Transaction() as outer_transaction:
    user = User(username="outer", email="outer@example.com")
    user.save()
    
    try:
        with Transaction() as inner_transaction:
            # This creates a savepoint
            invalid_user = User(username="inner", email="invalid-email")
            invalid_user.save()  # This will fail
    except Exception as e:
        print(f"Inner transaction failed: {e}")
        # Only the inner transaction is rolled back to the savepoint
    
    # The outer transaction can still continue
    another_user = User(username="another", email="another@example.com")
    another_user.save()
    
    # When the outer transaction completes, all successful changes are committed
```

## Transaction Isolation Levels

You can specify the isolation level for a transaction. The available isolation levels depend on the database backend:

```python
from rhosocial.activerecord.backend.transaction import Transaction, IsolationLevel

# Using a specific isolation level
with Transaction(isolation_level=IsolationLevel.SERIALIZABLE):
    # Operations with the highest isolation level
    user = User.find_one_for_update(1)  # Locks the row
    user.balance += 100
    user.save()
```

Common isolation levels include:

- `READ_UNCOMMITTED`: Lowest isolation level, allows dirty reads
- `READ_COMMITTED`: Prevents dirty reads
- `REPEATABLE_READ`: Prevents dirty and non-repeatable reads
- `SERIALIZABLE`: Highest isolation level, prevents all concurrency issues

## Transactions and Exceptions

You can control which exceptions trigger a rollback:

```python
class CustomException(Exception):
    pass

# Only specific exceptions will trigger a rollback
with Transaction(rollback_exceptions=[CustomException, ValueError]):
    # This will trigger a rollback
    raise ValueError("This triggers a rollback")
    
# All exceptions will trigger a rollback (default behavior)
with Transaction():
    # Any exception will trigger a rollback
    raise Exception("This also triggers a rollback")
```

## Best Practices

1. **Keep transactions short**: Long-running transactions can lead to performance issues and deadlocks.

2. **Handle exceptions properly**: Always catch exceptions and handle them appropriately.

3. **Use appropriate isolation levels**: Higher isolation levels provide more consistency but can reduce concurrency.

4. **Be aware of connection management**: Transactions are tied to database connections. In a multi-threaded environment, ensure proper connection handling.

5. **Consider using savepoints for complex operations**: For complex operations that might need partial rollbacks.

```python
with Transaction() as transaction:
    # Create a savepoint
    savepoint = transaction.savepoint("before_risky_operation")
    
    try:
        # Perform risky operation
        risky_operation()
    except Exception as e:
        # Roll back to the savepoint, not the entire transaction
        transaction.rollback_to_savepoint(savepoint)
        print(f"Risky operation failed: {e}")
    
    # Continue with the transaction
    safe_operation()
```

## Summary

Transactions are a powerful feature in rhosocial ActiveRecord that help maintain data integrity. By understanding and properly using transactions, you can ensure that your database operations are reliable and consistent, even in the face of errors or concurrent access.