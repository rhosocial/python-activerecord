# Transaction Management

Transaction management is a critical aspect of database operations that ensures data integrity and consistency. rhosocial ActiveRecord provides a robust transaction management system that works across different database backends.

## Basic Transaction Operations

rhosocial ActiveRecord offers several ways to work with transactions:

### Using the Context Manager (Recommended)

The most convenient and recommended way to use transactions is through the context manager interface:

```python
with User.transaction():
    user1.save()
    user2.save()
    # All operations succeed or fail together
```

The context manager automatically handles beginning, committing, and rolling back transactions. If any exception occurs within the transaction block, the transaction is automatically rolled back.

### Using Explicit Transaction Methods

For more control, you can use explicit transaction methods:

```python
# Get the backend instance
backend = User.backend()

# Begin transaction
backend.begin_transaction()

try:
    user1.save()
    user2.save()
    # Commit if all operations succeed
    backend.commit_transaction()
except Exception:
    # Rollback if any operation fails
    backend.rollback_transaction()
    raise
```

## Transaction States

A transaction in rhosocial ActiveRecord can be in one of the following states:

- **INACTIVE**: No active transaction
- **ACTIVE**: Transaction has been started but not yet committed or rolled back
- **COMMITTED**: Transaction has been successfully committed
- **ROLLED_BACK**: Transaction has been rolled back

You can check if a transaction is active using the `in_transaction` property:

```python
if User.backend().in_transaction:
    # We're currently in a transaction
    pass
```

## Transaction Manager

Behind the scenes, rhosocial ActiveRecord uses a `TransactionManager` class to handle transaction operations. Each database backend implements its own transaction manager that handles the specifics of that database system.

The transaction manager is responsible for:

- Beginning, committing, and rolling back transactions
- Managing transaction isolation levels
- Handling nested transactions through savepoints
- Providing the context manager interface

## Auto-Commit Behavior

When not in a transaction, rhosocial ActiveRecord follows these auto-commit rules:

1. By default, individual operations are auto-committed
2. Batch operations are also auto-committed unless wrapped in a transaction

This behavior can be controlled through the `auto_commit` parameter in various methods:

```python
# Disable auto-commit for this operation
User.backend().execute_sql("UPDATE users SET status = 'active'", auto_commit=False)
```

## Database-Specific Considerations

While rhosocial ActiveRecord provides a consistent transaction API across all supported databases, there are some database-specific considerations:

- **SQLite**: Supports basic transaction functionality but has limitations with concurrent transactions
- **MySQL/MariaDB**: Provides full transaction support with various isolation levels
- **PostgreSQL**: Offers the most comprehensive transaction support, including deferrable constraints

## Best Practices

1. **Use context managers**: The `with Model.transaction():` syntax is cleaner and safer
2. **Keep transactions short**: Long-running transactions can cause performance issues
3. **Handle exceptions properly**: Always ensure transactions are rolled back on errors
4. **Be aware of isolation levels**: Choose the appropriate isolation level for your use case
5. **Consider using savepoints**: For complex operations, savepoints provide additional control

## Next Steps

- Learn about [Isolation Level Configuration](isolation_level_configuration.md)
- Explore [Nested Transactions](nested_transactions.md)
- Understand [Savepoints](savepoints.md)
- Master [Error Handling in Transactions](error_handling_in_transactions.md)