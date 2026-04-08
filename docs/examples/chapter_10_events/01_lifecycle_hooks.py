"""
Events Chapter: Example 1 - Lifecycle Hooks
Demonstrates core concepts:
1. Registering event listeners via on() method
2. BEFORE_INSERT, AFTER_INSERT hooks for new records
3. BEFORE_UPDATE, AFTER_UPDATE hooks for existing records
4. before_delete, after_delete hooks
"""

from datetime import datetime, timezone
from typing import Optional
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.interface.base import ModelEvent
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

# --- Models with Lifecycle Hooks ---

class User(ActiveRecord):
    """User model with lifecycle hooks for auditing."""
    __table_name__ = "users"
    id: Optional[int] = None
    username: str
    email: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __init__(self, **data):
        super().__init__(**data)
        # Register event listeners for INSERT and UPDATE separately
        self.on(ModelEvent.BEFORE_INSERT, self._before_insert_handler)
        self.on(ModelEvent.AFTER_INSERT, self._after_insert_handler)
        self.on(ModelEvent.BEFORE_UPDATE, self._before_update_handler)
        self.on(ModelEvent.AFTER_UPDATE, self._after_update_handler)
        self.on(ModelEvent.BEFORE_DELETE, self._before_delete_handler)
        self.on(ModelEvent.AFTER_DELETE, self._after_delete_handler)

    def _before_insert_handler(self, instance, data, **kwargs):
        """Called before INSERT for new records."""
        now = datetime.now(timezone.utc)
        print(f"  [Hook] before_insert: Creating new user '{self.username}'")
        self.created_at = now
        self.updated_at = now
        # Also update data dict to ensure values are saved
        data['created_at'] = now
        data['updated_at'] = now

    def _after_insert_handler(self, instance, data, result, **kwargs):
        """Called after INSERT for new records."""
        print(f"  [Hook] after_insert: User '{self.username}' created with id={self.id}")

    def _before_update_handler(self, instance, data, dirty_fields, **kwargs):
        """Called before UPDATE for existing records."""
        print(f"  [Hook] before_update: Updating user '{self.username}'")
        print(f"           Changed fields: {dirty_fields}")
        now = datetime.now(timezone.utc)
        self.updated_at = now
        data['updated_at'] = now

    def _after_update_handler(self, instance, data, dirty_fields, result, **kwargs):
        """Called after UPDATE for existing records."""
        print(f"  [Hook] after_update: User '{self.username}' updated")
        print(f"           Affected rows: {result.affected_rows}")

    def _before_delete_handler(self, instance, **kwargs):
        """Called before DELETE."""
        print(f"  [Hook] before_delete: About to delete user '{self.username}'")

    def _after_delete_handler(self, instance, result, **kwargs):
        """Called after DELETE."""
        print(f"  [Hook] after_delete: User '{self.username}' deleted")

# --- Main Execution ---

def main():
    print("=" * 60)
    print("Example 1: Lifecycle Hooks")
    print("=" * 60)

    # Configure database
    config = SQLiteConnectionConfig(database=':memory:')
    User.configure(config, SQLiteBackend)

    # Create table
    backend = User.backend()
    backend.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50),
            email VARCHAR(100),
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    """, options=ExecutionOptions(stmt_type=StatementType.DDL))

    # 1. Create a new user (triggers before_insert -> after_insert)
    print("\n" + "-" * 40)
    print("Creating a new user:")
    print("-" * 40)
    user = User(username="alice", email="alice@example.com")
    user.save()
    print(f"\nResult: id={user.id}, created_at={user.created_at}")

    # 2. Update existing user (triggers before_update -> after_update)
    print("\n" + "-" * 40)
    print("Updating the user:")
    print("-" * 40)
    user.email = "alice.new@example.com"
    user.save()
    print(f"\nResult: updated_at={user.updated_at}")

    # 3. Delete user
    print("\n" + "-" * 40)
    print("Deleting the user:")
    print("-" * 40)
    user.delete()

    # 4. Exception handling in hooks
    print("\n" + "-" * 40)
    print("Exception handling example:")
    print("-" * 40)

    class StrictUser(ActiveRecord):
        """User with validation that can raise exceptions."""
        __table_name__ = "strict_users"
        id: Optional[int] = None
        username: str
        email: str

        def __init__(self, **data):
            super().__init__(**data)
            self.on(ModelEvent.BEFORE_INSERT, self._validate_username)

        def _validate_username(self, instance, data, **kwargs):
            # Example: Reject certain usernames
            if self.username.lower() == "admin":
                raise ValueError("Username 'admin' is reserved")
            print(f"  [Hook] before_insert: Username '{self.username}' validated")

    # Use the same database connection for StrictUser
    StrictUser.configure(config, SQLiteBackend)

    # Create table using StrictUser's backend
    strict_backend = StrictUser.backend()
    strict_backend.execute("""
        CREATE TABLE strict_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50),
            email VARCHAR(100)
        )
    """, options=ExecutionOptions(stmt_type=StatementType.DDL))

    try:
        admin = StrictUser(username="admin", email="admin@example.com")
        admin.save()
    except ValueError as e:
        print(f"  [Error] {e}")
        print("  Save operation was aborted by before_insert hook")

    # Valid user should work
    print("\n  Creating a valid user:")
    valid_user = StrictUser(username="john", email="john@example.com")
    valid_user.save()
    print(f"  Successfully created user with id={valid_user.id}")

if __name__ == "__main__":
    main()