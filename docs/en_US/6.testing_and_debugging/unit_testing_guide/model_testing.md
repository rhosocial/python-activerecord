# Model Testing with `python-activerecord-testsuite` Patterns

Testing your `ActiveRecord` models is fundamental to building robust and reliable applications. This guide demonstrates how to test your models effectively, leveraging the patterns established by the official `python-activerecord-testsuite` for a comprehensive and standardized approach.

The `testsuite` is designed to provide a generic way to define tests that can run against various database backends. This is achieved through "Providers" that supply backend-specific implementations and configurations. This approach promotes isolated, repeatable, and thorough testing.

## Understanding the Test Setup (Provider-based)

The `python-activerecord-testsuite` uses a `ProviderRegistry` to manage different backend implementations. For example, the SQLite backend registers several providers (e.g., `BasicProvider`, `EventsProvider`, `QueryProvider`), each responsible for setting up specific test scenarios and models for their respective feature groups.

A core component of this setup is the `_setup_model` method (or similar helper) within a Provider, which dynamically configures an `ActiveRecord` model for testing. This involves:
1.  Obtaining the correct `ConnectionConfig` and `StorageBackend` class for a given test scenario.
2.  Calling `model_class.configure(config, backend_class)` to link the model to the live database connection.
3.  Preparing the database schema (e.g., dropping existing tables and creating new ones from SQL files).

Here's a simplified representation of how a model is configured for testing:

```python
# Simplified helper from a Provider (e.g., BasicProvider in python-activerecord)
import os
import tempfile
from typing import Type
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

def _setup_model_for_testing(model_class: Type[ActiveRecord], scenario_name: str, schema_sql: str) -> Type[ActiveRecord]:
    """
    Configures an ActiveRecord model for a given test scenario,
    sets up a temporary database, and creates the schema.
    """
    # For simplicity, we'll always use an in-memory SQLite database here.
    # Actual providers use scenario_name to select different configurations.
    config = SQLiteConnectionConfig(database=":memory:")
    
    # Configure the model class with our specific backend and config.
    model_class.configure(config, SQLiteBackend)
    
    # Prepare the database schema.
    model_class.__backend__.execute(f"DROP TABLE IF EXISTS {model_class.__table_name__}")
    model_class.__backend__.execute(schema_sql)
    
    return model_class
```

In your actual tests, you would use `pytest` fixtures provided by the `testsuite` (or your own providers) to obtain a properly configured model instance.

## Basic Model Testing (CRUD Operations)

We'll use a `User` model example, similar to the `User` model found in the `testsuite`'s basic feature fixtures (`rhosocial.activerecord.testsuite.feature.basic.fixtures.models`).

```python
# Assuming this User model is defined in your_app/models.py
# or within your test fixtures for clarity.
from rhosocial.activerecord.model import ActiveRecord
from pydantic import Field, EmailStr
from typing import Optional

class User(ActiveRecord):
    __table_name__ = "users" # Explicitly define table name for schema creation
    id: Optional[int] = Field(None, primary_key=True)
    username: str
    email: EmailStr
    age: Optional[int] = Field(None, ge=0, le=100)
    balance: float = 0.0
    is_active: bool = True
```

Now, let's write tests for basic CRUD operations. We'll use a `pytest` fixture to provide a configured `User` model.

```python
# tests/test_basic_user.py
import pytest
from your_app.models import User
from rhosocial.activerecord.backend.errors import NotFoundError # Example exception

# Example schema for the User model
USER_SCHEMA = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    age INTEGER,
    balance REAL DEFAULT 0.0,
    is_active BOOLEAN DEFAULT TRUE
);
"""

@pytest.fixture
def configured_user_model() -> Type[User]:
    """
    Provides a configured User model with a clean database table for each test.
    """
    # Use our helper to set up the model.
    # In a real testsuite, this would come from a provider's setup_user_model.
    return _setup_model_for_testing(User, "memory", USER_SCHEMA)

def test_create_and_read_user(configured_user_model: Type[User]):
    """Tests creating a user and then retrieving it."""
    # Create
    user = configured_user_model.create(username='testuser', email='test@example.com', age=30)
    assert user.id is not None
    assert user.username == 'testuser'
    assert user.email == 'test@example.com'
    assert user.age == 30
    assert user.is_active is True

    # Read
    retrieved_user = configured_user_model.find(user.id)
    assert retrieved_user.username == 'testuser'
    assert retrieved_user.email == 'test@example.com'
    assert retrieved_user.age == 30

def test_update_user(configured_user_model: Type[User]):
    """Tests updating an existing user's attributes."""
    user = configured_user_model.create(username='testuser', email='test@example.com')
    
    # Update
    user.update(email='new_email@example.com', is_active=False)
    
    # Verify update
    updated_user = configured_user_model.find(user.id)
    assert updated_user.email == 'new_email@example.com'
    assert updated_user.is_active is False

def test_delete_user(configured_user_model: Type[User]):
    """Tests deleting a user from the database."""
    user = configured_user_model.create(username='testuser', email='test@example.com')
    user_id = user.id
    
    # Delete
    user.destroy()
    
    # Verify deletion
    with pytest.raises(NotFoundError): # Use the specific NotFoundError
        configured_user_model.find(user_id)
```

## Testing Validations

`ActiveRecord` models leverage `Pydantic` for powerful data validation. You can test these validations directly. We'll use a `ValidatedUser` model, also inspired by the `testsuite` fixtures.

```python
# Assuming this ValidatedUser model is defined in your_app/models.py
# or within your test fixtures.
import re
from rhosocial.activerecord.backend.errors import ValidationError as ActiveRecordValidationError # Alias to avoid conflict

class ValidatedUser(ActiveRecord):
    __table_name__ = "validated_users"
    id: Optional[int] = Field(None, primary_key=True)
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    age: Optional[int] = Field(None, ge=0, le=150)

    @field_validator('username')
    @classmethod
    def validate_username_no_spaces(cls, v: str) -> str:
        if len(v.strip()) != len(v):
            raise ActiveRecordValidationError("Username cannot have leading or trailing spaces")
        if not v.isalnum():
            raise ActiveRecordValidationError("Username must be alphanumeric")
        return v

    @classmethod
    def validate_record(cls, instance: 'ValidatedUser') -> None:
        """Business rule validation applied before saving."""
        if instance.age is not None and instance.age < 13:
            raise ActiveRecordValidationError("User must be at least 13 years old")
```

Now, let's test these validations:

```python
# tests/test_user_validations.py
import pytest
from pydantic import ValidationError as PydanticValidationError # Alias for Pydantic's ValidationError
from your_app.models import ValidatedUser
from rhosocial.activerecord.backend.errors import ValidationError as ActiveRecordValidationError

# Example schema for the ValidatedUser model
VALIDATED_USER_SCHEMA = """
CREATE TABLE validated_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    age INTEGER
);
"""

@pytest.fixture
def configured_validated_user_model() -> Type[ValidatedUser]:
    """
    Provides a configured ValidatedUser model with a clean table for each test.
    """
    return _setup_model_for_testing(ValidatedUser, "memory", VALIDATED_USER_SCHEMA)

def test_username_length_validation(configured_validated_user_model: Type[ValidatedUser]):
    """Tests Pydantic's min_length/max_length validation for username."""
    with pytest.raises(PydanticValidationError, match="username"):
        configured_validated_user_model.create(username='ab', email='test@example.com')
    with pytest.raises(PydanticValidationError, match="username"):
        configured_validated_user_model.create(username='a_very_long_username_that_exceeds_fifty_characters_limit', email='test@example.com')

def test_username_custom_validation(configured_validated_user_model: Type[ValidatedUser]):
    """Tests custom @field_validator for username."""
    with pytest.raises(ActiveRecordValidationError, match="Username cannot have leading or trailing spaces"):
        configured_validated_user_model.create(username='  testuser', email='test@example.com')
    with pytest.raises(ActiveRecordValidationError, match="Username must be alphanumeric"):
        configured_validated_user_model.create(username='test-user', email='test@example.com')

def test_email_format_validation(configured_validated_user_model: Type[ValidatedUser]):
    """Tests Pydantic's EmailStr validation for email."""
    with pytest.raises(PydanticValidationError, match="email"):
        configured_validated_user_model.create(username='testuser', email='not-an-email')

def test_age_business_rule_validation(configured_validated_user_model: Type[ValidatedUser]):
    """Tests custom business logic validation for age."""
    with pytest.raises(ActiveRecordValidationError, match="User must be at least 13 years old"):
        configured_validated_user_model.create(username='childuser', email='child@example.com', age=10)
```

## Testing Type Mappings

To test how `ActiveRecord` handles various data types, we can use a model similar to `TypeCase` from the `testsuite` fixtures, which includes a wide range of common types.

```python
# Assuming this TypeCase model is defined in your_app/models.py
from datetime import date, time, datetime
from decimal import Decimal
from typing import Optional
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.field import UUIDMixin # Provides uuid primary key

class TypeCase(UUIDMixin, ActiveRecord):
    __table_name__ = "type_cases"
    # id: UUID field provided by UUIDMixin
    username: str
    email: str
    tiny_int: Optional[int]
    small_int: Optional[int]
    big_int: Optional[int]
    float_val: Optional[float]
    double_val: Optional[float]
    decimal_val: Optional[Decimal]
    char_val: Optional[str]
    varchar_val: Optional[str]
    text_val: Optional[str]
    date_val: Optional[date]
    time_val: Optional[time]
    timestamp_val: Optional[datetime]
    blob_val: Optional[bytes]
    json_val: Optional[dict]
    array_val: Optional[list]
    is_active: bool = True
```

Now, let's test a selection of these types. Remember that `ActiveRecord` uses `TypeRegistry` and `SQLTypeAdapter`s for these conversions, as detailed in the [Data Type Mapping Guide](./data_type_mapping.md).

```python
# tests/test_type_case.py
import pytest
import uuid
from datetime import date, time, datetime
from decimal import Decimal
from your_app.models import TypeCase

# Example schema for the TypeCase model (simplified)
TYPE_CASE_SCHEMA = """
CREATE TABLE type_cases (
    id VARCHAR(36) PRIMARY KEY, -- UUID
    username VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    tiny_int INTEGER,
    small_int INTEGER,
    big_int INTEGER,
    float_val REAL,
    double_val REAL,
    decimal_val TEXT, -- Stored as TEXT in SQLite for Decimal precision
    char_val VARCHAR(1),
    varchar_val VARCHAR(255),
    text_val TEXT,
    date_val TEXT,     -- Stored as TEXT (ISO format)
    time_val TEXT,     -- Stored as TEXT (ISO format)
    timestamp_val TEXT, -- Stored as TEXT (ISO format)
    blob_val BLOB,
    json_val TEXT,     -- Stored as TEXT (JSON string)
    array_val TEXT,    -- Stored as TEXT (JSON string)
    is_active BOOLEAN
);
"""

@pytest.fixture
def configured_type_case_model() -> Type[TypeCase]:
    """
    Provides a configured TypeCase model with a clean database table for each test.
    """
    return _setup_model_for_testing(TypeCase, "memory", TYPE_CASE_SCHEMA)

def test_type_case_all_types(configured_type_case_model: Type[TypeCase]):
    """Tests writing and reading all supported data types."""
    test_uuid = uuid.uuid4()
    test_date = date(2023, 1, 15)
    test_time = time(14, 30, 45)
    test_datetime = datetime(2023, 1, 15, 14, 30, 45, 123456)
    test_decimal = Decimal("12345.6789")
    test_blob = b"binary_data"
    test_json = {"key": "value", "list": [1, 2, {"nested": True}]}
    test_array = ["item1", 123, {"obj_item": "data"}]

    tc_instance = configured_type_case_model.create(
        id=test_uuid,
        username="typetest",
        email="type@example.com",
        tiny_int=1,
        small_int=100,
        big_int=10000000000,
        float_val=1.23,
        double_val=1.23456789,
        decimal_val=test_decimal,
        char_val="A",
        varchar_val="short string",
        text_val="a very long string that needs to be stored as text",
        date_val=test_date,
        time_val=test_time,
        timestamp_val=test_datetime,
        blob_val=test_blob,
        json_val=test_json,
        array_val=test_array,
        is_active=False
    )

    retrieved_tc = configured_type_case_model.find(tc_instance.id)

    assert retrieved_tc.id == test_uuid
    assert retrieved_tc.username == "typetest"
    assert retrieved_tc.email == "type@example.com"
    assert retrieved_tc.tiny_int == 1
    assert retrieved_tc.small_int == 100
    assert retrieved_tc.big_int == 10000000000
    assert retrieved_tc.float_val == pytest.approx(1.23)
    assert retrieved_tc.double_val == pytest.approx(1.23456789)
    assert retrieved_tc.decimal_val == test_decimal
    assert retrieved_tc.char_val == "A"
    assert retrieved_tc.varchar_val == "short string"
    assert retrieved_tc.text_val == "a very long string that needs to be stored as text"
    assert retrieved_tc.date_val == test_date
    assert retrieved_tc.time_val == test_time
    # SQLite datetime precision might differ, compare up to seconds/microseconds if needed
    assert retrieved_tc.timestamp_val.isoformat(timespec='microseconds') == test_datetime.isoformat(timespec='microseconds')
    assert retrieved_tc.blob_val == test_blob
    assert retrieved_tc.json_val == test_json
    assert retrieved_tc.array_val == test_array
    assert retrieved_tc.is_active is False
```

## Testing Custom Type Adapters

As discussed in the [Data Type Mapping Guide](./data_type_mapping.md), custom `SQLTypeAdapter`s are crucial for handling specific data types not natively supported or requiring custom serialization. When testing them, you need to ensure they are correctly registered with the model's backend *before* the model interacts with the database.

Let's revisit the hypothetical `Money` type and `Your_MoneyAdapter` example.

```python
# your_app/types.py
from decimal import Decimal
from typing import Any, Dict, List, Optional, Type
from rhosocial.activerecord.backend.type_adapter import SQLTypeAdapter

class Money:
    def __init__(self, amount: Decimal, currency: str):
        self.amount = amount
        self.currency = currency
    
    def __eq__(self, other): # Important for testing equality
        if not isinstance(other, Money):
            return NotImplemented
        return self.amount == other.amount and self.currency == other.currency

class Your_MoneyAdapter(SQLTypeAdapter):
    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {Money: ["TEXT"]}

    def to_database(self, value: Money, target_type: Type, options: Optional[Dict[str, Any]] = None) -> Any:
        # Converts Money object to a string like "19.99,USD"
        return f"{value.amount},{value.currency}"
    
    def from_database(self, value: str, target_type: Type, options: Optional[Dict[str, Any]] = None) -> Any:
        # Converts "19.99,USD" string back to a Money object
        amount, currency = value.split(',')
        return Money(Decimal(amount), currency)

# your_app/models.py
from rhosocial.activerecord.model import ActiveRecord
from pydantic import Field
from .types import Money

class Product(ActiveRecord):
    __table_name__ = "products_money"
    id: Optional[int] = Field(None, primary_key=True)
    name: str
    price: Money # Model uses the custom Money type
```

Now, when testing this `Product` model, you need a fixture to configure the model and register `Your_MoneyAdapter` with its backend.

```python
# tests/test_product_money_adapter.py
import pytest
from decimal import Decimal
from your_app.models import Product
from your_app.types import Money, Your_MoneyAdapter
from rhosocial.activerecord.backend.errors import UnregisteredAdapterError # For unregistering

# Example schema for the Product model
PRODUCT_MONEY_SCHEMA = """
CREATE TABLE products_money (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    price TEXT -- Price is stored as TEXT in DB
);
"""

@pytest.fixture
def configured_product_model_with_money_adapter() -> Type[Product]:
    """
    Sets up the Product model for testing, including its schema and custom adapter.
    """
    # Configure the model using the helper.
    configured_model = _setup_model_for_testing(Product, "memory", PRODUCT_MONEY_SCHEMA)

    # Register the custom Your_MoneyAdapter with the model's backend
    backend = configured_model.backend()
    adapter = Your_MoneyAdapter()
    backend.adapter_registry.register(adapter, Money, "TEXT")

    yield configured_model

    # Cleanup: Unregister the adapter after the test
    # Note: In a real scenario, you might have a more robust cleanup for the registry
    # or rely on test isolation provided by in-memory databases.
    try:
        backend.adapter_registry.unregister(Money, "TEXT")
    except UnregisteredAdapterError:
        pass # Already unregistered or not found
```

With the model configured and the adapter registered, you can test its behavior:

```python
# tests/test_product_money_adapter.py (continued)
def test_money_type_adapter_write_and_read(configured_product_model_with_money_adapter: Type[Product]):
    """
    Tests that Your_MoneyAdapter correctly writes and reads the custom type through the model.
    """
    # 1. Create a product with a Money object
    initial_price = Money(Decimal("19.99"), "USD")
    product = configured_product_model_with_money_adapter.create(name="Test Product", price=initial_price)
    product_id = product.id

    # 2. Retrieve the product from the database
    retrieved_product = configured_product_model_with_money_adapter.find(product_id)

    # 3. Verify that the `from_database` conversion was successful
    assert isinstance(retrieved_product.price, Money)
    assert retrieved_product.price == initial_price # Uses __eq__ in Money class

    # 4. Directly inspect the raw database value to confirm `to_database` conversion
    # This requires using the model's backend directly.
    raw_data = configured_product_model_with_money_adapter.backend().execute_and_fetch_one(
        f"SELECT price FROM {configured_product_model_with_money_adapter.__table_name__} WHERE id=?",
        params=[product_id]
    )
    assert raw_data['price'] == "19.99,USD"
```

## Best Practices from the Test Suite

*   **Isolation**: Each test should run in an isolated environment. Providers (or your local test helpers like `_setup_model_for_testing`) ensure this by configuring a fresh database connection and schema for each test, often using in-memory databases (e.g., SQLite `:memory:`).
*   **Scenario-based Testing**: The `testsuite` uses different scenarios (e.g., in-memory, file-based SQLite, different pragmas) to test models under various conditions. This ensures robustness across deployment environments.
*   **Clear Schema Definitions**: Keep your test database schemas explicit and separate. In `testsuite` providers, these are often loaded from `.sql` files, promoting clarity and maintainability.
*   **Parameterized Fixtures**: Leverage `pytest` fixtures, potentially parameterized by scenarios, to avoid code duplication and ensure thorough testing across different backend configurations.
*   **Focus on `ActiveRecord` API**: While providers handle low-level setup, your tests should primarily interact with your `ActiveRecord` models' public API (`.create`, `.find`, `.update`, `.destroy`, `.query`). Use the backend's direct execution methods (`.execute`, `.execute_and_fetch_one`) sparingly, mainly for verifying intermediate states (like raw database values for adapter testing) or very low-level backend feature tests.
*   **Aliasing Pydantic Errors**: If your models use both Pydantic's `ValidationError` and the framework's `ActiveRecordValidationError` (e.g., for custom business logic), consider aliasing them to avoid confusion, as shown in the validation example.