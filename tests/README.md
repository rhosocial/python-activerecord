# rhosocial-activerecord Test Directory Structure

This directory contains the complete test suite for the `rhosocial-activerecord` core package. Tests use the **Provider Pattern**, supporting unified testing across multiple backends and Python versions.

## Directory Structure Overview

```text
tests/
├── conftest.py              # pytest root configuration, sets testsuite environment
├── providers/               # Test provider implementations (Provider Pattern)
│   ├── basic.py             # Basic functionality test provider
│   ├── events.py            # Event system test provider
│   ├── mixins.py            # Mixin class test provider
│   ├── query.py             # Query functionality test provider
│   ├── registry.py          # Provider registry
│   └── scenarios.py         # Scenario test provider
└── rhosocial/activerecord_test/
    ├── feature/             # Feature tests
    │   ├── backend/         # Backend-related tests
    │   ├── basic/           # Basic functionality tests
    │   ├── events/          # Event system tests
    │   ├── interface/       # Interface tests
    │   ├── mixins/          # Mixin class tests
    │   ├── query/           # Query functionality tests
    │   └── relation/        # Relationship tests
    └── realworld/           # Real-world scenario tests (reserved)
```

## Core Components

### 1. Provider Pattern (`providers/`)

The Provider pattern is the core mechanism for achieving backend-agnostic testing. Each Provider encapsulates test data preparation and cleanup logic for specific functionality, enabling test suite reuse across backends.

| File | Responsibility |
| ---- | ---------------- |
| `basic.py` | Basic CRUD, field mapping, type adapter tests |
| `events.py` | Lifecycle events, event handler tests |
| `mixins.py` | Optimistic lock, soft delete, timestamp mixin tests |
| `query.py` | Query builder, aggregation, JOIN, CTE tests |
| `registry.py` | Global Provider registry for testsuite lookup |
| `scenarios.py` | Complex business scenario tests |

**Workflow**:

1. `conftest.py` sets the `TESTSUITE_PROVIDER_REGISTRY` environment variable
2. Testsuite finds corresponding Provider implementations via the registry
3. Providers are responsible for creating test models, preparing data, and cleaning up resources

### 2. Feature Tests (`feature/`)

#### 2.1 Backend Tests (`backend/`)

Backend-related tests are organized by functionality module and backend type:

| Subdirectory | Content |
| ------------ | ------- |
| `base/` | Base backend protocol, transaction management, hook function tests |
| `dialect/` | SQL dialect protocol tests (CTE, window functions, arrays, JSON, etc.) |
| `dummy/` | Dummy backend basic functionality tests (no real database connection) |
| `dummy2/` | Dummy backend advanced functionality tests (window functions, advanced mixins) |
| `sqlite/` | SQLite backend core functionality tests |
| `sqlite2/` | SQLite batch operation tests (batch DML/DQL, transactions) |
| `sqlite3/` | SQLite column mapping and RETURNING clause tests |
| `sqlite4/` | SQLite introspection tests (table, column, index info queries) |
| `sqlite_async/` | Async backend functionality tests |
| `sqlite_pragma_extension/` | SQLite PRAGMA extension functionality tests |

**Directory Numbering Explanation**:

- Unnumbered directories (e.g., `sqlite/`): Core functionality tests
- Numbered directories (e.g., `sqlite2/`, `sqlite3/`): Specialized functionality tests, numbered by development order

#### 2.2 Basic Tests (`basic/`)

Tests for ActiveRecord core functionality:

- `test_crud.py` - Create, Read, Update, Delete operations
- `test_fields.py` - Field definition and types
- `test_validation.py` - Data validation
- `test_field_column_mapping.py` - Field to column mapping
- `test_type_adapter.py` - Type adapters
- `test_basic_mapped_models.py` - Basic mapped models

#### 2.3 Events Tests (`events/`)

Tests for model lifecycle events:

- `test_lifecycle.py` - Lifecycle hooks (before_save, after_save, etc.)
- `test_handlers.py` - Event handler registration and execution

#### 2.4 Mixins Tests (`mixins/`)

Tests for reusable mixin classes:

- `test_optimistic_lock.py` - Optimistic locking mechanism
- `test_soft_delete.py` - Soft delete functionality
- `test_timestamps.py` - Automatic timestamps
- `test_combined_articles.py` - Combined mixin tests

#### 2.5 Query Tests (`query/`)

Tests for query builder functionality:

- `test_active_query_basic.py` - Basic queries
- `test_active_query_join.py` - JOIN operations
- `test_active_query_aggregate.py` - Aggregate functions
- `test_active_query_range.py` - Range queries
- `test_active_query_set_operation.py` - Set operations (UNION, etc.)
- `test_aggregate_queries.py` - Aggregate queries

#### 2.6 Relation Tests (`relation/`)

Tests for model relationships:

- `test_base.py` - Basic relationships
- `test_interfaces.py` - Relationship interfaces
- `test_async_descriptors.py` - Async descriptors
- `test_batch_*.py` - Batch loading tests

### 3. Real-world Tests (`realworld/`)

Reserved directory for real business scenario integration tests. These tests simulate complex business logic combinations to validate ActiveRecord behavior in real applications.

## Test Running Guide

### Run All Tests

```bash
# Activate virtual environment in project root
source .venv3.14/bin/activate

# Run all tests
pytest tests/
```

### Run Specific Category Tests

```bash
# Run feature tests only
pytest tests/rhosocial/activerecord_test/feature/

# Run backend tests only
pytest tests/rhosocial/activerecord_test/feature/backend/

# Run SQLite introspection tests only
pytest tests/rhosocial/activerecord_test/feature/backend/sqlite4/
```

### Run Single Test File

```bash
pytest tests/rhosocial/activerecord_test/feature/basic/test_crud.py
```

### Filter by Markers

```bash
# Run tests with specific markers
pytest -m "not slow" tests/
```

## Test Conventions

### 1. File Naming

- Test files start with `test_`
- conftest.py for pytest fixtures
- schema/ subdirectories for test SQL schema files

### 2. Test Class Naming

- Test classes start with `Test`
- Use descriptive names, e.g., `TestSQLiteBackendTransaction`

### 3. Test Method Naming

- Test methods start with `test_`
- Use underscores to separate words, describe test scenario
- Example: `test_insert_with_returning_clause`

### 4. Fixture Usage

- Use standard fixtures provided by testsuite
- Use `select_fixture()` utility to select version-appropriate fixtures
- Python 3.8 uses base models, 3.10+ uses enhanced models

## Relationship with Testsuite

`rhosocial-activerecord-testsuite` is an independent test suite package that defines test interfaces and common test logic. This project implements the interfaces defined in testsuite through the Provider pattern, enabling tests to run across backends.

```text
testsuite (defines interfaces) ← providers/ (implements interfaces) ← feature/ (concrete tests)
```

## Extension Guide

### Adding New Backend Tests

1. Create a new directory under `feature/backend/` (e.g., `mysql/`)
2. Create `conftest.py` to configure fixtures
3. Write test files
4. Add corresponding Provider implementation in `providers/`

### Adding New Feature Tests

1. Determine which feature module the test belongs to
2. Create test file in the corresponding directory
3. If new fixtures are needed, update `conftest.py` or `providers/`

### Adding New Providers

1. Create a new Provider file under `providers/`
2. Inherit from the base interface defined in testsuite
3. Implement all required methods
4. Register in `registry.py`

## Common Issues and Solutions

### 1. Schema Loading Issues

**Problem**: Schema files not found when running tests

**Solution**: Ensure schema files are in the correct feature directory and verify the Provider's `_load_sqlite_schema` method points to the correct directory.

### 2. Import Errors

**Problem**: Cannot import ActiveRecord or other modules

**Solution**: Ensure the library is installed in development mode (`pip install -e .`) or PYTHONPATH includes the src directory.

### 3. Provider Registration Issues

**Problem**: Test suite cannot find provider implementations

**Solution**: Check that providers are correctly registered in `providers/registry.py` and that interface names match those defined in testsuite.

### 4. Test Scenario Problems

**Problem**: Tests not running with expected database configurations

**Solution**: Verify scenario definitions in `providers/scenarios.py` and ensure the provider correctly returns available scenarios.

### 5. Fixture Parameter Mismatch

**Problem**: Tests complaining about fixture parameters

**Solution**: Ensure bridge files correctly import fixtures from testsuite and tests in testsuite receive fixtures as parameters.

## Important Notes

- Tests in the testsuite package define testing contracts but don't import fixtures directly
- Bridge files in this repository import fixtures from testsuite and make them available to pytest
- Providers handle database setup and model configuration for each test
- Schema files are centralized by feature to maintain organization
- The architecture allows the same tests to run against different backends
