# Database Operation Testing

Transaction testing is not currently available in rhosocial ActiveRecord's testing framework. The current implementation provides basic database operation testing capabilities.

## Current Database Testing

Testing currently focuses on:

- Individual CRUD operation success/failure
- Basic database connection verification
- Simple query execution checks

## Basic Database Operation Test

```python
import unittest
from rhosocial.activerecord import ActiveRecord

class User(ActiveRecord):
    name: str
    email: str

class TestDatabaseOperations(unittest.TestCase):
    def test_create_operation(self):
        user = User(name="Test User", email="test@example.com")
        result = user.save()
        self.assertTrue(result)  # Or check that user.id is not None
        
    def test_retrieve_operation(self):
        user = User.find(1)  # Assuming a user with id=1 exists
        self.assertIsNotNone(user)
        
    def test_update_operation(self):
        user = User.find(1)
        if user:
            original_name = user.name
            user.name = "Updated Name"
            result = user.save()
            self.assertTrue(result)
    
    def test_delete_operation(self):
        user = User.find(1)
        if user:
            result = user.delete()
            self.assertTrue(result)
```

## Limitations

- No transaction isolation testing
- No multi-operation atomicity verification
- No rollback testing
- No concurrent access testing

These advanced database testing features will be added as transaction support is implemented.

## Setting Up Transaction Tests

### Test Database Configuration

For transaction testing, it's important to use a database that fully supports transactions:

```python
import pytest
from rhosocial.activerecord.backend import SQLiteBackend
from your_app.models import User, Account, Transfer

@pytest.fixture
def db_connection():
    """Create a test database connection."""
    connection = SQLiteBackend(":memory:")
    # Create necessary tables
    User.create_table(connection)
    Account.create_table(connection)
    Transfer.create_table(connection)
    yield connection
```

### Test Fixtures for Transaction Testing

Create fixtures with initial data for transaction tests:

```python
@pytest.fixture
def account_fixtures(db_connection):
    """Create test accounts for transaction testing."""
    # Create a user
    user = User(username="transaction_test", email="transaction@example.com")
    user.save()
    
    # Create accounts with initial balances
    account1 = Account(user_id=user.id, name="Account 1", balance=1000.00)
    account1.save()
    
    account2 = Account(user_id=user.id, name="Account 2", balance=500.00)
    account2.save()
    
    return {
        "user": user,
        "accounts": [account1, account2]
    }
```

## Testing Basic Transaction Functionality

Test that transactions properly commit or rollback changes:

```python
def test_basic_transaction_commit(db_connection, account_fixtures):
    """Test successful transaction commit."""
    accounts = account_fixtures["accounts"]
    account1 = accounts[0]
    account2 = accounts[1]
    
    # Initial balances
    initial_balance1 = account1.balance
    initial_balance2 = account2.balance
    
    # Perform a transfer within a transaction
    with db_connection.transaction():
        # Debit from account1
        account1.balance -= 200.00
        account1.save()
        
        # Credit to account2
        account2.balance += 200.00
        account2.save()
        
        # Create a transfer record
        transfer = Transfer(
            from_account_id=account1.id,
            to_account_id=account2.id,
            amount=200.00,
            status="completed"
        )
        transfer.save()
    
    # Reload accounts to verify changes were committed
    updated_account1 = Account.find_by_id(account1.id)
    updated_account2 = Account.find_by_id(account2.id)
    
    # Verify balances after transaction
    assert updated_account1.balance == initial_balance1 - 200.00
    assert updated_account2.balance == initial_balance2 + 200.00
    
    # Verify transfer record exists
    transfer = Transfer.find_by(from_account_id=account1.id, to_account_id=account2.id)
    assert transfer is not None
    assert transfer.amount == 200.00
    assert transfer.status == "completed"

def test_transaction_rollback(db_connection, account_fixtures):
    """Test transaction rollback on error."""
    accounts = account_fixtures["accounts"]
    account1 = accounts[0]
    account2 = accounts[1]
    
    # Initial balances
    initial_balance1 = account1.balance
    initial_balance2 = account2.balance
    
    # Attempt a transfer that will fail
    try:
        with db_connection.transaction():
            # Debit from account1
            account1.balance -= 200.00
            account1.save()
            
            # Credit to account2
            account2.balance += 200.00
            account2.save()
            
            # Simulate an error
            raise ValueError("Simulated error during transaction")
            
            # This code should not execute
            transfer = Transfer(
                from_account_id=account1.id,
                to_account_id=account2.id,
                amount=200.00,
                status="completed"
            )
            transfer.save()
    except ValueError:
        # Expected exception
        pass
    
    # Reload accounts to verify changes were rolled back
    updated_account1 = Account.find_by_id(account1.id)
    updated_account2 = Account.find_by_id(account2.id)
    
    # Verify balances are unchanged
    assert updated_account1.balance == initial_balance1
    assert updated_account2.balance == initial_balance2
    
    # Verify no transfer record exists
    transfer = Transfer.find_by(from_account_id=account1.id, to_account_id=account2.id)
    assert transfer is None
```

## Testing Transaction Isolation Levels

Test different transaction isolation levels to ensure they behave as expected:

```python
def test_transaction_isolation_read_committed(db_connection, account_fixtures):
    """Test READ COMMITTED isolation level."""
    # Skip if database doesn't support isolation levels
    if not hasattr(db_connection, "set_isolation_level"):
        pytest.skip("Database doesn't support isolation levels")
    
    accounts = account_fixtures["accounts"]
    account = accounts[0]
    
    # Start a transaction with READ COMMITTED isolation
    with db_connection.transaction(isolation_level="READ COMMITTED"):
        # Read initial balance
        initial_balance = account.balance
        
        # Simulate another connection updating the balance
        another_connection = SQLiteBackend(":memory:")
        another_connection.execute(
            f"UPDATE accounts SET balance = balance + 100 WHERE id = {account.id}"
        )
        
        # In READ COMMITTED, we should see the updated value when we read again
        account.refresh()  # Reload from database
        updated_balance = account.balance
        
        # Verify we can see the committed change
        assert updated_balance == initial_balance + 100

def test_transaction_isolation_repeatable_read(db_connection, account_fixtures):
    """Test REPEATABLE READ isolation level."""
    # Skip if database doesn't support isolation levels
    if not hasattr(db_connection, "set_isolation_level"):
        pytest.skip("Database doesn't support isolation levels")
    
    accounts = account_fixtures["accounts"]
    account = accounts[0]
    
    # Start a transaction with REPEATABLE READ isolation
    with db_connection.transaction(isolation_level="REPEATABLE READ"):
        # Read initial balance
        initial_balance = account.balance
        
        # Simulate another connection updating the balance
        another_connection = SQLiteBackend(":memory:")
        another_connection.execute(
            f"UPDATE accounts SET balance = balance + 100 WHERE id = {account.id}"
        )
        
        # In REPEATABLE READ, we should still see the original value
        account.refresh()  # Reload from database
        updated_balance = account.balance
        
        # Verify we still see the original value
        assert updated_balance == initial_balance
```

## Testing Nested Transactions

Test that nested transactions work correctly:

```python
def test_nested_transactions(db_connection, account_fixtures):
    """Test nested transactions behavior."""
    accounts = account_fixtures["accounts"]
    account1 = accounts[0]
    account2 = accounts[1]
    
    # Initial balances
    initial_balance1 = account1.balance
    initial_balance2 = account2.balance
    
    # Outer transaction
    with db_connection.transaction():
        # Update account1
        account1.balance -= 100.00
        account1.save()
        
        # Inner transaction that succeeds
        with db_connection.transaction():
            # Update account2
            account2.balance += 50.00
            account2.save()
        
        # Inner transaction that fails
        try:
            with db_connection.transaction():
                # Update account2 again
                account2.balance += 50.00
                account2.save()
                
                # Simulate an error
                raise ValueError("Simulated error in inner transaction")
        except ValueError:
            # Expected exception
            pass
    
    # Reload accounts to verify changes
    updated_account1 = Account.find_by_id(account1.id)
    updated_account2 = Account.find_by_id(account2.id)
    
    # Verify final balances
    # account1: initial - 100
    # account2: initial + 50 (from successful inner transaction)
    assert updated_account1.balance == initial_balance1 - 100.00
    assert updated_account2.balance == initial_balance2 + 50.00
```

## Testing Savepoints

Test savepoints for partial rollbacks within transactions:

```python
def test_savepoints(db_connection, account_fixtures):
    """Test savepoints for partial rollbacks."""
    # Skip if database doesn't support savepoints
    if not hasattr(db_connection, "savepoint"):
        pytest.skip("Database doesn't support savepoints")
    
    accounts = account_fixtures["accounts"]
    account1 = accounts[0]
    account2 = accounts[1]
    
    # Initial balances
    initial_balance1 = account1.balance
    initial_balance2 = account2.balance
    
    # Start a transaction
    with db_connection.transaction() as transaction:
        # Update account1
        account1.balance -= 200.00
        account1.save()
        
        # Create a savepoint
        savepoint = transaction.savepoint("transfer_savepoint")
        
        # Update account2
        account2.balance += 200.00
        account2.save()
        
        # Simulate a problem and rollback to savepoint
        transaction.rollback_to_savepoint(savepoint)
        
        # Try again with a different amount
        account2.balance += 150.00
        account2.save()
    
    # Reload accounts to verify changes
    updated_account1 = Account.find_by_id(account1.id)
    updated_account2 = Account.find_by_id(account2.id)
    
    # Verify final balances
    # account1: initial - 200
    # account2: initial + 150 (after savepoint rollback)
    assert updated_account1.balance == initial_balance1 - 200.00
    assert updated_account2.balance == initial_balance2 + 150.00
```

## Testing Error Handling in Transactions

Test how your application handles various error scenarios in transactions:

```python
def test_transaction_error_handling(db_connection, account_fixtures):
    """Test error handling in transactions."""
    accounts = account_fixtures["accounts"]
    account1 = accounts[0]
    account2 = accounts[1]
    
    # Test handling database constraint violations
    try:
        with db_connection.transaction():
            # Try to update account1 with an invalid value
            account1.balance = -1000.00  # Assuming negative balance is not allowed
            account1.save()
            
            # This should not execute if the constraint is enforced
            account2.balance += 1000.00
            account2.save()
    except Exception as e:
        # Verify the exception type matches what we expect
        assert "constraint" in str(e).lower() or "check" in str(e).lower()
    
    # Reload accounts to verify no changes were made
    updated_account1 = Account.find_by_id(account1.id)
    updated_account2 = Account.find_by_id(account2.id)
    
    assert updated_account1.balance == account1.balance
    assert updated_account2.balance == account2.balance
    
    # Test handling deadlocks (if supported by the database)
    # This is more complex and might require multiple threads/processes
```

## Testing Transaction Performance

Test the performance impact of transactions:

```python
import time

def test_transaction_performance(db_connection, account_fixtures):
    """Test transaction performance."""
    accounts = account_fixtures["accounts"]
    account1 = accounts[0]
    account2 = accounts[1]
    
    # Measure time for operations without a transaction
    start_time = time.time()
    for i in range(100):
        account1.balance -= 1.00
        account1.save()
        account2.balance += 1.00
        account2.save()
    no_transaction_time = time.time() - start_time
    
    # Reset accounts
    account1.balance = 1000.00
    account1.save()
    account2.balance = 500.00
    account2.save()
    
    # Measure time for operations within a single transaction
    start_time = time.time()
    with db_connection.transaction():
        for i in range(100):
            account1.balance -= 1.00
            account1.save()
            account2.balance += 1.00
            account2.save()
    transaction_time = time.time() - start_time
    
    # Verify the transaction approach is more efficient
    # This might not always be true for in-memory SQLite
    print(f"No transaction time: {no_transaction_time}")
    print(f"Transaction time: {transaction_time}")
```

## Best Practices for Transaction Testing

1. **Test Commit and Rollback**: Always test both successful commits and rollbacks due to errors.

2. **Test Isolation Levels**: If your application uses specific isolation levels, test that they behave as expected.

3. **Test Nested Transactions**: If your application uses nested transactions, test their behavior thoroughly.

4. **Test Concurrent Access**: Use multiple threads or processes to test how transactions handle concurrent access.

5. **Test Error Recovery**: Ensure your application can recover gracefully from transaction errors.

6. **Test Performance**: Measure the performance impact of transactions, especially for bulk operations.

7. **Test Real-World Scenarios**: Create tests that simulate real-world transaction scenarios in your application.

8. **Use Database-Specific Tests**: Some transaction features are database-specific, so create tests for your specific database.

9. **Test Transaction Boundaries**: Ensure transaction boundaries are correctly defined in your application code.

10. **Test Long-Running Transactions**: If your application uses long-running transactions, test their impact on database resources.