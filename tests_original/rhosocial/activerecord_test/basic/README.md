# Basic Functionality Tests

This directory contains comprehensive test suites for the basic functionality of RhoSocial ActiveRecord. These tests verify the fundamental CRUD operations, field handling, and validation mechanisms that all database backends must implement.

## 📋 Table of Contents

- [Overview](#overview)
- [Directory Structure](#directory-structure)
- [Test Modules](#test-modules)
- [Test Models](#test-models)
- [Database Schema](#database-schema)
- [Backend Requirements](#backend-requirements)
- [Usage for Backend Developers](#usage-for-backend-developers)
- [Running Tests](#running-tests)
- [Test Coverage](#test-coverage)

## 🎯 Overview

The basic functionality tests ensure that your database backend correctly implements the core ActiveRecord operations. These tests are **mandatory** for all database backends, whether relational or non-relational, as they validate the fundamental contract between the ActiveRecord interface and the underlying database implementation.

**Priority Level**: 🔴 **Required** for all backends

## 📁 Directory Structure

```
tests/rhosocial/activerecord_test/basic/
├── __init__.py                 # Module initialization
├── conftest.py                # Pytest configuration
├── test_crud.py               # CRUD operations testing
├── test_fields.py             # Field type handling testing
├── test_validation.py         # Data validation testing
└── fixtures/                  # Test fixtures and models
    ├── __init__.py
    ├── models.py              # Test model definitions
    └── schema/                # Database schema files
        └── sqlite/            # SQLite reference schemas
            ├── users.sql
            ├── type_cases.sql
            ├── type_tests.sql
            ├── validated_users.sql
            └── validated_field_users.sql
```

## 🧪 Test Modules

### test_crud.py - CRUD Operations

Tests the fundamental Create, Read, Update, Delete operations that form the core of any ActiveRecord implementation.

**Key Test Functions:**
- `test_create_user()` - Record creation with various data types
- `test_create_user_with_invalid_data()` - Validation during creation
- `test_find_user()` - Record retrieval by primary key
- `test_find_nonexistent_user()` - Handling of missing records
- `test_update_user()` - Record modification and dirty tracking
- `test_update_with_invalid_data()` - Validation during updates
- `test_delete_user()` - Record deletion and verification

**Features Tested:**
- Basic CRUD operations
- Primary key handling
- Timestamp management (created_at, updated_at)
- Record state tracking (is_new_record, is_dirty)
- Error handling for invalid operations
- Complex data types (Decimal, DateTime, etc.)

### test_fields.py - Field Type Handling

Validates that your backend correctly handles various data types and field configurations.

**Key Test Functions:**
- `test_string_field()` - String handling with special characters and Unicode
- `test_numeric_fields()` - Integer, Float, and Decimal precision
- `test_boolean_field()` - Boolean value storage and retrieval
- `test_datetime_fields()` - Date, Time, and DateTime handling
- `test_json_field()` - JSON/structured data support
- `test_nullable_fields()` - NULL value handling
- `test_default_values()` - Field default value behavior

**Data Types Covered:**
- String/Text fields with encoding
- Numeric types (Integer, Float, Decimal)
- Boolean values
- Date and time types
- JSON/structured data
- Binary data (BLOB)
- Array/list data
- UUID fields

### test_validation.py - Data Validation

Ensures that your backend properly enforces data validation rules at both the field level and business logic level.

**Key Test Functions:**
- `test_field_validation()` - Pydantic field-level validation
- `test_business_rule_validation()` - Custom validation rules
- `test_validation_on_update()` - Validation during record updates
- `test_validation_error_handling()` - Proper error propagation

**Validation Types:**
- Field constraints (length, range, format)
- Data type validation
- Email format validation
- Custom business rules
- Cross-field validation

## 🏗️ Test Models

The test suite includes several model classes designed to test different aspects of ActiveRecord functionality:

### User Model
```python
class User(IntegerPKMixin, TimestampMixin, ActiveRecord):
    __table_name__ = "users"
    
    id: Optional[int] = None
    username: str
    email: EmailStr
    age: Optional[int] = Field(..., ge=0, le=100)
    balance: float = 0.0
    is_active: bool = True
```
**Purpose**: Tests basic CRUD operations with common field types and automatic timestamps.

### TypeCase Model
```python
class TypeCase(UUIDMixin, ActiveRecord):
    __table_name__ = "type_cases"
    
    # Comprehensive data type testing
    username: str
    email: str
    tiny_int: Optional[int]
    float_val: Optional[float]
    decimal_val: Optional[Decimal]
    date_val: Optional[date]
    json_val: Optional[dict]
    # ... and more
```
**Purpose**: Tests all supported data types and their proper serialization/deserialization.

### ValidatedUser Model
```python
class ValidatedUser(IntegerPKMixin, ActiveRecord):
    __table_name__ = "validated_users"
    
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    age: Optional[int] = Field(None, ge=0, le=150)
    
    @field_validator('username')
    def validate_username(cls, v: str) -> str:
        # Custom validation logic
        ...
```
**Purpose**: Tests field validation and custom business rules.

### TypeTestModel Model
```python
class TypeTestModel(UUIDMixin, ActiveRecord):
    __table_name__ = "type_tests"
    
    string_field: str = Field(default="test string")
    int_field: int = Field(default=42)
    decimal_field: Decimal = Field(default=Decimal("10.99"))
    datetime_field: datetime = Field(default_factory=datetime.now)
    # ... more test fields
```
**Purpose**: Tests field type handling with default values and complex types.

## 🗄️ Database Schema

The `fixtures/schema/sqlite/` directory contains reference database schemas that your backend should be able to create and work with. These schemas demonstrate:

### users.sql
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    email TEXT NOT NULL,
    age INTEGER,
    balance REAL NOT NULL DEFAULT 0.00,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT,
    updated_at TEXT
);
```

### type_cases.sql
```sql
CREATE TABLE type_cases (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    -- Various data type columns
    decimal_val TEXT,
    json_val TEXT,
    blob_val BLOB,
    -- ... more type examples
);
```

**Schema Features:**
- Primary key handling (both auto-increment and UUID)
- Default values
- NOT NULL constraints
- Various data type mappings
- Timestamp columns
- JSON/structured data storage

## ⚡ Backend Requirements

For your database backend to pass these tests, it must implement:

### Required Operations
- ✅ **CREATE**: Insert new records with proper field handling
- ✅ **READ**: Retrieve records by primary key
- ✅ **UPDATE**: Modify existing records with change tracking
- ✅ **DELETE**: Remove records from the database

### Required Features
- ✅ **Primary Key Management**: Auto-generation and UUID support
- ✅ **Data Type Handling**: Proper serialization/deserialization
- ✅ **Validation Integration**: Support for Pydantic validation
- ✅ **Timestamp Tracking**: Automatic created_at/updated_at handling
- ✅ **Record State Tracking**: is_new_record, is_dirty flags
- ✅ **Error Handling**: Proper exception propagation

### Data Type Support
| Type | Required | Notes |
|------|----------|-------|
| String/Text | ✅ Required | Unicode support |
| Integer | ✅ Required | Various sizes |
| Float | ✅ Required | Precision handling |
| Decimal | ✅ Required | Exact precision |
| Boolean | ✅ Required | True/False mapping |
| DateTime | ✅ Required | Timezone awareness |
| JSON | 🟡 Recommended | Structured data |
| Binary | 🟡 Optional | BLOB support |
| UUID | 🟡 Recommended | Primary key option |

## 👨‍💻 Usage for Backend Developers

### Step 1: Create Backend-Specific Models

```python
# In your backend test package
from rhosocial.activerecord_test.basic.fixtures.models import (
    User, TypeCase, ValidatedUser, TypeTestModel
)
from rhosocial.activerecord_test.utils import create_active_record_fixture

# Configure models for your backend
User.__supported_backends__ = ["your_backend"]
TypeCase.__supported_backends__ = ["your_backend"]
ValidatedUser.__supported_backends__ = ["your_backend"]
TypeTestModel.__supported_backends__ = ["your_backend"]

# Create backend-specific fixtures
your_user_class = create_active_record_fixture(User)
your_type_case_class = create_active_record_fixture(TypeCase)
your_validated_user = create_active_record_fixture(ValidatedUser)
your_type_test_model = create_active_record_fixture(TypeTestModel)
```

### Step 2: Register Your Backend

```python
# In your backend's utils.py
from rhosocial.activerecord_test.utils import DB_HELPERS, DB_CONFIGS
from your_backend.backend import YourBackend
from your_backend.config import YourConnectionConfig

# Register your backend
DB_CONFIGS["your_backend"] = {
    "local": {
        "host": "localhost",
        "database": "test_db",
        # ... your config
    }
}

DB_HELPERS["your_backend"] = {
    "class": YourBackend,
    "config_class": YourConnectionConfig,
}
```

### Step 3: Create Database Schema

Adapt the SQLite schemas in `fixtures/schema/sqlite/` to your database's SQL dialect:

```sql
-- For PostgreSQL example
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    age INTEGER,
    balance DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Step 4: Reuse Test Functions

```python
# In your compatibility test module
from rhosocial.activerecord_test.basic.test_crud import (
    test_create_user,
    test_find_user,
    test_update_user,
    test_delete_user
)

class TestYourBackendBasicCompatibility:
    def test_your_create_user(self, your_user_class):
        test_create_user(your_user_class)
    
    def test_your_find_user(self, your_user_class):
        test_find_user(your_user_class)
    
    # ... reuse other test functions
```

## 🚀 Running Tests

### Run All Basic Tests
```bash
# From project root
PYTHONPATH=src:tests:$PYTHONPATH pytest tests/rhosocial/activerecord_test/basic/
```

### Run Specific Test Module
```bash
# Test only CRUD operations
PYTHONPATH=src:tests:$PYTHONPATH pytest tests/rhosocial/activerecord_test/basic/test_crud.py

# Test only field handling
PYTHONPATH=src:tests:$PYTHONPATH pytest tests/rhosocial/activerecord_test/basic/test_fields.py

# Test only validation
PYTHONPATH=src:tests:$PYTHONPATH pytest tests/rhosocial/activerecord_test/basic/test_validation.py
```

### Run With Coverage
```bash
PYTHONPATH=src:tests:$PYTHONPATH pytest tests/rhosocial/activerecord_test/basic/ --cov=rhosocial.activerecord
```

### Verbose Output
```bash
PYTHONPATH=src:tests:$PYTHONPATH pytest tests/rhosocial/activerecord_test/basic/ -v -s
```

## 📊 Test Coverage

These basic tests provide comprehensive coverage of:

### Core Functionality (100% Required)
- ✅ Record creation and insertion
- ✅ Record retrieval by primary key
- ✅ Record updates and modifications
- ✅ Record deletion
- ✅ Primary key generation
- ✅ Timestamp management
- ✅ Record state tracking

### Data Handling (90% Required)
- ✅ String/text field processing
- ✅ Numeric type handling
- ✅ Boolean value storage
- ✅ Date/time processing
- ✅ NULL value handling
- ✅ Default value behavior
- 🟡 JSON/structured data (if supported)
- 🟡 Binary data handling (if supported)

### Validation (95% Required)
- ✅ Pydantic field validation
- ✅ Data type validation
- ✅ Field constraint validation
- ✅ Custom business rules
- ✅ Error message handling
- ✅ Validation on updates

### Expected Pass Rate
- **Relational Databases**: 95-100% of tests should pass
- **Non-Relational Databases**: 80-95% depending on capabilities
- **Document Stores**: 70-90% (may skip some relational features)
- **Key-Value Stores**: 60-80% (basic operations only)

## 🔍 Troubleshooting

### Common Issues

#### Test Failures Due to Data Type Handling
```python
# Problem: Decimal precision loss
assert saved_model.decimal_field == Decimal("10.99")  # Fails

# Solution: Implement proper Decimal serialization in your backend
```

#### Primary Key Generation Issues
```python
# Problem: Auto-increment not working
assert instance.id is not None  # Fails after save()

# Solution: Ensure your backend properly handles auto-generated keys
```

#### Timestamp Handling Problems
```python
# Problem: Timestamps not being set
assert instance.created_at is not None  # Fails

# Solution: Implement TimestampMixin support in your backend
```

### Debug Tips

1. **Enable Logging**: Set logging to DEBUG to see SQL/query details
2. **Check Schema**: Ensure your database schema matches the test requirements
3. **Validate Configuration**: Verify your backend is properly registered
4. **Test Incrementally**: Start with simple CRUD tests before complex validation

## 📞 Support

If you encounter issues while implementing basic functionality tests for your backend:

1. **Check Reference Implementation**: Look at the SQLite backend for guidance
2. **Review Test Models**: Ensure your backend supports the required field types
3. **Validate Schema**: Make sure your database schema is compatible
4. **Debug Step by Step**: Run individual test functions to isolate issues

For more information, see the main [TESTING.md](../../../TESTING.md) guide.

---

**Remember**: These basic tests form the foundation for all other ActiveRecord functionality. Ensure your backend passes these tests before moving on to more advanced features like relations, queries, or mixins.