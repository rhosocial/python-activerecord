# Testing Strategy and Testsuite Architecture

## Overview

The rhosocial-activerecord ecosystem employs a sophisticated testing strategy based on **separation of test definitions from backend implementations**. This will be achieved through the `rhosocial-activerecord-testsuite` package, which defines standardized test contracts that all backends must implement.

> **Important Note**: The testsuite separation is currently in the planning phase. Tests currently exist within the main codebase and will be gradually migrated to the separate testsuite package. The testsuite package content described here is under active development and its directory structure should be considered as reference architecture rather than current implementation.

## Current State vs. Future Architecture

### Current State
- Tests are located in `tests/` directory of the main repository
- Backend-specific tests are mixed with general tests
- Test organization follows traditional pytest structure

### Future Architecture (In Development)
- Standardized tests will move to `rhosocial-activerecord-testsuite` package
- Backend packages will only contain backend-specific tests and schema fixtures
- Clear separation between test contracts and implementations

## Core Testing Philosophy

### Three Testing Pillars

Our testing strategy is built on three core pillars, each serving different validation purposes:

1. **Feature Tests**: Validate individual functionality points (e.g., `where` queries, `save` methods, `BelongsTo` relationships)
2. **Real-world Scenarios**: Simulate actual business scenarios to verify complex interactions
3. **Performance Benchmarks**: Measure and compare backend performance under standardized loads

### Separation of Concerns

- **Testsuite Package**: Defines test logic and business models (the "what")
- **Backend Packages**: Provide database schemas and environment setup (the "how")

## Current Test Structure

As of now, tests remain in the main repository structure:

```
tests/
├── rhosocial/
│   └── activerecord_test/
│       ├── backend/           # Backend-specific tests
│       │   └── sqlite/
│       ├── basic/            # Core functionality tests
│       │   ├── test_crud.py
│       │   ├── test_fields.py
│       │   └── test_validation.py
│       ├── query/            # Query builder tests
│       │   ├── test_active_query.py
│       │   └── test_cte_query.py
│       ├── relation/         # Relationship tests
│       └── field/           # Field type tests
```

These tests will be gradually migrated to the testsuite package following the planned architecture below.

## Testsuite Package Structure (Planned)

> **Note**: The following structure represents the planned architecture for the separated testsuite package. As the migration is ongoing, this structure serves as a reference guide and may evolve based on implementation needs.

### Directory Organization

```
rhosocial-activerecord-testsuite/
└── src/
    └── rhosocial/
        └── activerecord/
            └── testsuite/
                ├── __init__.py             # Version definitions
                ├── feature/                # Feature tests
                │   ├── basic/
                │   │   ├── test_crud.py
                │   │   ├── test_validation.py
                │   │   └── fixtures/
                │   │       └── models.py
                │   ├── query/
                │   │   ├── test_where.py
                │   │   ├── test_joins.py
                │   │   └── test_cte.py
                │   ├── relation/
                │   │   ├── test_has_one.py
                │   │   ├── test_has_many.py
                │   │   └── test_belongs_to.py
                │   └── field/
                │       ├── test_timestamp.py
                │       └── test_soft_delete.py
                ├── realworld/              # Real-world scenarios
                │   ├── fixtures/
                │   │   └── models.py
                │   ├── ecommerce/
                │   │   ├── test_checkout.py
                │   │   ├── test_inventory.py
                │   │   └── models.py
                │   ├── finance/
                │   │   ├── test_transactions.py
                │   │   └── models.py
                │   └── social/
                │       ├── test_messaging.py
                │       └── models.py
                ├── benchmark/              # Performance tests
                │   ├── fixtures/
                │   ├── test_bulk_operations.py
                │   ├── test_complex_queries.py
                │   └── test_concurrent_access.py
                └── utils/                  # Testing utilities
                    ├── schema_generator.py
                    └── helpers.py
```

### Version Management (Planned)

> **Note**: Version management strategy is tentative and will be finalized when the testsuite package is released.

The testsuite package will maintain independent version numbers for each testing pillar:

```python
# rhosocial/activerecord/testsuite/__init__.py
__version__ = "1.2.5"  # Package version, synced with feature tests
__feature_version__ = "1.2.5"  # Synced with core library
__realworld_version__ = "1.1.0"  # Independent versioning
__benchmark_version__ = "1.0.2"  # Independent versioning
```

## Test Marking System

### Standard Markers

All tests in the testsuite use pytest markers for categorization:

```python
# Feature test example
@pytest.mark.feature
@pytest.mark.feature_crud
def test_save_record():
    pass

# Real-world scenario example
@pytest.mark.realworld
@pytest.mark.scenario_ecommerce
def test_order_processing():
    pass

# Benchmark example
@pytest.mark.benchmark
@pytest.mark.benchmark_bulk
def test_bulk_insert_performance():
    pass
```

### Running Specific Test Categories

```bash
# Run all feature tests
pytest -m "feature"

# Run specific feature category
pytest -m "feature_crud"

# Run real-world scenarios
pytest -m "realworld"

# Run specific scenario
pytest -m "scenario_ecommerce"

# Run benchmarks
pytest -m "benchmark"
```

## Backend Integration

### Backend Responsibilities

Each backend package must:

1. **Provide Schema Fixtures**: Implement fixtures that create/destroy database schemas
2. **Match Testsuite Structure**: Organize schemas to mirror testsuite organization
3. **Declare Compatibility**: Specify compatible testsuite version in dependencies

### Schema Management

#### Backend Schema Organization

```
rhosocial-activerecord-mysql/
└── tests/
    ├── schemas/
    │   ├── feature/
    │   │   ├── basic.sql
    │   │   ├── query.sql
    │   │   └── relation.sql
    │   ├── realworld/
    │   │   ├── ecommerce.sql
    │   │   ├── finance.sql
    │   │   └── social.sql
    │   └── benchmark/
    │       └── performance.sql
    └── conftest.py
```

#### Fixture Implementation

Backend packages must provide fixtures that testsuite tests depend on:

```python
# rhosocial-activerecord-mysql/tests/conftest.py
import pytest
from pathlib import Path

@pytest.fixture(scope="module")
def ecommerce_schema(db_connection):
    """Setup e-commerce scenario database schema."""
    schema_path = Path("tests/schemas/realworld/ecommerce.sql")
    
    # Setup: Create tables
    with open(schema_path) as f:
        db_connection.execute(f.read())
    print("\n✓ E-commerce schema created")
    
    yield  # Run tests
    
    # Teardown: Drop tables
    db_connection.execute("""
        DROP TABLE IF EXISTS orders, order_items, products, 
                            customers, payments, inventory
    """)
    print("\n✓ E-commerce schema cleaned up")

@pytest.fixture(scope="module")
def feature_basic_schema(db_connection):
    """Setup basic feature test schema."""
    schema_path = Path("tests/schemas/feature/basic.sql")
    
    with open(schema_path) as f:
        db_connection.execute(f.read())
    
    yield
    
    db_connection.execute("DROP TABLE IF EXISTS users, posts")
```

### Schema Generation Tool

The testsuite provides a helper tool for generating initial SQL schemas:

```bash
# Generate schema template for e-commerce scenario
python -m rhosocial.activerecord.testsuite.utils.schema_generator \
    --scenario ecommerce > tests/schemas/realworld/ecommerce.sql

# Generate schema for basic features
python -m rhosocial.activerecord.testsuite.utils.schema_generator \
    --feature basic > tests/schemas/feature/basic.sql
```

**Note**: Generated schemas are templates requiring database-specific adjustments.

## Transition Strategy

### For Current Development

While the testsuite package is being developed:

1. **Continue using existing tests**: Current tests in `tests/` directory remain functional
2. **Follow testsuite patterns**: New tests should follow the planned categorization (feature/realworld/benchmark)
3. **Prepare for migration**: Structure new tests to be easily portable to the testsuite package

### For Backend Developers

To prepare for testsuite integration:

1. **Organize schemas**: Start organizing SQL schemas following the planned structure
2. **Create modular fixtures**: Design fixtures that can be easily adapted
3. **Document compatibility**: Track which core features your backend supports
4. **Monitor updates**: Watch for testsuite package release announcements

### Migration Timeline

- **Phase 1** (Current): Planning and architecture design
- **Phase 2**: Testsuite package initial release with feature tests
- **Phase 3**: Migration of real-world scenarios
- **Phase 4**: Addition of performance benchmarks
- **Phase 5**: Full deprecation of tests in main repository

## Running Testsuite (Future)

### Enabling Testsuite Execution

The testsuite is optional by default to keep local backend tests focused:

```bash
# Run only backend's own tests (default)
pytest

# Run with testsuite included
pytest --run-testsuite

# Run testsuite with specific markers
pytest --run-testsuite -m "feature"
```

### Configuration in conftest.py

Backend packages control testsuite execution through pytest hooks:

```python
# Backend's conftest.py
def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-testsuite",
        action="store_true",
        default=False,
        help="Run standardized testsuite tests"
    )

def pytest_collection_modifyitems(config, items):
    """Control test collection based on options."""
    if not config.getoption("--run-testsuite"):
        # Skip testsuite tests if not explicitly requested
        skip_testsuite = pytest.mark.skip(
            reason="Need --run-testsuite option to run"
        )
        for item in items:
            if "testsuite" in str(item.fspath):
                item.add_marker(skip_testsuite)
```

## Compatibility Reporting

### Report Generation

Generate compatibility reports to assess backend compliance:

```bash
# Generate HTML report
pytest --run-testsuite --compat-report=html

# Generate console report
pytest --run-testsuite --compat-report=console

# No report (default, suitable for IDE)
pytest --run-testsuite
```

### Report Formats

#### HTML Report
- **Visual**: Rich CSS/JavaScript interface
- **Interactive**: Clickable elements for details
- **Comprehensive**: Full test results with categorization

#### Console Report
- **Concise**: Plain text table format
- **CI-friendly**: Suitable for logs
- **Essential info**: Key metrics and scores

### Sample Compatibility Report

```
================== Backend Compatibility Report ==================
Test Suite Version: 1.2.5
- Features: v1.2.5
- Real-world: v1.1.0
- Benchmark: v1.0.2
==================================================================

| Category | Test Area | Status/Score | Notes |
|----------|-----------|--------------|--------|
| **Feature Tests (v1.2.5)** | **Compatibility** | **95%** | 190/200 passed |
| | CRUD Operations | ✅ | |
| | Query Builder | ✅ | |
| | CTE Support | ✅ | |
| | Window Functions | ⚠️ | GROUPS mode not implemented |
| | Transactions | ✅ | |
| **Real-world (v1.1.0)** | **E-commerce** | ✅ | All checkout flows pass |
| | **Finance** | ⚠️ | Deadlock in concurrent transfers |
| | **Social** | ✅ | |
| **Benchmarks (v1.0.2)** | **Bulk Insert (10k)** | 1.23s | mean execution time |
| | **Complex Join (1k)** | 5.67s | mean execution time |
```

## Backend Certification Standards

### Mandatory Requirements
- **Pass all Feature Tests**: Minimum requirement for "compatible" certification
- **Compatibility Score**: `passed_features / total_features`

### Recommended Requirements
- **Pass all Real-world Scenarios**: Demonstrates production readiness
- **Indicates high-quality implementation**

### Optional Requirements
- **Complete Performance Benchmarks**: For performance comparison
- **Does not affect compatibility certification**

## Writing Tests for Testsuite

### Feature Test Example

```python
# testsuite/feature/basic/test_crud.py
import pytest
from typing import Type

@pytest.mark.feature
@pytest.mark.feature_crud
@pytest.mark.usefixtures("feature_basic_schema")
class TestCRUDOperations:
    """Test basic CRUD operations."""
    
    def test_create(self, user_model: Type['User']):
        """Test record creation."""
        user = user_model(name="John", email="john@example.com")
        assert user.save()
        assert user.id is not None
        assert not user.is_new_record
    
    def test_read(self, user_model: Type['User']):
        """Test record retrieval."""
        # Create test data
        user = user_model(name="Jane", email="jane@example.com")
        user.save()
        
        # Test retrieval
        found = user_model.find(user.id)
        assert found is not None
        assert found.name == "Jane"
    
    def test_update(self, user_model: Type['User']):
        """Test record update."""
        user = user_model(name="Bob", email="bob@example.com")
        user.save()
        
        # Update
        user.email = "newemail@example.com"
        assert user.save()
        
        # Verify
        fresh = user_model.find(user.id)
        assert fresh.email == "newemail@example.com"
```

### Real-world Scenario Example

```python
# testsuite/realworld/ecommerce/test_checkout.py
import pytest
from decimal import Decimal

@pytest.mark.realworld
@pytest.mark.scenario_ecommerce
@pytest.mark.usefixtures("ecommerce_schema")
class TestCheckoutFlow:
    """Test complete e-commerce checkout process."""
    
    def test_order_creation_and_payment(self, ecommerce_models):
        """Test creating order and processing payment."""
        Customer, Product, Order, Payment = ecommerce_models
        
        # Create customer
        customer = Customer(
            name="Alice Smith",
            email="alice@example.com"
        )
        customer.save()
        
        # Create products
        products = [
            Product(name="Laptop", price=Decimal("999.99"), stock=10),
            Product(name="Mouse", price=Decimal("29.99"), stock=50)
        ]
        for p in products:
            p.save()
        
        # Create order
        order = Order(customer_id=customer.id)
        order.save()
        
        # Add items
        order.add_item(products[0], quantity=1)
        order.add_item(products[1], quantity=2)
        
        # Process payment
        payment = Payment(
            order_id=order.id,
            amount=order.total,
            method="credit_card"
        )
        payment.process()
        
        # Verify
        assert order.status == "paid"
        assert products[0].stock == 9
        assert products[1].stock == 48
```

### Performance Benchmark Example

```python
# testsuite/benchmark/test_bulk_operations.py
import pytest
import time
from typing import Type, List

@pytest.mark.benchmark
@pytest.mark.benchmark_bulk
@pytest.mark.usefixtures("benchmark_schema")
class TestBulkOperations:
    """Benchmark bulk database operations."""
    
    def test_bulk_insert_10k(self, user_model: Type['User'], timer):
        """Measure bulk insert performance."""
        users_data = [
            {"name": f"User{i}", "email": f"user{i}@example.com"}
            for i in range(10000)
        ]
        
        with timer:
            user_model.insert_many(users_data)
        
        # Report metric
        timer.report("bulk_insert_10k", unit="seconds")
        
        # Verify
        assert user_model.count() == 10000
    
    def test_bulk_update(self, user_model: Type['User'], timer):
        """Measure bulk update performance."""
        # Setup: Create records
        users_data = [
            {"name": f"User{i}", "email": f"user{i}@example.com"}
            for i in range(1000)
        ]
        user_model.insert_many(users_data)
        
        # Benchmark update
        with timer:
            user_model.where(id__lte=1000).update(status="active")
        
        timer.report("bulk_update_1k", unit="seconds")
```

## Backend-Specific Extensions

While the testsuite defines standard tests, backends can add their own specific tests:

```python
# rhosocial-activerecord-mysql/tests/test_mysql_specific.py
import pytest

class TestMySQLSpecific:
    """MySQL-specific feature tests."""
    
    def test_full_text_search(self):
        """Test MySQL FULLTEXT search."""
        # MySQL-specific functionality
        pass
    
    def test_spatial_queries(self):
        """Test MySQL spatial data types."""
        # MySQL-specific functionality
        pass
```

## Continuous Integration

### CI Configuration Example

```yaml
# .github/workflows/test.yml
name: Backend Testing

on: [push, pull_request]

jobs:
  test-compatibility:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.8', '3.9', '3.10', '3.11']
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: |
          pip install -e .[test]
          pip install rhosocial-activerecord-testsuite>=1.2,<1.3
      
      - name: Run backend tests
        run: pytest
      
      - name: Run testsuite compatibility
        run: pytest --run-testsuite --compat-report=console
      
      - name: Generate HTML report
        if: matrix.python-version == '3.11'
        run: |
          pytest --run-testsuite --compat-report=html
          
      - name: Upload compatibility report
        if: matrix.python-version == '3.11'
        uses: actions/upload-artifact@v3
        with:
          name: compatibility-report
          path: compatibility-report.html
```

## Best Practices

### For Testsuite Development

1. **Keep Tests Backend-Agnostic**: Don't assume specific SQL syntax
2. **Use Fixtures for Dependencies**: Declare schema requirements clearly
3. **Provide Clear Model Definitions**: Document expected fields and types
4. **Version Appropriately**: Update versions when breaking changes occur

### For Backend Implementation

1. **Match Testsuite Structure**: Keep schema organization consistent
2. **Implement All Required Fixtures**: Ensure all dependencies are provided
3. **Document Limitations**: Clearly state unsupported features
4. **Test Incrementally**: Start with feature tests before scenarios
5. **Optimize for Benchmarks**: But prioritize correctness first

### For Testing Workflow

1. **Start Local**: Test backend-specific features first
2. **Add Testsuite**: Gradually enable testsuite categories
3. **Generate Reports**: Use compatibility reports for documentation
4. **Track Progress**: Monitor compatibility scores over time
5. **Contribute Back**: Report testsuite issues or improvements