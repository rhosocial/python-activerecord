"""
Events Chapter: Example 1 - Lifecycle Hooks
Demonstrates core concepts:
1. Registering event listeners via on() method
2. before_save, after_save hooks
3. before_delete, after_delete hooks
4. Distinguishing new vs existing records
"""

from datetime import datetime
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
        # Register event listeners
        self.on(ModelEvent.BEFORE_SAVE, self._before_save_handler)
        self.on(ModelEvent.AFTER_SAVE, self._after_save_handler)
        self.on(ModelEvent.BEFORE_DELETE, self._before_delete_handler)
        self.on(ModelEvent.AFTER_DELETE, self._after_delete_handler)

    def _before_save_handler(self, instance, is_new: bool = False, **kwargs):
        """Called before INSERT/UPDATE."""
        now = datetime.now()
        if is_new:
            print(f"  [Hook] before_save: Creating new user '{self.username}'")
            self.created_at = now
        else:
            print(f"  [Hook] before_save: Updating existing user '{self.username}'")
        self.updated_at = now

    def _after_save_handler(self, instance, is_new: bool = False, result=None, **kwargs):
        """Called after INSERT/UPDATE."""
        if is_new:
            print(f"  [Hook] after_save: User '{self.username}' created with id={self.id}")
        else:
            print(f"  [Hook] after_save: User '{self.username}' updated")

    def _before_delete_handler(self, instance, **kwargs):
        """Called before DELETE."""
        print(f"  [Hook] before_delete: About to delete user '{self.username}'")

    def _after_delete_handler(self, instance, result=None, **kwargs):
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

    # 1. Create a new user (triggers before_save -> after_save)
    print("\n" + "-" * 40)
    print("Creating a new user:")
    print("-" * 40)
    user = User(username="alice", email="alice@example.com")
    user.save()
    print(f"\nResult: id={user.id}, created_at={user.created_at}")

    # 2. Update existing user
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
            self.on(ModelEvent.BEFORE_SAVE, self._validate_username)

        def _validate_username(self, instance, is_new: bool = False, **kwargs):
            # Example: Reject certain usernames
            if self.username.lower() == "admin":
                raise ValueError("Username 'admin' is reserved")
            print(f"  [Hook] before_save: Username '{self.username}' validated")

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
        print("  Save operation was aborted by before_save hook")

    # Valid user should work
    print("\n  Creating a valid user:")
    valid_user = StrictUser(username="john", email="john@example.com")
    valid_user.save()
    print(f"  Successfully created user with id={valid_user.id}")

if __name__ == "__main__":
    main()
