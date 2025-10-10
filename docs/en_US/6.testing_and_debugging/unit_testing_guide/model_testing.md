# Model Testing

Model testing in rhosocial ActiveRecord currently focuses on basic model functionality and simple validation checks.

## Basic Model Testing

Current testing capabilities include:

- Testing model attribute assignment and retrieval
- Basic validation through Pydantic's validation system
- Simple CRUD operation verification

## Setting Up Model Tests

Basic approach for testing models:

1. Create model instances with test data
2. Verify attribute values
3. Test save and delete operations
4. Verify basic validation rules

## Example Model Test

```python
import unittest
from rhosocial.activerecord import ActiveRecord

class User(ActiveRecord):
    name: str
    email: str

class TestUserModel(unittest.TestCase):
    def test_attribute_assignment(self):
        user = User(name="John", email="john@example.com")
        self.assertEqual(user.name, "John")
        self.assertEqual(user.email, "john@example.com")
    
    def test_model_persistence(self):
        user = User(name="Jane", email="jane@example.com")
        result = user.save()
        self.assertIsNotNone(user.id)  # Assuming successful save assigns an ID
```

## Current Limitations

The current model testing approach is limited to basic functionality. Advanced testing features such as relationship validation, complex query testing, and transaction verification are not currently available in the testing framework.

## Setting Up Test Environment

### Test Database Configuration

For model testing, it's important to use a dedicated test database:

```python
# Example test database configuration
from rhosocial.activerecord.backend import SQLiteBackend

test_db = SQLiteBackend(":memory:")  # Use in-memory SQLite for tests
```

Using an in-memory SQLite database for tests offers several advantages:
- Tests run faster without disk I/O
- Each test starts with a clean database state
- No need to clean up after tests

### Test Fixtures

Fixtures provide a consistent set of test data. rhosocial ActiveRecord works well with pytest fixtures:

```python
import pytest
from rhosocial.activerecord.backend import SQLiteBackend
from your_app.models import User

@pytest.fixture
def db_connection():
    """Create a test database connection."""
    connection = SQLiteBackend(":memory:")
    # Create necessary tables
    User.create_table(connection)
    yield connection
    # No cleanup needed for in-memory database

@pytest.fixture
def user_fixture(db_connection):
    """Create a test user."""
    user = User(
        username="test_user",
        email="test@example.com",
        age=30
    )
    user.save()
    return user
```

## Testing Model Validation

Validation rules ensure data integrity. Test both valid and invalid scenarios:

```python
def test_user_validation(db_connection):
    """Test user model validation rules."""
    # Test valid user
    valid_user = User(
        username="valid_user",
        email="valid@example.com",
        age=25
    )
    assert valid_user.validate() == True
    
    # Test invalid user (missing required field)
    invalid_user = User(
        username="",  # Empty username
        email="invalid@example.com",
        age=25
    )
    assert invalid_user.validate() == False
    assert "username" in invalid_user.errors
    
    # Test invalid email format
    invalid_email_user = User(
        username="user2",
        email="not-an-email",  # Invalid email format
        age=25
    )
    assert invalid_email_user.validate() == False
    assert "email" in invalid_email_user.errors
```

## Testing Model Persistence

Test saving, updating, and deleting models:

```python
def test_user_persistence(db_connection):
    """Test user model persistence operations."""
    # Test creating a user
    user = User(
        username="persistence_test",
        email="persist@example.com",
        age=35
    )
    assert user.is_new_record == True
    assert user.save() == True
    assert user.is_new_record == False
    assert user.id is not None
    
    # Test updating a user
    user.username = "updated_username"
    assert user.save() == True
    
    # Verify update by reloading
    reloaded_user = User.find_by_id(user.id)
    assert reloaded_user.username == "updated_username"
    
    # Test deleting a user
    assert user.delete() == True
    assert User.find_by_id(user.id) is None
```

## Testing Model Queries

Test various query methods to ensure they return the expected results:

```python
def test_user_queries(db_connection):
    """Test user model query methods."""
    # Create test data
    User(username="user1", email="user1@example.com", age=20).save()
    User(username="user2", email="user2@example.com", age=30).save()
    User(username="user3", email="user3@example.com", age=40).save()
    
    # Test find_by_id
    user = User.find_by_id(1)
    assert user is not None
    assert user.username == "user1"
    
    # Test find_by
    user = User.find_by(username="user2")
    assert user is not None
    assert user.email == "user2@example.com"
    
    # Test where clause
    users = User.where("age > ?", [25]).all()
    assert len(users) == 2
    assert users[0].username in ["user2", "user3"]
    assert users[1].username in ["user2", "user3"]
    
    # Test order
    users = User.order("age DESC").all()
    assert len(users) == 3
    assert users[0].username == "user3"
    assert users[2].username == "user1"
    
    # Test limit and offset
    users = User.order("age ASC").limit(1).offset(1).all()
    assert len(users) == 1
    assert users[0].username == "user2"
```

## Testing Custom Model Methods

Test any custom methods you've added to your models:

```python
def test_custom_user_methods(db_connection, user_fixture):
    """Test custom user model methods."""
    # Assuming User has a custom method full_name
    user_fixture.first_name = "John"
    user_fixture.last_name = "Doe"
    assert user_fixture.full_name() == "John Doe"
    
    # Test another custom method (e.g., is_adult)
    assert user_fixture.is_adult() == True  # age is 30 from fixture
```

## Testing Model Events

Test lifecycle hooks and event callbacks:

```python
def test_user_lifecycle_events(db_connection):
    """Test user model lifecycle events."""
    # Create a user with a callback counter
    user = User(username="event_test", email="event@example.com", age=25)
    user.before_save_called = 0
    user.after_save_called = 0
    
    # Override lifecycle methods for testing
    original_before_save = User.before_save
    original_after_save = User.after_save
    
    def test_before_save(self):
        self.before_save_called += 1
        return original_before_save(self)
        
    def test_after_save(self):
        self.after_save_called += 1
        return original_after_save(self)
    
    # Monkey patch for testing
    User.before_save = test_before_save
    User.after_save = test_after_save
    
    # Test save triggers events
    user.save()
    assert user.before_save_called == 1
    assert user.after_save_called == 1
    
    # Test update triggers events
    user.username = "updated_event_test"
    user.save()
    assert user.before_save_called == 2
    assert user.after_save_called == 2
    
    # Restore original methods
    User.before_save = original_before_save
    User.after_save = original_after_save
```

## Best Practices

1. **Isolate Tests**: Each test should be independent and not rely on the state from other tests.

2. **Use Transactions**: Wrap tests in transactions to automatically roll back changes:
   ```python
   def test_with_transaction(db_connection):
       with db_connection.transaction():
           # Test code here
           # Transaction will be rolled back automatically
   ```

3. **Test Edge Cases**: Test boundary conditions, null values, and other edge cases.

4. **Mock External Dependencies**: Use mocking to isolate model tests from external services.

5. **Test Performance**: For critical models, include performance tests to ensure queries remain efficient.

6. **Use Descriptive Test Names**: Name tests clearly to describe what they're testing and expected behavior.

7. **Keep Tests DRY**: Use fixtures and helper methods to avoid repetition in tests.

8. **Test Failure Cases**: Ensure your code handles errors gracefully by testing failure scenarios.