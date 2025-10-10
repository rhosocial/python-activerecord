# Testing and Debugging

Testing and debugging in rhosocial ActiveRecord currently focuses on basic functionality. The actual implementation provides fundamental tools for development and debugging, with more advanced features planned for future releases.

## Current Testing Capabilities

- Basic CRUD operation testing
- Simple model validation testing
- Direct database interaction verification
- Query execution debugging

## Contents

- [Basic Testing Guide](unit_testing_guide/README.md)
  - [Model Testing](unit_testing_guide/model_testing.md) - Testing basic model functionality
  - [Query Testing](unit_testing_guide/relationship_testing.md) - Approaches for testing query execution
  - [Database Testing](unit_testing_guide/transaction_testing.md) - Testing database operations

- [Debugging Techniques](debugging_techniques.md) - Current debugging approaches for ActiveRecord applications
  - Using logging for debugging
  - Inspecting query execution
  - Troubleshooting common issues

- [Logging and Analysis](logging_and_analysis.md) - Configuring and using logs effectively
  - Setting up logging
  - Log analysis techniques

## Limitations

The current testing framework is basic and lacks comprehensive testing tools for relationships, transactions, and advanced features. These will be added in future releases.