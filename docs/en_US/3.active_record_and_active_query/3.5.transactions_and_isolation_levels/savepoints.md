# Savepoints

Savepoints provide a way to set intermediate markers within a transaction, allowing for partial rollbacks without aborting the entire transaction. rhosocial ActiveRecord offers comprehensive savepoint support, giving you fine-grained control over transaction operations.

## Understanding Savepoints

A savepoint is a point within a transaction that you can roll back to without rolling back the entire transaction. This is particularly useful for complex operations where you might want to retry only a portion of a transaction if an error occurs.

Savepoints are also the underlying mechanism that enables nested transactions in rhosocial ActiveRecord.

## Basic Savepoint Operations

rhosocial ActiveRecord provides three main operations for working with savepoints:

1. **Creating a savepoint**: Marks a point in the transaction that you can later roll back to
2. **Releasing a savepoint**: Removes a savepoint (but keeps all changes made since the savepoint)
3. **Rolling back to a savepoint**: Reverts all changes made since the savepoint was created

## Using Savepoints

To work with savepoints, you need to access the transaction manager directly:

```python
# Get the transaction manager
tx_manager = User.backend().transaction_manager

# Begin a transaction
User.backend().begin_transaction()

try:
    # Perform some operations
    user1 = User(name="User 1")
    user1.save()
    
    # Create a savepoint
    savepoint_name = tx_manager.savepoint("after_user1")
    
    # Perform more operations
    user2 = User(name="User 2")
    user2.save()
    
    # Something went wrong with user2
    if some_condition:
        # Roll back to the savepoint (undo user2 changes only)
        tx_manager.rollback_to(savepoint_name)
    else:
        # Release the savepoint (keep all changes)
        tx_manager.release(savepoint_name)
    
    # Continue with the transaction
    user3 = User(name="User 3")
    user3.save()
    
    # Commit the entire transaction
    User.backend().commit_transaction()
except Exception:
    # Roll back the entire transaction
    User.backend().rollback_transaction()
    raise
```

## Automatic Savepoint Naming

If you don't provide a name when creating a savepoint, rhosocial ActiveRecord will generate one automatically:

```python
# Create a savepoint with auto-generated name
savepoint_name = tx_manager.savepoint()
print(f"Created savepoint: {savepoint_name}")
```

The auto-generated names follow the pattern `SP_n` where `n` is an incremental counter.

## Savepoints and Nested Transactions

Nested transactions in rhosocial ActiveRecord are implemented using savepoints. When you begin a nested transaction, a savepoint is created automatically:

```python
# Begin outer transaction
User.backend().begin_transaction()

# Do some work
user1.save()

# Begin nested transaction (creates a savepoint internally)
User.backend().begin_transaction()

# Do more work
user2.save()

# Commit nested transaction (releases the savepoint)
User.backend().commit_transaction()

# Commit outer transaction
User.backend().commit_transaction()
```

If an error occurs in the nested transaction, rolling it back will roll back to the savepoint, preserving the work done in the outer transaction.

## Tracking Active Savepoints

The transaction manager keeps track of all active savepoints. When you roll back to a savepoint, all savepoints created after that one are automatically removed:

```python
# Begin transaction
User.backend().begin_transaction()

# Create first savepoint
sp1 = tx_manager.savepoint("sp1")

# Do some work
user1.save()

# Create second savepoint
sp2 = tx_manager.savepoint("sp2")

# Do more work
user2.save()

# Create third savepoint
sp3 = tx_manager.savepoint("sp3")

# Do even more work
user3.save()

# Roll back to the second savepoint
tx_manager.rollback_to(sp2)
# This undoes user3.save() and removes sp3
# Only sp1 and sp2 remain active

# Continue with transaction
user4.save()

# Commit transaction
User.backend().commit_transaction()
```

## Database Support for Savepoints

Savepoint support varies by database:

- **PostgreSQL**: Full support for savepoints with all standard operations
- **MySQL/MariaDB**: Full support for savepoints
- **SQLite**: Basic support for savepoints

The rhosocial ActiveRecord transaction manager automatically adapts to the capabilities of the underlying database.

## Error Handling with Savepoints

When working with savepoints, several errors can occur:

- **No active transaction**: Attempting to create, release, or roll back to a savepoint without an active transaction
- **Invalid savepoint name**: Attempting to release or roll back to a non-existent savepoint
- **Database-specific errors**: Issues with the underlying database operation

All these errors are wrapped in a `TransactionError` exception:

```python
from rhosocial.activerecord.backend.errors import TransactionError

try:
    # Attempt to create a savepoint without an active transaction
    savepoint_name = tx_manager.savepoint()
except TransactionError as e:
    print(f"Savepoint error: {e}")
```

## Best Practices

1. **Use meaningful savepoint names**: Makes debugging easier
2. **Don't overuse savepoints**: Too many savepoints can complicate transaction logic
3. **Clean up savepoints**: Release savepoints when they're no longer needed
4. **Handle errors properly**: Catch and handle `TransactionError` exceptions
5. **Consider using nested transactions**: For common patterns, nested transactions provide a cleaner interface

## Next Steps

- Learn about [Error Handling in Transactions](error_handling_in_transactions.md)
- Explore [Nested Transactions](nested_transactions.md)
- Return to [Transaction Management](transaction_management.md)