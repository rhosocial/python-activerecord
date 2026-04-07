"""
Serialization Chapter: Example 2 - Field Filtering
Demonstrates core concepts:
1. exclude - exclude specific fields
2. include - include only specific fields
3. Nested field filtering
4. Dynamic field exclusion based on context
"""

from datetime import datetime
from typing import Optional
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
import json

# --- Models ---

class User(ActiveRecord):
    """User model with sensitive fields."""
    __table_name__ = "users"
    id: Optional[int] = None
    username: str
    email: str
    password_hash: Optional[str] = None
    api_key: Optional[str] = None
    is_admin: bool = False
    created_at: Optional[datetime] = None


class Profile(ActiveRecord):
    """Profile model with nested structure."""
    __table_name__ = "profiles"
    id: Optional[int] = None
    user_id: int
    bio: str
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[dict] = None
    settings: Optional[dict] = None

# --- Helper Functions ---

def print_json(data: dict, title: str = ""):
    """Pretty print JSON data."""
    if title:
        print(f"\n{title}:")
    print(json.dumps(data, indent=2, default=str))

# --- Main Execution ---

def main():
    print("=" * 60)
    print("Example 2: Field Filtering")
    print("=" * 60)

    # Configure database
    config = SQLiteConnectionConfig(database=':memory:')
    User.configure(config, SQLiteBackend)
    Profile.configure(config, SQLiteBackend)

    # Create tables
    backend = User.backend()
    backend.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50),
            email VARCHAR(100),
            password_hash VARCHAR(100),
            api_key VARCHAR(100),
            is_admin BOOLEAN,
            created_at TIMESTAMP
        )
    """, options=ExecutionOptions(stmt_type=StatementType.DDL))

    # Create profiles table using Profile's backend
    profile_backend = Profile.backend()
    profile_backend.execute("""
        CREATE TABLE profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            bio TEXT,
            avatar_url VARCHAR(200),
            phone VARCHAR(20),
            address TEXT,
            settings TEXT
        )
    """, options=ExecutionOptions(stmt_type=StatementType.DDL))

    # Create test data
    user = User(
        username="alice",
        email="alice@example.com",
        password_hash="hashed_secret_123",
        api_key="sk-abc123xyz",
        is_admin=True,
        created_at=datetime.now()
    )
    user.save()

    profile = Profile(
        user_id=user.id,
        bio="Software developer",
        avatar_url="https://example.com/avatar.jpg",
        phone="+1-555-1234",
        address={"street": "123 Main St", "city": "NYC", "zip": "10001"},
        settings={"theme": "dark", "notifications": True}
    )
    profile.save()

    # 1. Exclude sensitive fields
    print("\n" + "-" * 40)
    print("Excluding sensitive fields:")
    print("-" * 40)

    # Full data (includes sensitive fields)
    full_data = user.model_dump()
    print(f"Full data includes password_hash: {'password_hash' in full_data}")
    print(f"Full data includes api_key: {'api_key' in full_data}")

    # Exclude sensitive fields
    safe_data = user.model_dump(exclude={'password_hash', 'api_key'})
    print(f"\nSafe data excludes password_hash: {'password_hash' not in safe_data}")
    print(f"Safe data excludes api_key: {'api_key' not in safe_data}")
    print_json(safe_data, "Safe output")

    # 2. Include only specific fields
    print("\n" + "-" * 40)
    print("Including only specific fields:")
    print("-" * 40)

    public_profile = user.model_dump(include={'id', 'username', 'created_at'})
    print_json(public_profile, "Public profile")

    # 3. Nested field filtering
    print("\n" + "-" * 40)
    print("Nested field filtering:")
    print("-" * 40)

    # Full profile data
    print_json(profile.model_dump(), "Full profile")

    # Exclude nested fields (address.zip, settings.notifications)
    filtered_profile = profile.model_dump(
        exclude={
            'address': {'zip'},
            'settings': {'notifications'}
        }
    )
    print_json(filtered_profile, "Filtered nested fields")

    # Include only specific nested fields
    minimal_address = profile.model_dump(
        include={
            'id': True,
            'user_id': True,
            'address': {'city': True}
        }
    )
    print_json(minimal_address, "Minimal with nested include")

    # 4. Context-aware serialization
    print("\n" + "-" * 40)
    print("Context-aware serialization:")
    print("-" * 40)

    def serialize_for_admin(user: User) -> dict:
        """Serialize with all fields for admin view."""
        return user.model_dump()

    def serialize_for_public(user: User) -> dict:
        """Serialize with sensitive fields excluded for public view."""
        return user.model_dump(exclude={'password_hash', 'api_key', 'is_admin'})

    def serialize_for_api(user: User) -> dict:
        """Serialize for API responses."""
        return user.model_dump(
            include={'id', 'username', 'email', 'created_at'}
        )

    print("Admin view:")
    print(f"  Fields: {list(serialize_for_admin(user).keys())}")

    print("\nPublic view:")
    print(f"  Fields: {list(serialize_for_public(user).keys())}")

    print("\nAPI response:")
    print(f"  Fields: {list(serialize_for_api(user).keys())}")

    # 5. Using exclude_unset
    print("\n" + "-" * 40)
    print("exclude_unset - only changed fields:")
    print("-" * 40)

    new_user = User(username="bob", email="bob@example.com")
    # Note: password_hash, api_key, is_admin, created_at are not set

    # This shows only fields that were explicitly set
    set_fields = new_user.model_dump(exclude_unset=True)
    print(f"Set fields: {set_fields}")

if __name__ == "__main__":
    main()
