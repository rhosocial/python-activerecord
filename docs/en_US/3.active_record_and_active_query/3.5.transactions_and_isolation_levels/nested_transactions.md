# Nested Transactions

Nested transactions allow you to start a new transaction within an already running transaction. rhosocial ActiveRecord provides robust support for nested transactions through savepoints, enabling more granular control over complex database operations.

## Understanding Nested Transactions

In rhosocial ActiveRecord, when you begin a transaction inside an already active transaction, the framework creates a savepoint rather than starting a new physical transaction. This approach allows for partial rollbacks within a larger transaction.

The transaction nesting level is tracked internally, and each nested transaction operation affects only the current nesting level:

```python
# Begin outer transaction (level 1)
with User.transaction():
    user1.save()  # Part of outer transaction
    
    # Begin nested transaction (level 2)
    with User.transaction():
        user2.save()  # Part of nested transaction
        
        # If an exception occurs here, only the nested transaction is rolled back
        # user2 changes are rolled back, but user1 changes remain
    
    # Continue with outer transaction
    user3.save()  # Part of outer transaction
```

## How Nested Transactions Work

rhosocial ActiveRecord implements nested transactions using the following approach:

1. The first `begin_transaction()` call starts a real database transaction
2. Subsequent `begin_transaction()` calls create savepoints
3. When a nested transaction is committed, its savepoint is released
4. When a nested transaction is rolled back, the database is rolled back to its savepoint
5. Only when the outermost transaction is committed does the entire transaction get committed to the database

## Transaction Nesting Level

The transaction manager keeps track of the current nesting level:

```python
# Get the transaction manager
tx_manager = User.backend().transaction_manager

# Check current nesting level (0 if no active transaction)
level = tx_manager.transaction_level
print(f"Current transaction level: {level}")
```

Each call to `begin_transaction()` increments the level, and each call to `commit_transaction()` or `rollback_transaction()` decrements it.

## Nested Transaction Example

Here's a more detailed example of nested transactions:

```python
from rhosocial.activerecord.backend.errors import TransactionError

# Begin outer transaction
User.backend().begin_transaction()

try:
    # Operations in outer transaction
    user1 = User(name="User 1")
    user1.save()
    
    try:
        # Begin nested transaction
        User.backend().begin_transaction()
        
        # Operations in nested transaction
        user2 = User(name="User 2")
        user2.save()
        
        # Simulate an error
        if user2.name == "User 2":
            raise ValueError("Demonstration error")
            
        # This won't execute due to the error
        User.backend().commit_transaction()
    except Exception as e:
        # Rollback only the nested transaction
        User.backend().rollback_transaction()
        print(f"Nested transaction rolled back: {e}")
    
    # Continue with outer transaction
    user3 = User(name="User 3")
    user3.save()
    
    # Commit outer transaction
    User.backend().commit_transaction()
    # Result: user1 and user3 are saved, user2 is not
    
except Exception as e:
    # Rollback entire transaction if outer transaction fails
    User.backend().rollback_transaction()
    print(f"Outer transaction rolled back: {e}")
```

## Using Context Managers for Nested Transactions

The recommended way to work with nested transactions is using context managers, which handle the nesting automatically:

```python
# Outer transaction
with User.transaction():
    user1.save()
    
    # Nested transaction
    try:
        with User.transaction():
            user2.save()
            raise ValueError("Demonstration error")
    except ValueError:
        # The nested transaction is automatically rolled back
        # but the outer transaction continues
        pass
    
    user3.save()
    # Outer transaction commits: user1 and user3 are saved, user2 is not
```

## Database Support for Nested Transactions

Nested transaction support varies by database:

- **PostgreSQL**: Full support for nested transactions via savepoints
- **MySQL/MariaDB**: Full support for nested transactions via savepoints
- **SQLite**: Basic support for nested transactions via savepoints

## Limitations and Considerations

1. **Isolation Level Effects**: The isolation level of the outermost transaction applies to all nested transactions
2. **Error Handling**: Errors in nested transactions don't automatically propagate to outer transactions unless unhandled
3. **Resource Usage**: Deeply nested transactions can consume additional resources
4. **Deadlock Potential**: Complex nested transactions may increase deadlock potential

## Best Practices

1. **Keep nesting shallow**: Avoid deeply nested transactions
2. **Use context managers**: They ensure proper cleanup even when exceptions occur
3. **Handle exceptions appropriately**: Decide whether errors should propagate to outer transactions
4. **Consider using savepoints directly**: For more complex scenarios, explicit savepoints offer more control
5. **Test thoroughly**: Nested transactions can have subtle behavior differences across databases

## Next Steps

- Learn about [Savepoints](savepoints.md) for more granular control
- Understand [Error Handling in Transactions](error_handling_in_transactions.md)
- Return to [Transaction Management](transaction_management.md)