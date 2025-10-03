# Tests Directory Documentation

## Overview
This directory contains the test infrastructure for the python-activerecord library. The tests are organized using a testsuite pattern that separates test definitions from backend implementations.

## Directory Structure

### `providers/`
Contains the provider implementations that connect the testsuite with the database backends. Each provider implements interfaces defined in the testsuite and handles:
- Database schema setup and teardown
- Test scenario configuration
- Backend-specific model configuration

### `rhosocial/activerecord_test/`
Contains bridge files that connect the testsuite tests with the specific backend implementation. These files import tests from the testsuite and make them run against the specific backend (SQLite in this case).

#### `feature/`
Contains bridge files for each feature group:
- `basic/` - Basic CRUD operations
- `events/` - Event handling functionality
- `mixins/` - Mixin functionality
- `query/` - Query operations

### `fixtures/`
Contains shared fixtures and resources needed for testing:
- `schemas/` - SQL schema files organized by backend type

#### `schemas/sqlite/`
Contains SQLite-specific schema files for different test groups.

## Working with the Testsuite Architecture

### 1. Understanding the Testsuite Pattern
The tests are structured using a provider pattern:
- Test definitions exist in the `python-activerecord-testsuite` package
- Backend implementations (like SQLite) provide concrete implementations
- Bridge files in this repository connect the abstract tests with concrete implementations

### 2. Adding New Schema Files
1. Add schema files to the appropriate feature directory:
   - For query tests: `tests/rhosocial/activerecord_test/feature/query/schema/`
   - For other features: follow the same pattern
2. Ensure the schema files are named to match the expected table names
3. Update the provider to load the schema file

### 3. Creating/Updating Providers
Providers implement the interfaces defined in the testsuite and are responsible for:
- Setting up database schemas for each test
- Configuring models with the appropriate backend
- Managing test scenarios
- Cleaning up after tests

### 4. Running Tests
```bash
# From the project root directory
PYTHONPATH=src:tests:$PYTHONPATH pytest tests/rhosocial/activerecord_test/feature/query/
```

## Common Workflows

### Adding New Feature Tests
1. New test files should be added to the testsuite package
2. Create bridge files in the appropriate `feature/*/` directory
3. Ensure the bridge files import the correct fixtures from the testsuite
4. Register provider implementations in `providers/registry.py`

### Schema Management
All schema files are centralized by feature:
1. Query schemas: `tests/rhosocial/activerecord_test/feature/query/schema/`
2. Other features follow the same pattern
3. Providers load schemas from these centralized locations

### Provider Registration
All providers must be registered in `providers/registry.py`:
1. Import the provider class
2. Register it with the appropriate interface name
3. Ensure the interface name matches the one defined in the testsuite

## Potential Issues and Solutions

### 1. Schema Loading Issues
**Problem:** Schema files not found when running tests
**Solution:** Ensure schemas are in the correct centralized location for the feature, and verify the provider's `_load_sqlite_schema` method points to the right directory.

### 2. Import Errors
**Problem:** Cannot import ActiveRecord or other modules
**Solution:** Make sure the library is installed in development mode (`pip install -e .`) or PYTHONPATH includes the src directory.

### 3. Provider Registration Issues
**Problem:** Test suite can't find provider implementations
**Solution:** Check that providers are correctly registered in `providers/registry.py` and that interface names match between testsuite and provider.

### 4. Test Scenario Problems
**Problem:** Tests not running with expected database configurations
**Solution:** Verify scenario definitions in `providers/scenarios.py` and ensure the provider correctly returns available scenarios.

### 5. Fixture Parameter Mismatch
**Problem:** Tests complaining about fixture parameters
**Solution:** Ensure bridge files correctly import fixtures from the testsuite and tests in the testsuite receive fixtures as parameters.

## Important Notes

- Tests in the testsuite package define the testing contracts but don't import fixtures directly
- Bridge files in this repository import fixtures from the testsuite and make them available to pytest
- Providers handle database setup and model configuration for each test
- Schema files are centralized by feature to maintain organization
- The architecture allows the same tests to run against different backends