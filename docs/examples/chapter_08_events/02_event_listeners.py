"""
Events Chapter: Example 2 - Event Listeners
Demonstrates core concepts:
1. Using on() method to register event listeners
2. Multiple listeners for the same event
3. Dynamic listener registration and removal
4. Using ModelEvent enum
"""

from datetime import datetime
from typing import Optional
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.interface.base import ModelEvent
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

# --- Models ---

class User(ActiveRecord):
    """User model demonstrating event listener pattern."""
    __table_name__ = "users"
    id: Optional[int] = None
    username: str
    email: str
    password_hash: Optional[str] = None
    created_at: Optional[datetime] = None

    # Temporary storage for plain password (not saved to DB)
    _plain_password: Optional[str] = None

    def set_password(self, password: str):
        """Set plain password to be hashed before save."""
        self._plain_password = password

    def __init__(self, **data):
        super().__init__(**data)
        # Register event listeners in __init__
        self.on(ModelEvent.BEFORE_SAVE, self._hash_password)
        self.on(ModelEvent.BEFORE_SAVE, self._set_timestamp)
        self.on(ModelEvent.AFTER_SAVE, self._log_save)

    def _hash_password(self, instance, is_new=False, **kwargs):
        """Hash password before saving."""
        if self._plain_password and not self.password_hash:
            # Simulate password hashing
            self.password_hash = f"hashed_{self._plain_password}"
            self._plain_password = None  # Clear plain password
            print(f"  [Listener] Password hashed for '{self.username}'")

    def _set_timestamp(self, instance, is_new=False, **kwargs):
        """Set creation timestamp."""
        if is_new:
            self.created_at = datetime.now()
            print(f"  [Listener] Timestamp set for '{self.username}'")

    def _log_save(self, instance, is_new=False, result=None, **kwargs):
        """Log save operation."""
        action = "created" if is_new else "updated"
        print(f"  [Listener] User '{self.username}' {action} successfully")


class AuditedModel(ActiveRecord):
    """Base model with audit logging via event listeners."""

    def __init__(self, **data):
        super().__init__(**data)
        self.on(ModelEvent.AFTER_SAVE, self._audit_save)
        self.on(ModelEvent.AFTER_DELETE, self._audit_delete)

    def _audit_save(self, instance, is_new=False, result=None, **kwargs):
        """Audit log for save operations."""
        action = "CREATE" if is_new else "UPDATE"
        print(f"  [Audit] {action}: {self.__class__.__name__} id={self.id}")

    def _audit_delete(self, instance, result=None, **kwargs):
        """Audit log for delete operations."""
        print(f"  [Audit] DELETE: {self.__class__.__name__} id={self.id}")


class Product(AuditedModel):
    """Product model inheriting audit functionality."""
    __table_name__ = "products"
    id: Optional[int] = None
    name: str
    price: float

# --- Main Execution ---

def main():
    print("=" * 60)
    print("Example 2: Event Listeners")
    print("=" * 60)

    # Configure database
    config = SQLiteConnectionConfig(database=':memory:')
    User.configure(config, SQLiteBackend)

    # Create tables
    backend = User.backend()
    backend.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50),
            email VARCHAR(100),
            password_hash VARCHAR(100),
            created_at TIMESTAMP
        )
    """, options=ExecutionOptions(stmt_type=StatementType.DDL))

    # 1. Multiple listeners on same event
    print("\n" + "-" * 40)
    print("Multiple listeners (BEFORE_SAVE):")
    print("-" * 40)
    user = User(username="alice", email="alice@example.com")
    user.set_password("secret123")
    user.save()
    print(f"\nResult: password_hash={user.password_hash}")

    # 2. Inherited event listeners
    print("\n" + "-" * 40)
    print("Inherited listeners (AuditedModel):")
    print("-" * 40)
    Product.configure(config, SQLiteBackend)

    # Create table using Product's backend
    product_backend = Product.backend()
    product_backend.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100),
            price REAL
        )
    """, options=ExecutionOptions(stmt_type=StatementType.DDL))

    product = Product(name="Widget", price=19.99)
    product.save()

    product.price = 24.99
    product.save()

    product.delete()

    # 3. Dynamic listener management
    print("\n" + "-" * 40)
    print("Dynamic listener management:")
    print("-" * 40)

    def temporary_listener(instance, **kwargs):
        print("  [Temporary] This listener does something special")

    # Add temporary listener
    user2 = User(username="bob", email="bob@example.com")
    user2.set_password("pass456")
    user2.on(ModelEvent.BEFORE_SAVE, temporary_listener)
    print("Saving with temporary listener:")
    user2.save()

    # The temporary listener only affects this instance
    user3 = User(username="charlie", email="charlie@example.com")
    user3.set_password("pass789")
    print("\nSaving another instance (no temporary listener):")
    user3.save()

if __name__ == "__main__":
    main()
