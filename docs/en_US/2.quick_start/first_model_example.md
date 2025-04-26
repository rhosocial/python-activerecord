# First Model Example

This guide walks you through creating your first ActiveRecord model and performing basic database operations.

## Defining Your First Model

In rhosocial ActiveRecord, models are Python classes that inherit from `ActiveRecord` and define the structure of your database tables.

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend.typing import ConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from datetime import datetime
from typing import Optional

# Define a User model
class User(ActiveRecord):
    __table_name__ = 'users'  # Specify the table name
    
    # Define fields with type annotations
    id: int                   # Primary key
    name: str                 # User's name
    email: str                # User's email
    created_at: datetime      # Creation timestamp
    updated_at: Optional[datetime] = None  # Last update timestamp

# Configure the database connection
User.configure(
    ConnectionConfig(database='database.sqlite3'),
    backend_class=SQLiteBackend
)
```

### Key Components of a Model

- **Class Inheritance**: Your model inherits from `ActiveRecord`
- **Table Name**: The `__table_name__` attribute specifies the database table name
- **Fields**: Defined using Python type annotations

## Working with Database Tables

rhosocial ActiveRecord works with existing database tables that match your model definitions. Currently, the framework does not support migration capabilities, so you'll need to create your database tables using SQL or other database management tools before using your models.

## Basic CRUD Operations

Now that you have a model and table, you can perform Create, Read, Update, and Delete operations.

### Creating Records

```python
# Create a new user
user = User(
    name='John Doe',
    email='john@example.com',
    created_at=datetime.now()
    # Note: Do NOT specify the auto-increment primary key (id)
    # The database will generate it automatically
)

# Save the user to the database
user.save()

# The ID is automatically set after saving, and the model instance is refreshed
print(f"User created with ID: {user.id}")
```

### Reading Records

```python
# Find a user by primary key
user = User.find_one(1)
if user:
    print(f"Found user: {user.name}")

# Query all users
# Note: This is equivalent to Query.find_all() and will return ALL records without filtering
# Use with caution for large datasets as it may cause performance issues
all_users = User.query().all()
for user in all_users:
    print(f"User: {user.name}, Email: {user.email}")

# Query with conditions
# Note: It's best to use conditions that match indexes for better performance
# String searches like LIKE may be slow without proper indexing
john_users = User.query().where("name LIKE ?", "%John%").all()
for user in john_users:
    print(f"Found John: {user.name}")
```

### Updating Records

```python
# Find and update a user
user = User.find_one(1)
if user:
    user.name = "Jane Doe"  # Update the name
    user.updated_at = datetime.now()  # Update the timestamp
    user.save()  # Save changes to the database
    print(f"User updated: {user.name}")
```

### Deleting Records

```python
# Find and delete a user
user = User.find_one(1)
if user:
    user.delete()  # Delete from the database
    print("User deleted")
    
    # Note: After deletion, the instance still exists in memory
    # It becomes a new record state, with cleared attributes
    # You can save it again as a new record with a different ID
    user.name = "New User After Deletion"
    user.save()  # This will create a new record with a new ID
    print(f"New user created after deletion with ID: {user.id}")
```

> **Important**: When you delete a record using the `delete()` method, only the database record is removed. The instance object still exists in memory and becomes a new record state. You can modify its attributes and call `save()` to create a new record in the database, which will receive a new auto-increment primary key value.

## Using the Query Builder

rhosocial ActiveRecord includes a powerful query builder for more complex queries:

```python
# Complex query example
recent_users = User.query()\
    .where("created_at > ?", datetime.now() - timedelta(days=7))\
    .order_by("created_at DESC")\
    .limit(10)\
    .all()

print(f"Found {len(recent_users)} recent users")

# Count query
user_count = User.query().count()
print(f"Total users: {user_count}")

# Conditional query with parameterized query for SQL injection protection
young_users = User.query().where('age < ?', (22,)).all()
print(f"Found {len(young_users)} young users")
```

> **Important Security Note**: Always use parameterized queries with placeholder (`?`) for all user inputs to prevent SQL injection attacks. Pass the actual values as a tuple in the second argument of the `where()` method. Never directly concatenate user input into SQL strings. This is critical for security unless you can guarantee that end users have no access to the original query statements.

## Transactions

For operations that need to be atomic, use transactions:

```python
# Start a transaction
with User.transaction():
    # Create multiple users in a single transaction
    for i in range(5):
        user = User(
            name=f"User {i}",
            email=f"user{i}@example.com",
            created_at=datetime.now()
        )
        user.save()
    # If any operation fails, all changes are rolled back
```

## Complete Example

Here's a complete example that demonstrates the full lifecycle of a model:

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend.typing import ConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from datetime import datetime
from typing import Optional

# Define the model
class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    name: str
    email: str
    created_at: datetime
    updated_at: Optional[datetime] = None

# Configure the database
User.configure(
    ConnectionConfig(database='example.sqlite3'),
    backend_class=SQLiteBackend
)

# Create a user
user = User(
    name='John Doe',
    email='john@example.com',
    created_at=datetime.now()
)
user.save()
print(f"Created user with ID: {user.id}")

# Find and update the user
found_user = User.find_one(user.id)
if found_user:
    found_user.name = "Jane Doe"
    found_user.updated_at = datetime.now()
    found_user.save()
    print(f"Updated user name to: {found_user.name}")

# Query all users
all_users = User.query().all()
print(f"Total users: {len(all_users)}")
for u in all_users:
    print(f"User {u.id}: {u.name}, {u.email}, Created: {u.created_at}")

# Delete the user
found_user.delete()
print("User deleted")

# Verify deletion
remaining = User.query().count()
print(f"Remaining users: {remaining}")
```

## Next Steps

Now that you've created your first model and performed basic operations, check out the [Frequently Asked Questions](faq.md) for common issues and solutions, or explore the more advanced topics in the documentation.