# Unit Testing Guide

Unit testing with rhosocial ActiveRecord currently focuses on basic model functionality and simple operations.

## Overview

Current unit testing involves:

- Testing basic model creation and validation
- Verifying simple CRUD operations
- Basic query execution verification

## Testing Framework

rhosocial ActiveRecord works with standard Python testing frameworks:

- `unittest` - Python's built-in testing framework
- `pytest` - A more feature-rich testing framework

## Basic Test Setup

For testing with ActiveRecord models:

1. Configure a test database (typically in-memory SQLite)
2. Create necessary database tables
3. Test basic model operations

## Current Limitations

- No built-in test fixtures or factories
- Limited relationship testing support
- No transaction testing framework
- Basic error handling verification only

## Simple Test Example

```python
import unittest
from rhosocial.activerecord import ActiveRecord

class User(ActiveRecord):
    name: str
    email: str

class TestUser(unittest.TestCase):
    def setUp(self):
        # Setup test database
        pass

    def test_model_creation(self):
        user = User(name="Test User", email="test@example.com")
        self.assertEqual(user.name, "Test User")
        
    def test_save_operation(self):
        user = User(name="Test User", email="test@example.com")
        result = user.save()
        # Verify save operation completed
        self.assertTrue(result)
```