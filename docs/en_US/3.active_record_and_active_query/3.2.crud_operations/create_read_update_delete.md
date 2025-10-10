# Create, Read, Update, Delete Operations

This document covers the basic CRUD (Create, Read, Update, Delete) operations in rhosocial ActiveRecord. These operations form the foundation of database interactions in your applications.

## Creating Records

rhosocial ActiveRecord provides several methods for creating new records:

### Method 1: Instantiate and Save

The most common method is to create an instance of your model and then call the `save()` method:

```python
# Create a new user
user = User(username="johndoe", email="john@example.com", age=30)
user.save()  # Insert the record into the database

# The primary key is automatically set after saving
print(user.id)  # Outputs the new ID
```

### Method 2: Create from Dictionary

You can also create model instances from attribute dictionaries:

```python
user_data = {
    "username": "janedoe",
    "email": "jane@example.com",
    "age": 28
}
user = User(**user_data)
user.save()
```

### Validation During Creation

When you save a record, validations are automatically performed. If validation fails, a `DBValidationError` exception is raised:

```python
try:
    user = User(username="a", email="invalid-email")
    user.save()
except DBValidationError as e:
    print(f"Validation failed: {e}")
```

### Lifecycle Events

During the creation process, several events are triggered that you can hook into:

- `BEFORE_VALIDATE`: Triggered before validation is performed
- `AFTER_VALIDATE`: Triggered after validation succeeds
- `BEFORE_SAVE`: Triggered before the save operation
- `AFTER_SAVE`: Triggered after the save operation
- `AFTER_INSERT`: Triggered after a new record is inserted

## Reading Records

rhosocial ActiveRecord provides various methods for querying records:

### Finding by Primary Key

The most common query is finding a single record by its primary key:

```python
# Find a user by ID
user = User.find_one(1)  # Returns the user with ID 1 or None

# Throw an exception if the record doesn't exist
try:
    user = User.find_one_or_fail(999)  # Throws RecordNotFound if user with ID 999 doesn't exist
except RecordNotFound:
    print("User doesn't exist")
```

### Querying with Conditions

You can use conditions to find records:

```python
# Find a single record by primary key
user = User.find_one(1)  # Query by primary key

# Find all records
all_users = User.find_all()
```

### Advanced Queries with ActiveQuery

For more complex queries, you can use ActiveQuery:

```python
# Find active users older than 25, ordered by creation date
users = User.query()\
    .where("status = ?", ("active",))\
    .where("age > ?", (25,))\
    .order_by("created_at DESC")\
    .all()
```

### Using OR Conditions

When you need to connect multiple conditions with OR logic, you can use the `or_where` method:

```python
# Find users with active or VIP status
users = User.query()\
    .where("status = ?", ("active",))\
    .or_where("status = ?", ("vip",))\
    .all()
# Equivalent to: SELECT * FROM users WHERE status = 'active' OR status = 'vip'

# Combining AND and OR conditions
users = User.query()\
    .where("status = ?", ("active",))\
    .where("age > ?", (25,))\
    .or_where("vip_level > ?", (0,))\
    .all()
# Equivalent to: SELECT * FROM users WHERE (status = 'active' AND age > 25) OR vip_level > 0
```

You can also use condition groups to create more complex logical combinations:

```python
# Using condition groups for complex queries
users = User.query()\
    .where("status = ?", ("active",))\
    .start_or_group()\
    .where("age > ?", (25,))\
    .or_where("vip_level > ?", (0,))\
    .end_or_group()\
    .all()
# Equivalent to: SELECT * FROM users WHERE status = 'active' AND (age > 25 OR vip_level > 0)
```

> **Note**: Query conditions must use SQL expressions and parameter placeholders. Dictionary input is not supported. Parameter values must be passed as tuples, even for single values: `(value,)`.

## Updating Records

### Updating a Single Record

To update an existing record, first retrieve the record, modify its attributes, then save:

```python
# Find and update a user
user = User.find_one(1)
if user:
    user.email = "newemail@example.com"
    user.age += 1
    user.save()  # Update the record in the database
```

### Batch Updates

> **❌ NOT IMPLEMENTED**: Batch update functionality is not implemented. This is planned functionality and is provided for future reference only. Current users should update records individually. This feature may be developed in future releases with no guaranteed timeline.

Theoretically, batch updates would allow you to update multiple records at once using the query builder:

```python
# Update all inactive users to archived status (example code, currently unavailable)
affected_rows = User.query()\
    .where("status = ?", ("inactive",))\
    .update({"status": "archived"})

print(f"Updated {affected_rows} records")
```

### Lifecycle Events During Updates

During the update process, the following events are triggered:

- `BEFORE_VALIDATE`: Triggered before validation is performed
- `AFTER_VALIDATE`: Triggered after validation succeeds
- `BEFORE_SAVE`: Triggered before the save operation
- `AFTER_SAVE`: Triggered after the save operation
- `AFTER_UPDATE`: Triggered after an existing record is updated

## Deleting Records

### Deleting a Single Record

To delete a record, first retrieve the record, then call the `delete()` method:

```python
# Find and delete a user
user = User.find_one(1)
if user:
    affected_rows = user.delete()  # Delete the record from the database
    print(f"Deleted {affected_rows} records")
```

### Batch Deletes

For batch deletes, you can use the query builder:

```python
# Delete all inactive users
affected_rows = User.query()\
    .where({"status": "inactive"})\
    .delete()

print(f"Deleted {affected_rows} records")
```

### Soft Deletes

If your model uses the `SoftDeleteMixin`, the `delete()` method won't actually remove records from the database but mark them as deleted:

```python
# For models using SoftDeleteMixin
user = User.find_one(1)
user.delete()  # Marks as deleted, but record remains in the database

# Default queries exclude deleted records
active_users = User.find_all()  # Only returns non-deleted records

# Include deleted records
all_users = User.query().with_deleted().all()

# Query only deleted records
deleted_users = User.query().only_deleted().all()
```

> **Important**: Even after a record is deleted, the instance object still exists in memory. You can still modify its attributes and call the `save()` method to restore or update it to the database. For soft-deleted records, this will automatically restore the record; for hard-deleted records, this will create a new record with the same attributes (possibly with a new primary key).

### Lifecycle Events During Deletion

During the deletion process, the following events are triggered:

- `BEFORE_DELETE`: Triggered before the delete operation
- `AFTER_DELETE`: Triggered after the delete operation

## Refreshing Records

If you need to reload a record's latest state from the database, you can use the `refresh()` method:

```python
user = User.find_one(1)
# ... other code might have modified the record in the database ...
user.refresh()  # Reload the record from the database
```

## Checking Record Status

ActiveRecord provides several useful properties to check the status of a record:

```python
user = User.find_one(1)

# Check if it's a new record (not yet saved to the database)
if user.is_new_record:
    print("This is a new record")

# Check if the record has been modified
user.email = "changed@example.com"
if user.is_dirty:
    print("The record has been modified")
    print(f"Modified attributes: {user.dirty_attributes}")
```

## Summary

rhosocial ActiveRecord provides an intuitive and powerful API for performing CRUD operations. With these basic operations, you can easily interact with your database while leveraging lifecycle events and validations to ensure data integrity and consistency.