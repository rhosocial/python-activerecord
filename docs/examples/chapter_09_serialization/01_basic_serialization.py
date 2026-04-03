"""
Serialization Chapter: Example 1 - Basic Serialization
Demonstrates core concepts:
1. model_dump() - convert to dictionary
2. model_dump_json() - convert to JSON string
3. Handling different field types
4. JSON encoding of special types
"""

from datetime import datetime
from typing import Optional
from decimal import Decimal
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
import json

# --- Models ---

class Product(ActiveRecord):
    """Product model with various field types."""
    __table_name__ = "products"
    id: Optional[int] = None
    name: str
    price: Decimal
    quantity: int
    is_available: bool
    created_at: Optional[datetime] = None
    metadata: Optional[dict] = None


class User(ActiveRecord):
    """User model for serialization examples."""
    __table_name__ = "users"
    id: Optional[int] = None
    username: str
    email: str
    balance: Decimal
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

# --- Main Execution ---

def main():
    print("=" * 60)
    print("Example 1: Basic Serialization")
    print("=" * 60)

    # Configure database
    config = SQLiteConnectionConfig(database=':memory:')
    Product.configure(config, SQLiteBackend)
    User.configure(config, SQLiteBackend)

    # Create tables
    backend = Product.backend()
    backend.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100),
            price DECIMAL(10, 2),
            quantity INTEGER,
            is_available BOOLEAN,
            created_at TIMESTAMP,
            metadata TEXT
        )
    """, options=ExecutionOptions(stmt_type=StatementType.DDL))

    # Create users table using User's backend
    user_backend = User.backend()
    user_backend.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50),
            email VARCHAR(100),
            balance DECIMAL(10, 2),
            created_at TIMESTAMP,
            last_login TIMESTAMP
        )
    """, options=ExecutionOptions(stmt_type=StatementType.DDL))

    # 1. Basic model_dump()
    print("\n" + "-" * 40)
    print("model_dump() - Dictionary output:")
    print("-" * 40)

    product = Product(
        name="Widget",
        price=Decimal("19.99"),
        quantity=100,
        is_available=True,
        created_at=datetime.now(),
        metadata={"color": "blue", "weight": "1.5kg"}
    )
    product.save()

    data = product.model_dump()
    print(f"Type: {type(data)}")
    print(f"Content: {json.dumps(data, indent=2, default=str)}")

    # 2. model_dump_json()
    print("\n" + "-" * 40)
    print("model_dump_json() - JSON string output:")
    print("-" * 40)

    json_str = product.model_dump_json()
    print(f"Type: {type(json_str)}")
    print(f"Content: {json_str}")

    # Parse to verify it's valid JSON
    parsed = json.loads(json_str)
    print(f"Parsed back: {parsed['name']} - ${parsed['price']}")

    # 3. Different field types
    print("\n" + "-" * 40)
    print("Different field types serialization:")
    print("-" * 40)

    user = User(
        username="alice",
        email="alice@example.com",
        balance=Decimal("1250.50"),
        created_at=datetime(2024, 1, 15, 10, 30, 0),
        last_login=datetime.now()
    )
    user.save()

    user_data = user.model_dump()
    print(f"String field: {user_data['username']}")
    print(f"Decimal field: {user_data['balance']} (type: {type(user_data['balance'])})")
    print(f"Datetime field: {user_data['created_at']} (type: {type(user_data['created_at'])})")
    print(f"None field: {user_data.get('last_login')}")

    # 4. JSON encoding options
    print("\n" + "-" * 40)
    print("JSON encoding with mode option:")
    print("-" * 40)

    # 'python' mode returns Python objects (default)
    python_data = user.model_dump(mode='python')
    print(f"Python mode - balance type: {type(python_data['balance'])}")

    # 'json' mode returns JSON-serializable types
    json_data = user.model_dump(mode='json')
    print(f"JSON mode - balance type: {type(json_data['balance'])}")
    print(f"JSON mode - created_at: {json_data['created_at']}")

    # 5. Round-trip serialization
    print("\n" + "-" * 40)
    print("Round-trip serialization:")
    print("-" * 40)

    # Serialize
    json_output = user.model_dump_json()
    print(f"Serialized: {json_output[:100]}...")

    # Deserialize back to model
    user_copy = User.model_validate_json(json_output)
    print(f"Deserialized: {user_copy.username}, balance={user_copy.balance}")

if __name__ == "__main__":
    main()
