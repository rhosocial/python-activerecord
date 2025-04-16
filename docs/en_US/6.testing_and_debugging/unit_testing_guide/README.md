# Unit Testing Guide

Unit testing is a critical part of developing reliable ActiveRecord applications. This guide covers best practices and strategies for testing your ActiveRecord models, relationships, and transactions.

## Overview

Effective unit testing for ActiveRecord applications involves:

- Testing model validation and business logic
- Verifying relationship behavior
- Ensuring transaction integrity
- Mocking database connections when appropriate

## Testing Framework

Python ActiveRecord is designed to work seamlessly with standard Python testing frameworks like:

- `unittest` - Python's built-in testing framework
- `pytest` - A more feature-rich testing framework with excellent fixtures support

## Test Database Configuration

When testing ActiveRecord models, it's recommended to:

1. Use a separate test database configuration
2. Reset the database state between tests
3. Use transactions to isolate test cases
4. Consider using in-memory SQLite for faster tests when appropriate

## Contents

- [Model Testing](model_testing.md) - Strategies for testing ActiveRecord models
- [Relationship Testing](relationship_testing.md) - Techniques for testing model relationships
- [Transaction Testing](transaction_testing.md) - Approaches for testing database transactions

## Best Practices

- Keep tests isolated and independent
- Use fixtures or factories to create test data
- Test both valid and invalid scenarios
- Mock external dependencies when necessary
- Use database transactions to speed up tests and ensure isolation