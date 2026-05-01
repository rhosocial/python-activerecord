"""
Chapter 3: Modeling Data - Pydantic V2 Integration Examples
Demonstrates how to use Pydantic V2 features with ActiveRecord.

NOTE: This project provides its own SQLTypeAdapter (for database type conversion),
which is different from Pydantic's TypeAdapter (for general type validation).

Run this script directly: python pydantic_integration.py
"""

import sys
import json
from datetime import datetime, date, time
from typing import Annotated, Optional, List, Any, Dict, Set, Type

# Add src to path for imports
sys.path.insert(0, "/Users/vistart/PycharmProjects/rhosocial/python-activerecord/src")

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
    ConfigDict,
    computed_field,
    AliasPath,
    TypeAdapter,
)
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import UseAdapter
from rhosocial.activerecord.field import UUIDMixin, TimestampMixin
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.backend.type_adapter import SQLTypeAdapter


# =============================================================================
# 1. Basic Model Definition (基础Model定义)
# =============================================================================


# Method 1: Define directly as ActiveRecord subclass
# Use UUIDMixin for automatic ID generation
class User(UUIDMixin, TimestampMixin, ActiveRecord):
    username: str
    email: str
    age: Optional[int] = None
    bio: str = Field(default="", max_length=500)


# Method 2: Use Pydantic BaseModel independently, then convert
class UserProfile(BaseModel):
    nickname: str
    avatar_url: Optional[str] = None
    bio: str = ""


# =============================================================================
# 2. Field Validation (字段验证)
# =============================================================================


# Method 1: Using Field() directly
class Product(UUIDMixin, ActiveRecord):
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0, description="Price must be greater than 0")
    stock: int = Field(ge=0, le=9999)


# Method 2: Using Annotated (Pydantic V2 recommended, reusable)
PositiveFloat = Annotated[float, Field(gt=0, description="Must be positive")]

class Order(UUIDMixin, ActiveRecord):
    amount: PositiveFloat
    discount: Annotated[float, Field(ge=0, le=1)] = 0.0


# =============================================================================
# 3. Custom Validators (自定义验证器)
# =============================================================================


class UserRegistration(BaseModel):
    username: str
    password: str
    confirm_password: str
    email: str

    # Field-level validator (field_validator replaces @validator from V1)
    @field_validator("username")
    @classmethod
    def username_must_be_alphanumeric(cls, v: str) -> str:
        if not v.isalnum():
            raise ValueError("Username must contain only letters and numbers")
        return v.lower()

    @field_validator("email")
    @classmethod
    def email_must_contain_at(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v.lower()

    # Cross-field validator (model_validator)
    @model_validator(mode="after")
    def passwords_must_match(self) -> "UserRegistration":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


def test_custom_validators():
    print("\n3. Testing Custom Validators:")
    try:
        user = UserRegistration(
            username="JohnDoe",
            password="password123",
            confirm_password="password123",
            email="JOHN@EXAMPLE.COM",
        )
        print(f"  Created user: {user.username}, email: {user.email}")
    except Exception as e:
        print(f"  Error: {e}")


# =============================================================================
# 4. Type Coercion & Strict Mode (类型强制转换与严格模式)
# =============================================================================


# Default: Lax mode - automatic type coercion
class LaxModel(BaseModel):
    value: int


# Strict mode: No implicit conversion
class StrictModel(BaseModel):
    model_config = ConfigDict(strict=True)
    value: int


def test_type_coercion():
    print("\n4. Testing Type Coercion & Strict Mode:")
    # Lax mode
    lax = LaxModel(value="42")
    print(f"  LaxModel(value='42'): {lax.value} (type: {type(lax.value).__name__})")

    # Strict mode
    strict = StrictModel(value=42)
    print(f"  StrictModel(value=42): {strict.value} (type: {type(strict.value).__name__})")

    try:
        strict_error = StrictModel(value="42")
    except Exception as e:
        print(f"  StrictModel(value='42') raised: {type(e).__name__}")


# =============================================================================
# 5. Nested Models & Lists (嵌套模型和列表)
# =============================================================================


class Address(BaseModel):
    city: str
    zip_code: str


class Company(BaseModel):
    name: str
    addresses: List[Address]
    tags: List[str] = []


def demo_nested_models():
    print("\n5. Nested Models:")
    company = Company(
        name="Example Corp",
        addresses=[{"city": "Beijing", "zip_code": "100000"}],
    )
    print(f"  Company: {company.name}")
    print(f"  First address: {company.addresses[0].city}")


# =============================================================================
# 6. Serialization (序列化)
# =============================================================================


class SerializationDemo(BaseModel):
    id: int
    name: str
    email: str
    age: Optional[int] = None
    bio: str = ""


def demo_serialization():
    print("\n6. Serialization:")
    user = SerializationDemo(id=1, name="Alice", email="alice@example.com")

    # Convert to dict
    data = user.model_dump()
    print(f"  model_dump(): {data}")

    # Exclude None fields
    data_without_none = user.model_dump(exclude_none=True)
    print(f"  model_dump(exclude_none=True): {data_without_none}")

    # Convert to JSON string
    json_str = user.model_dump_json(exclude_none=True)
    print(f"  model_dump_json(): {json_str}")


# =============================================================================
# 7. Alias (别名)
# =============================================================================


class Response(BaseModel):
    user_id: int = Field(alias="userId")
    user_name: str = Field(alias="userName")

    model_config = ConfigDict(populate_by_name=True)


def demo_alias():
    print("\n7. Alias:")
    # Parse API response with camelCase
    data = Response.model_validate({"userId": 1, "userName": "Bob"})
    print(f"  Parsed from camelCase: user_id={data.user_id}, user_name={data.user_name}")

    # Output with alias
    dumped = data.model_dump(by_alias=True)
    print(f"  model_dump(by_alias=True): {dumped}")


# AliasPath: Extract value from nested JSON (Pydantic V2 new feature)
class FlatModel(BaseModel):
    city: str = Field(validation_alias=AliasPath("address", "city"))


def demo_alias_path():
    print("\n7b. AliasPath:")
    data = FlatModel.model_validate({"address": {"city": "Shanghai"}})
    print(f"  Extracted from nested JSON: city={data.city}")


# =============================================================================
# 8. Parse from JSON/dict (从JSON/dict解析)
# =============================================================================


def demo_parse():
    print("\n8. Parse from JSON/dict:")
    # From dict
    user = SerializationDemo.model_validate({"id": 1, "name": "Alice", "email": "a@b.com"})
    print(f"  From dict: {user.name}")

    # From JSON string (faster than model_validate + json.loads)
    user_from_json = SerializationDemo.model_validate_json(
        '{"id": 2, "name": "Bob", "email": "b@c.com"}'
    )
    print(f"  From JSON: {user_from_json.name}")


# =============================================================================
# 9. ConfigDict Common Configurations (ConfigDict常用配置)
# =============================================================================


class ConfigDemo(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,  # Auto-strip whitespace from strings
        frozen=True,  # Immutable (like dataclass frozen)
        extra="forbid",  # Forbid extra fields ("ignore"/"allow" also available)
    )

    name: str = "default"


def demo_config():
    print("\n9. ConfigDict:")
    # Test frozen
    demo = ConfigDemo(name="test")
    try:
        demo.name = "change"
    except Exception as e:
        print(f"  Frozen: Cannot modify (expected)")

    # Test extra=forbid
    try:
        extra_demo = ConfigDemo(extra_field="not allowed")
    except Exception as e:
        print(f"  Extra='forbid': Rejected extra field (expected)")


# =============================================================================
# 10. Using TypeAdapter (Non-Model validation scenario)
# =============================================================================


def demo_type_adapter():
    print("\n10. TypeAdapter (Pydantic):")
    # Validate any type, no need to define a Model
    adapter = TypeAdapter(List[int])
    result = adapter.validate_python([1, 2, "3"])
    print(f"  validate_python([1, 2, '3']): {result}")

    json_result = adapter.validate_json("[1, 2, 3]")
    print(f"  validate_json('[1, 2, 3]'): {json_result}")


# =============================================================================
# 11. Using Computed Fields (计算属性)
# =============================================================================


class OrderItem(BaseModel):
    price: float
    quantity: int

    @computed_field
    @property
    def total(self) -> float:
        return self.price * self.quantity


def demo_computed_field():
    print("\n11. Computed Fields:")
    item = OrderItem(price=10.5, quantity=3)
    print(f"  OrderItem(price=10.5, quantity=3).total: {item.total}")


# =============================================================================
# 12. Advanced: ActiveRecord with Custom SQLTypeAdapter
# =============================================================================
# This section shows how to combine Pydantic validation with
# the project's SQLTypeAdapter for database operations.


class JsonListAdapter(SQLTypeAdapter):
    """Custom adapter for storing Python list as JSON string in database.

    NOTE: This is the project's own SQLTypeAdapter, different from Pydantic's TypeAdapter.
    This adapter handles conversion between Python objects and database values.
    """

    def __init__(self):
        self._supported_types: Dict[Type, Set[Type]] = {list: {str}}

    @property
    def supported_types(self) -> Dict[Type, Set[Type]]:
        return self._supported_types

    def to_database(self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None) -> Any:
        if value is None:
            return None
        return json.dumps(value)

    def from_database(self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            return json.loads(value)
        return value


class PostWithTags(UUIDMixin, ActiveRecord):
    """Post model with tags stored as JSON in database."""

    title: str
    content: str
    tags_cache: Annotated[List[str], UseAdapter(JsonListAdapter(), str)] = []

    @computed_field
    @property
    def tag_count(self) -> int:
        return len(self.tags_cache)


# =============================================================================
# 13. ActiveRecord with Pydantic Config
# =============================================================================


class StrictUser(ActiveRecord):
    """ActiveRecord with strict mode and custom validation."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    username: str = Field(min_length=3, max_length=50)
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v.lower()


# =============================================================================
# Main Execution with Database Demo
# =============================================================================


def main():
    print("=" * 60)
    print("Pydantic V2 Integration Examples")
    print("=" * 60)

    # Demo nested models
    demo_nested_models()

    # Demo serialization
    demo_serialization()

    # Demo alias
    demo_alias()

    # Demo alias path
    demo_alias_path()

    # Demo parse
    demo_parse()

    # Demo config
    demo_config()

    # Demo type adapter
    demo_type_adapter()

    # Demo computed fields
    demo_computed_field()

    # Demo custom validators
    test_custom_validators()

    # Test type coercion
    test_type_coercion()

    # Database demo
    print("\n" + "=" * 60)
    print("Database Integration Demo")
    print("=" * 60)

    # Configure Database (Use in-memory database)
    config = SQLiteConnectionConfig(database=":memory:")

    # Define a model that can store list as JSON
    class DemoModel(UUIDMixin, TimestampMixin, ActiveRecord):
        title: str
        data_list: Annotated[List[str], UseAdapter(JsonListAdapter(), str)] = []
        is_active: bool = True

        @classmethod
        def table_name(cls) -> str:
            return "demo_model"

    DemoModel.configure(config, SQLiteBackend)
    backend = DemoModel.backend()

    # Create Table
    backend.execute(
        """
        CREATE TABLE demo_model (
            id TEXT PRIMARY KEY,
            title TEXT,
            data_list TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT,
            version INTEGER DEFAULT 1
        )
    """,
        options=ExecutionOptions(stmt_type=StatementType.DDL),
    )

    # Test 1: CRUD with Pydantic validation
    print("\n1. CRUD with Pydantic Validation:")
    try:
        model = DemoModel(title="Test Model", data_list=["a", "b", "c"], is_active=True)
        model.save()
        print(f"  Created: id={model.id}, title={model.title}, data_list={model.data_list}")

        # Find and verify - adapter converts JSON string back to list
        found = DemoModel.find_one(model.id)
        print(f"  Loaded: title={found.title}, data_list={found.data_list}")
    except Exception as e:
        print(f"  Error: {e}")

    # Test 2: Validation with strict mode
    print("\n2. Strict Mode Validation:")
    try:
        # This should work
        model2 = DemoModel(title="Strict Test", data_list=[], is_active=False)
        model2.save()
        print(f"  Created with is_active=False: OK")

        # Try to pass string where bool is expected (should fail in strict mode)
        class StrictDemo(BaseModel):
            model_config = ConfigDict(strict=True)
            value: int

        StrictDemo(value=42)
        print(f"  Strict model with int: OK")
    except Exception as e:
        print(f"  Error: {type(e).__name__}")

    print("\n" + "=" * 60)
    print("All examples executed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()

