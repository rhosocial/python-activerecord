# Error Handling in Transactions

Proper error handling is crucial when working with database transactions. rhosocial ActiveRecord provides several mechanisms to handle errors that occur during transaction processing, ensuring data integrity while giving developers flexibility in error management.

## Transaction Error Types

rhosocial ActiveRecord defines several error types related to transactions:

- **TransactionError**: Base class for all transaction-related errors
- **IsolationLevelError**: Raised when attempting to change isolation level during an active transaction

These errors are defined in the `rhosocial.activerecord.backend.errors` module:

```python
from rhosocial.activerecord.backend.errors import TransactionError, IsolationLevelError
```

## Automatic Error Handling with Context Managers

The recommended way to handle transaction errors is using the context manager interface, which automatically rolls back the transaction if an exception occurs:

```python
try:
    with User.transaction():
        user1.save()
        user2.save()
        if some_condition:
            raise ValueError("Demonstration error")
        user3.save()
        # If any exception occurs, the transaction is automatically rolled back
except ValueError as e:
    # Handle the specific error
    print(f"Transaction failed: {e}")
```

This approach ensures that the transaction is properly rolled back even if you forget to handle a specific exception.

## Manual Error Handling

When using explicit transaction methods, you need to handle errors manually:

```python
# Begin transaction
User.backend().begin_transaction()

try:
    # Perform operations
    user1.save()
    user2.save()
    
    # Commit transaction
    User.backend().commit_transaction()
except Exception as e:
    # Roll back transaction on any error
    User.backend().rollback_transaction()
    print(f"Transaction failed: {e}")
    # Re-raise or handle the exception as needed
    raise
```

## Handling Specific Database Errors

Different database systems may raise different types of errors. rhosocial ActiveRecord attempts to normalize these errors, but you may still need to handle database-specific errors in some cases:

```python
from rhosocial.activerecord.backend.errors import (
    DatabaseError,
    ConstraintViolationError,
    DeadlockError,
    LockTimeoutError
)

try:
    with User.transaction():
        # Operations that might cause database errors
        user.save()
except ConstraintViolationError as e:
    # Handle constraint violations (e.g., unique constraint)
    print(f"Constraint violation: {e}")
except DeadlockError as e:
    # Handle deadlock situations
    print(f"Deadlock detected: {e}")
    # Maybe retry the transaction
except LockTimeoutError as e:
    # Handle lock timeout
    print(f"Lock timeout: {e}")
except DatabaseError as e:
    # Handle other database errors
    print(f"Database error: {e}")
except Exception as e:
    # Handle other exceptions
    print(f"Other error: {e}")
```

## Error Handling in Nested Transactions

When working with nested transactions, error handling becomes more complex. By default, an error in a nested transaction will roll back only that nested transaction, not the outer transaction:

```python
# Begin outer transaction
with User.transaction():
    user1.save()  # Part of outer transaction
    
    try:
        # Begin nested transaction
        with User.transaction():
            user2.save()  # Part of nested transaction
            raise ValueError("Error in nested transaction")
            # Nested transaction is rolled back automatically
    except ValueError as e:
        # Handle the error from the nested transaction
        print(f"Nested transaction error: {e}")
    
    # Outer transaction continues
    user3.save()  # Part of outer transaction
    # Outer transaction commits: user1 and user3 are saved, user2 is not
```

If you want an error in a nested transaction to roll back the entire transaction, you need to re-raise the exception:

```python
# Begin outer transaction
with User.transaction():
    user1.save()  # Part of outer transaction
    
    try:
        # Begin nested transaction
        with User.transaction():
            user2.save()  # Part of nested transaction
            raise ValueError("Error in nested transaction")
            # Nested transaction is rolled back automatically
    except ValueError as e:
        # Re-raise to roll back outer transaction too
        raise
    
    # This code won't execute if an error occurs in the nested transaction
    user3.save()
```

## Error Handling with Savepoints

When working with savepoints, you can handle errors by rolling back to a specific savepoint:

```python
# Get the transaction manager
tx_manager = User.backend().transaction_manager

# Begin transaction
User.backend().begin_transaction()

try:
    # Perform initial operations
    user1.save()
    
    # Create a savepoint
    savepoint_name = tx_manager.savepoint("before_risky_operation")
    
    try:
        # Perform risky operations
        user2.save()
        risky_operation()
    except Exception as e:
        # Roll back to savepoint on error
        tx_manager.rollback_to(savepoint_name)
        print(f"Rolled back risky operation: {e}")
    
    # Continue with transaction
    user3.save()
    
    # Commit transaction
    User.backend().commit_transaction()
except Exception as e:
    # Roll back entire transaction on other errors
    User.backend().rollback_transaction()
    print(f"Transaction failed: {e}")
    raise
```

## Logging Transaction Errors

rhosocial ActiveRecord's transaction manager includes built-in logging for transaction operations and errors. You can configure the logger to capture more detailed information:

```python
import logging

# Configure logger
logger = logging.getLogger('transaction')
logger.setLevel(logging.DEBUG)

# Add handler
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

# Set logger on transaction manager
User.backend().transaction_manager.logger = logger
```

With this configuration, all transaction operations and errors will be logged with detailed information.

## Retry Strategies for Transaction Errors

Some transaction errors, such as deadlocks or lock timeouts, are temporary and can be resolved by retrying the transaction. Here's a simple retry strategy:

```python
from rhosocial.activerecord.backend.errors import DeadlockError, LockTimeoutError
import time

def perform_with_retry(max_retries=3, retry_delay=0.5):
    retries = 0
    while True:
        try:
            with User.transaction():
                # Perform database operations
                user1.save()
                user2.save()
            # Success, exit the loop
            break
        except (DeadlockError, LockTimeoutError) as e:
            retries += 1
            if retries > max_retries:
                # Max retries exceeded, re-raise the exception
                raise
            # Wait before retrying
            time.sleep(retry_delay * retries)  # Exponential backoff
            print(f"Retrying transaction after error: {e} (attempt {retries})")
```

## Best Practices

1. **Use context managers**: They ensure proper rollback on errors
2. **Catch specific exceptions**: Handle different types of errors appropriately
3. **Consider retry strategies**: For transient errors like deadlocks
4. **Log transaction errors**: For debugging and monitoring
5. **Be careful with nested transactions**: Understand how errors propagate
6. **Use savepoints for complex operations**: They provide more control over error recovery
7. **Test error scenarios**: Ensure your error handling works as expected

## Next Steps

- Learn about [Transaction Management](transaction_management.md)
- Explore [Isolation Level Configuration](isolation_level_configuration.md)
- Understand [Nested Transactions](nested_transactions.md)
- Master [Savepoints](savepoints.md)