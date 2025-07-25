# Testing Guide

This document explains how to test the RhoSocial ActiveRecord package and how to develop tests for new database backends.

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Test Directory Structure](#test-directory-structure)
- [Running Tests](#running-tests)
- [Test Reports](#test-reports)
- [IDE Configuration](#ide-configuration)
- [Backend Development](#backend-development)
- [Test Organization for Backend Packages](#test-organization-for-backend-packages)
- [Test Reuse Mechanism](#test-reuse-mechanism)
- [Environment Management](#environment-management)
- [Troubleshooting](#troubleshooting)

## 🚀 Quick Start

### Getting the Code

You can obtain the code in two ways:

**Option 1: Clone Repository**
```bash
git clone https://github.com/rhosocial/python-activerecord.git
cd python-activerecord
```

**Option 2: Download ZIP**
1. Visit [GitHub Repository](https://github.com/rhosocial/python-activerecord)
2. Click "Code" → "Download ZIP"
3. Extract and navigate to the directory

### Development Environment Setup

```bash
# Install in editable mode (automatically sets up test package symlink)
pip install -e .

# Install test dependencies
pip install -e ".[test]"

# Run all tests (pytest automatically finds tests/ directory)
pytest
```

### Verify Installation

```bash
# Verify main package
python -c "import rhosocial.activerecord; print('✅ Main package OK')"

# Verify test package (available after editable installation)
python -c "from rhosocial.activerecord_test import __version__; print(f'✅ Test package OK: {__version__}')"
```

## 📁 Test Directory Structure

```
tests/rhosocial/activerecord_test/
├── backend/          # Backend-specific tests and SQLite reference implementation
├── basic/            # Basic CRUD operations
├── events/           # Lifecycle event hooks
├── fixtures/         # Global test fixtures
├── mixins/           # Built-in mixin tests (timestamps, soft delete, optimistic lock, etc.)
├── query/            # Comprehensive query functionality tests
└── relation/         # Relationship tests
```

**Directory Descriptions:**

- **backend/**: Contains backend interface compliance tests and SQLite-specific tests as reference implementation
- **basic/**: Tests for fundamental CRUD (Create, Read, Update, Delete) operations
- **events/**: Tests for lifecycle event hooks and callbacks
- **fixtures/**: Global test fixtures and utilities shared across test modules
- **mixins/**: Tests for built-in mixin classes like timestamps, soft delete, optimistic locking
- **query/**: Comprehensive query functionality including conditions, expressions, aggregates, joins, subqueries, CTEs
- **relation/**: Tests for relationship functionality (has_one, has_many, belongs_to, many_to_many)

## 🧪 Running Tests

### Command Line Testing

Due to the project using **src-layout** structure, you need to manually set the Python path:

```bash
# Linux/macOS
PYTHONPATH=src:tests:$PYTHONPATH pytest

# Windows (Command Prompt)
set PYTHONPATH=src;tests;%PYTHONPATH% && pytest

# Windows (PowerShell)
$env:PYTHONPATH="src;tests;$env:PYTHONPATH"; pytest
```

### Why Set PYTHONPATH?

The project uses **src-layout** directory structure:

```
project-root/
├── src/
│   └── rhosocial/
│       └── activerecord/     # Main package code
├── tests/
│   └── rhosocial/
│       └── activerecord_test/ # Test package code
└── pyproject.toml
```

Test files contain import statements like:
```python
from rhosocial.activerecord.interface import IActiveRecord
from rhosocial.activerecord_test.utils import DBTestConfig
```

By default, Python cannot find the `src/rhosocial` and `tests/rhosocial` packages, so these directories need to be added to `PYTHONPATH`.

### Run Specific Test Groups

```bash
# Run basic functionality tests
PYTHONPATH=src:tests:$PYTHONPATH pytest tests/rhosocial/activerecord_test/basic/

# Run backend tests
PYTHONPATH=src:tests:$PYTHONPATH pytest tests/rhosocial/activerecord_test/backend/

# Run query tests
PYTHONPATH=src:tests:$PYTHONPATH pytest tests/rhosocial/activerecord_test/query/

# Run relationship tests
PYTHONPATH=src:tests:$PYTHONPATH pytest tests/rhosocial/activerecord_test/relation/
```

### Test Options

```bash
# Verbose output
PYTHONPATH=src:tests:$PYTHONPATH pytest tests/ -v

# Show test coverage
PYTHONPATH=src:tests:$PYTHONPATH pytest tests/ --cov=rhosocial.activerecord

# Run only failed tests
PYTHONPATH=src:tests:$PYTHONPATH pytest tests/ --lf

# Stop at first failure
PYTHONPATH=src:tests:$PYTHONPATH pytest tests/ -x
```

### Parallel Test Execution

**⚠️ IMPORTANT: This project's tests are NOT suitable for parallel execution.**

While the project includes `pytest-xdist>=3.6.1` plugin as a dependency, the current test architecture prevents safe parallel execution due to the following characteristics:

#### Why Parallel Execution is Not Supported

**Table Management Conflicts:**
```python
@pytest.fixture(scope="function")
def mysql_transaction_test_db(mysql_test_db):
    """Setup and teardown for transaction tests"""
    setup_transaction_tables(mysql_test_db)  # Creates tables
    yield mysql_test_db
    teardown_transaction_tables(mysql_test_db)  # Drops tables
```

Each test fixture:
1. **Creates dedicated tables** at the start of each test
2. **Inserts test data** specific to that test
3. **Drops all tables** at the end of each test

**Database Schema Conflicts:**
- Multiple parallel processes would attempt to create/drop the same table names simultaneously
- Table creation/deletion operations cannot be safely isolated between parallel processes
- Even with different databases, the table naming scheme would cause conflicts

**Resource Contention:**
```python
def teardown_expression_tables(backend):
    """Clean up expression test tables"""
    try:
        backend.execute("DROP TABLE IF EXISTS expression_test_order_items")
        backend.execute("DROP TABLE IF EXISTS expression_test_orders") 
        backend.execute("DROP TABLE IF EXISTS expression_test_products")
        backend.execute("DROP TABLE IF EXISTS expression_test_customers")
```

#### Current Test Architecture

The project uses a **complete isolation** strategy where each test:

1. **Full Environment Setup:** Creates fresh tables and data
2. **Test Execution:** Runs the actual test logic
3. **Complete Cleanup:** Drops all tables and data

This approach ensures:
- ✅ **Complete test isolation** - No test affects another
- ✅ **Clean state guarantees** - Each test starts with known conditions  
- ✅ **Deterministic results** - No residual data affects outcomes
- ❌ **Sequential execution only** - Cannot run in parallel safely

#### Running Tests Sequentially

Use standard pytest commands without parallel options:

```bash
# Run all tests sequentially
PYTHONPATH=src:tests:$PYTHONPATH pytest tests/ -v

# Run with coverage
PYTHONPATH=src:tests:$PYTHONPATH pytest tests/ --cov=rhosocial.activerecord

# Run specific test groups
PYTHONPATH=src:tests:$PYTHONPATH pytest tests/rhosocial/activerecord_test/basic/
```

#### Future Parallel Support Considerations

To support parallel execution in the future, the test architecture would need to be redesigned with:

1. **Unique table naming per process** (e.g., `test_table_p1`, `test_table_p2`)
2. **Separate test databases per worker** 
3. **Shared fixture management** instead of per-test table creation
4. **Connection pooling coordination** between parallel processes

Currently, attempting parallel execution with `-n auto` may result in:
- Table creation/deletion conflicts
- Database connection errors  
- Inconsistent test results
- Test failures due to resource contention

### Simplifying Commands

**Method 1: Set Environment Variable**
```bash
# Linux/macOS - Add to ~/.bashrc or ~/.zshrc
export PYTHONPATH="$(pwd)/src:$(pwd)/tests:$PYTHONPATH"

# Then run directly
pytest
```

**Method 2: Use Alias**
```bash
# Linux/macOS - Add to ~/.bashrc or ~/.zshrc
alias pytest-dev='PYTHONPATH=src:tests:$PYTHONPATH pytest'

# Use alias
pytest-dev
```

**Method 3: Create Simple Script**
```bash
# Create run_tests.sh
#!/bin/bash
PYTHONPATH=src:tests:$PYTHONPATH pytest "$@"

# Use script
chmod +x run_tests.sh
./run_tests.sh
```

## 📊 Test Reports

pytest supports generating test reports in various formats for different use cases including CI/CD integration, test result analysis, and interactive visualization.

### Basic Report Formats

#### JUnit XML Reports
Generate XML reports compatible with most CI/CD systems:

```bash
# Generate JUnit XML report
PYTHONPATH=src:tests:$PYTHONPATH pytest --junit-xml=reports/junit.xml

# Specify custom report location
PYTHONPATH=src:tests:$PYTHONPATH pytest --junit-xml=test-results/junit-report.xml

# Include system properties in XML
PYTHONPATH=src:tests:$PYTHONPATH pytest --junit-xml=reports/junit.xml --junit-prefix-names
```

#### JSON Reports
Generate structured JSON test reports (requires pytest-json-report plugin):

```bash
# Install JSON report plugin
pip install pytest-json-report

# Generate JSON report
PYTHONPATH=src:tests:$PYTHONPATH pytest --json-report --json-report-file=reports/report.json

# Generate JSON report with summary only
PYTHONPATH=src:tests:$PYTHONPATH pytest --json-report --json-report-file=reports/summary.json --json-report-summary
```

#### HTML Reports
Generate detailed HTML reports (requires pytest-html plugin):

```bash
# Install HTML report plugin
pip install pytest-html

# Generate HTML report
PYTHONPATH=src:tests:$PYTHONPATH pytest --html=reports/report.html --self-contained-html

# Generate HTML report with custom CSS
PYTHONPATH=src:tests:$PYTHONPATH pytest --html=reports/report.html --css=custom.css
```

### Coverage Reports Integration

Combine test reports with coverage analysis:

```bash
# HTML coverage + test report
PYTHONPATH=src:tests:$PYTHONPATH pytest \
    --cov=rhosocial.activerecord \
    --cov-report=html:htmlcov \
    --html=reports/report.html \
    --self-contained-html

# XML coverage + JUnit XML
PYTHONPATH=src:tests:$PYTHONPATH pytest \
    --cov=rhosocial.activerecord \
    --cov-report=xml:coverage.xml \
    --junit-xml=reports/junit.xml

# Terminal coverage + JSON report
PYTHONPATH=src:tests:$PYTHONPATH pytest \
    --cov=rhosocial.activerecord \
    --cov-report=term-missing \
    --json-report \
    --json-report-file=reports/test-results.json
```

### Interactive Test Reports with Allure

Allure Framework provides rich interactive test reports with detailed test execution information, attachments, and historical trends.

#### Installation and Setup

```bash
# Install Allure pytest plugin
pip install allure-pytest

# Install Allure command-line tool (choose one method):

# Method 1: Using npm (requires Node.js)
npm install -g allure-commandline

# Method 2: Using pip
pip install allure-pytest-bdd

# Method 3: Download from GitHub releases
# Visit: https://github.com/allure-framework/allure2/releases
# Extract to your PATH

# Method 4: Using package managers
# macOS: brew install allure
# Ubuntu: sudo apt-get install allure
```

#### Generating Allure Reports

```bash
# Generate Allure test results
PYTHONPATH=src:tests:$PYTHONPATH pytest --alluredir=allure-results

# Generate and serve Allure report
allure serve allure-results

# Generate static Allure report
allure generate allure-results --output allure-report --clean

# Open generated report
allure open allure-report
```

#### Advanced Allure Features

Add rich information to Allure reports using decorators and functions:

```python
# tests/rhosocial/activerecord_mysql_test/basic/test_crud_with_allure.py
import allure
import pytest
from decimal import Decimal


@allure.epic("MySQL Backend")
@allure.feature("Basic CRUD Operations") 
@allure.story("User Management")
class TestMySQLCRUDWithAllure:
    
    @allure.title("Create new user record with MySQL backend")
    @allure.description("Test creating a new user with MySQL-specific features")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_create_user_mysql(self, user_class):
        with allure.step("Prepare user data"):
            user_data = {
                'username': 'mysql_testuser',
                'email': 'mysql_test@example.com',
                'age': 25,
                'balance': Decimal('100.00')
            }
            allure.attach(str(user_data), name="User Data", attachment_type=allure.attachment_type.JSON)
        
        with allure.step("Create user instance"):
            user = user_class(**user_data)
        
        with allure.step("Save user to MySQL database"):
            result = user.save()
            allure.attach(str(result), name="Save Result", attachment_type=allure.attachment_type.TEXT)
        
        with allure.step("Verify MySQL AUTO_INCREMENT behavior"):
            assert result == 1
            assert user.id is not None
            allure.attach(str(user.id), name="Generated User ID", attachment_type=allure.attachment_type.TEXT)
        
        with allure.step("Verify MySQL timestamp defaults"):
            assert user.created_at is not None
            assert user.updated_at is not None
            allure.attach(str(user.created_at), name="Created At", attachment_type=allure.attachment_type.TEXT)

    @allure.title("Test MySQL JSON field operations")
    @allure.description("Test MySQL-specific JSON field functionality")
    @allure.severity(allure.severity_level.NORMAL)
    def test_mysql_json_operations(self, type_case_class):
        with allure.step("Prepare JSON data"):
            json_data = {"profile": {"age": 30, "city": "New York"}, "tags": ["mysql", "json"]}
            allure.attach(str(json_data), name="JSON Data", attachment_type=allure.attachment_type.JSON)
        
        with allure.step("Create record with JSON field"):
            record = type_case_class(
                username='json_test',
                email='json@test.com',
                json_val=json_data
            )
            record.save()
        
        with allure.step("Retrieve and verify JSON data"):
            retrieved = type_case_class.find_one(record.id)
            assert retrieved.json_val == json_data
            allure.attach(str(retrieved.json_val), name="Retrieved JSON", attachment_type=allure.attachment_type.JSON)

    @allure.title("Test MySQL DECIMAL precision handling")
    @allure.description("Test MySQL DECIMAL field precision and scale")
    @allure.severity(allure.severity_level.NORMAL)
    def test_mysql_decimal_precision(self, type_case_class):
        with allure.step("Test high precision decimal values"):
            test_values = [
                Decimal('999999.9999'),
                Decimal('0.0001'),
                Decimal('123456.7890')
            ]
            
            for decimal_val in test_values:
                with allure.step(f"Test decimal value: {decimal_val}"):
                    record = type_case_class(
                        username=f'decimal_test_{decimal_val}',
                        email=f'decimal_{decimal_val}@test.com',
                        decimal_val=decimal_val
                    )
                    record.save()
                    
                    retrieved = type_case_class.find_one(record.id)
                    assert retrieved.decimal_val == decimal_val
                    allure.attach(
                        f"Expected: {decimal_val}, Actual: {retrieved.decimal_val}",
                        name=f"Decimal Precision Test {decimal_val}",
                        attachment_type=allure.attachment_type.TEXT
                    )
```

#### Backend-Specific Allure Configuration

Create backend-specific Allure properties:

```properties
# tests/rhosocial/activerecord_mysql_test/allure.properties
allure.results.directory=allure-results-mysql
allure.link.issue.pattern=https://github.com/rhosocial/python-activerecord-mysql/issues/{}
allure.link.tms.pattern=https://your-test-management-system.com/mysql/{}

# Custom categories for MySQL-specific tests
allure.categories.json={
  "name": "MySQL Backend Issues",
  "matchedStatuses": ["failed", "broken"],
  "messageRegex": ".*mysql.*|.*MySQL.*"
}
```

#### CI/CD Integration with Backend Reports

Example GitHub Actions workflow for generating reports across multiple backends:

```yaml
# .github/workflows/mysql-test-reports.yml
name: MySQL Backend Test Reports

on: [push, pull_request]

jobs:
  mysql-test-reports:
    runs-on: ubuntu-latest
    
    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: root
          MYSQL_DATABASE: test_activerecord_mysql
          MYSQL_USER: test_user
          MYSQL_PASSWORD: test_password
        ports:
          - 3306:3306
        options: --health-cmd="mysqladmin ping" --health-interval=10s --health-timeout=5s --health-retries=3
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install -e ".[test]"
        pip install pytest-html pytest-json-report allure-pytest
        # Install MySQL-specific dependencies
        pip install -e ../rhosocial-activerecord-mysql
    
    - name: Run MySQL backend tests with reports
      run: |
        mkdir -p reports
        PYTHONPATH=src:tests:$PYTHONPATH pytest \
          tests/rhosocial/activerecord_mysql_test/ \
          --junit-xml=reports/mysql-junit.xml \
          --html=reports/mysql-report.html \
          --self-contained-html \
          --json-report \
          --json-report-file=reports/mysql-report.json \
          --alluredir=allure-results-mysql \
          --cov=rhosocial.activerecord_mysql \
          --cov-report=xml:reports/mysql-coverage.xml \
          --cov-report=html:reports/mysql-htmlcov
    
    - name: Run Core compatibility tests
      run: |
        PYTHONPATH=src:tests:$PYTHONPATH pytest \
          tests/rhosocial/activerecord_test/basic/ \
          tests/rhosocial/activerecord_test/query/ \
          --junit-xml=reports/core-compatibility.xml \
          --html=reports/core-compatibility.html \
          --self-contained-html
    
    - name: Generate MySQL Allure Report
      if: always()
      run: |
        wget -O allure-commandline.tgz https://github.com/allure-framework/allure2/releases/download/2.24.1/allure-2.24.1.tgz
        tar -xzf allure-commandline.tgz
        ./allure-2.24.1/bin/allure generate allure-results-mysql --output allure-report-mysql --clean
    
    - name: Upload MySQL Test Reports
      if: always()
      uses: actions/upload-artifact@v4
      with:
        name: mysql-test-reports
        path: |
          reports/
          allure-report-mysql/
    
    - name: Publish MySQL Test Results
      if: always()
      uses: dorny/test-reporter@v1
      with:
        name: MySQL Backend Test Results
        path: reports/mysql-junit.xml
        reporter: java-junit
```

### Report Analysis and Best Practices

#### Backend-Specific Report Organization

```bash
# Organize reports by backend and timestamp
BACKEND="mysql"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_DIR="reports/${BACKEND}/${TIMESTAMP}"
mkdir -p "${REPORT_DIR}"

# Run backend-specific tests with organized reports
PYTHONPATH=src:tests:$PYTHONPATH pytest \
    tests/rhosocial/activerecord_${BACKEND}_test/ \
    --junit-xml="${REPORT_DIR}/junit.xml" \
    --html="${REPORT_DIR}/report.html" \
    --alluredir="${REPORT_DIR}/allure-results" \
    --cov=rhosocial.activerecord_${BACKEND} \
    --cov-report=html:${REPORT_DIR}/htmlcov

# Archive old reports (keep last 5 for each backend)
find reports/${BACKEND}/ -maxdepth 1 -type d -name "20*" | sort -r | tail -n +6 | xargs rm -rf
```

#### Cross-Backend Report Comparison

```python
# scripts/compare_backend_reports.py
import json
import xml.etree.ElementTree as ET
from pathlib import Path


def compare_backend_test_results(core_junit: Path, backend_junit: Path) -> dict:
    """Compare test results between core and backend implementations"""
    
    def parse_junit_results(junit_path: Path) -> dict:
        tree = ET.parse(junit_path)
        root = tree.getroot()
        
        results = {}
        for testcase in root.findall('.//testcase'):
            test_name = testcase.get('name')
            class_name = testcase.get('classname')
            full_name = f"{class_name}::{test_name}"
            
            if testcase.find('failure') is not None:
                results[full_name] = 'failed'
            elif testcase.find('error') is not None:
                results[full_name] = 'error'
            elif testcase.find('skipped') is not None:
                results[full_name] = 'skipped'
            else:
                results[full_name] = 'passed'
        
        return results
    
    core_results = parse_junit_results(core_junit)
    backend_results = parse_junit_results(backend_junit)
    
    # Find tests that exist in core but not in backend
    missing_tests = set(core_results.keys()) - set(backend_results.keys())
    
    # Find tests with different outcomes
    different_outcomes = {}
    for test_name in core_results:
        if test_name in backend_results:
            if core_results[test_name] != backend_results[test_name]:
                different_outcomes[test_name] = {
                    'core': core_results[test_name],
                    'backend': backend_results[test_name]
                }
    
    return {
        'missing_tests': list(missing_tests),
        'different_outcomes': different_outcomes,
        'total_core_tests': len(core_results),
        'total_backend_tests': len(backend_results),
        'compatibility_score': (len(backend_results) - len(different_outcomes)) / len(core_results) * 100
    }


# Usage example
comparison = compare_backend_test_results(
    Path('reports/core/junit.xml'),
    Path('reports/mysql/junit.xml')
)
print(f"Backend compatibility score: {comparison['compatibility_score']:.1f}%")
```

## 🔧 IDE Configuration

### PyCharm Configuration

To properly use test functionality in PyCharm, follow these configuration steps:

1. **Configure Project Structure**:
   - Open **File → Settings → Project → Project Structure**
   - Right-click `src` folder → Select **Mark as Sources** (marked in blue)
   - Right-click `tests` folder → Select **Mark as Test Sources** (marked in green)

2. **Configure Test Runner**:
   - Go to **File → Settings → Tools → Python Integrated Tools**
   - Set **Default test runner** to **pytest**
   - Set **Working directory** to project root directory

3. **Run Tests**:
   - Right-click test file or test function → Select **Run 'pytest in ...'**
   - Or use PyCharm's test window to manage tests

After configuration, PyCharm will be able to:
- Correctly recognize import statements
- Provide code completion and navigation
- Display test structure in the test window
- Support debugging test code

### VSCode Configuration

If using VSCode, it's recommended to configure in `.vscode/settings.json`:

```json
{
    "python.analysis.extraPaths": [
        "./src",
        "./tests"
    ],
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": [
        "tests"
    ]
}
```

Looking at the current TESTING.md, I need to adjust the "Backend Development" section to align with your preferred directory structure. Here are the modified sections:

## 🔧 Backend Development

### Developing New Database Backends

If you're developing a new database backend for RhoSocial ActiveRecord, you can reuse the existing test suite to ensure compatibility.

### Test Requirements

To ensure your backend is fully compatible with RhoSocial ActiveRecord:

| Test Category | Relational DB | Non-Relational DB | Description |
|---------------|---------------|-------------------|-------------|
| **backend/** | 🔴 Required | 🟡 Recommended | Backend interface compliance |
| **basic/** | 🔴 Required | 🔴 Required | Basic CRUD operations |
| **events/** | 🔴 Required | 🟡 Optional | Lifecycle event hooks |
| **fixtures/** | 🔴 Required | 🔴 Required | Test infrastructure |
| **mixins/** | 🔴 Required | 🟡 Optional | Built-in mixins support |
| **query/** | 🔴 Required | 🟡 Partial | Query functionality |
| **relation/** | 🔴 Required | ❌ Not Applicable | Relationship support |

**For Relational Databases**: We recommend satisfying **all** test categories.

**For Non-Relational Databases**: You may satisfy only **backend/**, **basic/**, **events/** or parts of them, depending on your database's capabilities.

### Example Backend Test Package Structure

```
rhosocial-activerecord-mysql/
├── src/rhosocial/activerecord_mysql/
│   ├── backend.py        # MySQL backend implementation
│   └── connection.py     # MySQL connection management
├── tests/rhosocial/activerecord_mysql_test/
│   ├── backend/                # Backend-specific tests  
│   │   ├── __init__.py
│   │   ├── test_mysql_backend.py        # MySQL backend specific features
│   │   ├── test_mysql_connection.py     # MySQL connection specific features
│   │   └── fixtures/
│   │       ├── __init__.py
│   │       └── models.py
│   ├── basic/                  # Basic CRUD operations (reused + MySQL specific)
│   │   ├── __init__.py
│   │   ├── conftest.py         # pytest configuration
│   │   ├── test_crud.py        # Reuse core CRUD tests + MySQL specific CRUD features
│   │   ├── test_fields.py      # Reuse field tests + MySQL specific field types
│   │   ├── test_validation.py  # Reuse validation tests + MySQL specific validation
│   │   ├── test_mysql_crud.py  # Pure MySQL specific CRUD features (if separate file needed)
│   │   └── fixtures/
│   │       ├── __init__.py
│   │       ├── models.py       # MySQL specific test models
│   │       └── schema/
│   │           └── mysql/      # MySQL schema files
│   │               ├── users.sql
│   │               ├── type_cases.sql
│   │               └── ...
│   ├── events/                 # Lifecycle events (reused + MySQL specific)
│   │   ├── __init__.py
│   │   ├── test_lifecycle.py   # Reuse lifecycle tests
│   │   ├── test_mysql_triggers.py      # MySQL trigger specific features
│   │   └── fixtures/
│   │       ├── __init__.py
│   │       └── models.py
│   ├── fixtures/               # Global test fixtures
│   │   ├── __init__.py
│   │   ├── models.py           # Global MySQL test models
│   │   ├── connection.py       # MySQL test database setup
│   │   └── schema/
│   │       └── mysql/
│   ├── mixins/                 # Built-in mixin tests (reused + MySQL specific)
│   │   ├── __init__.py
│   │   ├── test_timestamps.py  # Reuse timestamp tests
│   │   ├── test_soft_delete.py # Reuse soft delete tests
│   │   ├── test_mysql_json_mixin.py    # MySQL JSON mixin specific features
│   │   └── fixtures/
│   │       ├── __init__.py
│   │       └── models.py
│   ├── query/                  # Query functionality (reused + MySQL specific)
│   │   ├── __init__.py
│   │   ├── test_conditions.py  # Reuse condition query tests
│   │   ├── test_expressions.py # Reuse expression tests
│   │   ├── test_aggregates.py  # Reuse aggregate tests + MySQL specific aggregate functions
│   │   ├── test_joins.py       # Reuse join tests
│   │   ├── test_subqueries.py  # Reuse subquery tests
│   │   ├── test_mysql_fulltext.py      # MySQL full-text search specific features
│   │   ├── test_mysql_json_ops.py      # MySQL JSON operations specific features
│   │   ├── test_mysql_window.py        # MySQL window functions specific features  
│   │   └── fixtures/
│   │       ├── __init__.py
│   │       └── models.py
│   ├── relation/               # Relation functionality (reused + MySQL specific)
│   │   ├── __init__.py
│   │   ├── test_has_one.py     # Reuse one-to-one relation tests
│   │   ├── test_has_many.py    # Reuse one-to-many relation tests
│   │   ├── test_belongs_to.py  # Reuse belongs-to relation tests
│   │   ├── test_many_to_many.py # Reuse many-to-many relation tests
│   │   ├── test_mysql_foreign_keys.py  # MySQL foreign key specific features
│   │   └── fixtures/
│   │       ├── __init__.py
│   │       └── models.py
│   └── utils.py                # MySQL backend configuration
└── pyproject.toml
```

### MySQL-Specific Features Integration

Tests for database-specific functionality are integrated into each functional directory:

```python
# tests/rhosocial/activerecord_mysql_test/basic/test_crud.py
"""Basic CRUD operations for MySQL backend with core test reuse"""

# Import and reuse core test functions
from rhosocial.activerecord_test.basic.test_crud import (
    test_create_user as _test_create_user,
    test_find_user as _test_find_user,
    test_update_user as _test_update_user,
    test_delete_user as _test_delete_user,
)

from .fixtures.models import user_class


# Reuse core test functions
def test_create_user(user_class):
    """Test creating a user record with MySQL backend"""
    return _test_create_user(user_class)


def test_find_user(user_class):
    """Test finding a user record with MySQL backend"""
    return _test_find_user(user_class)


# MySQL-specific CRUD tests
def test_mysql_auto_increment_behavior(user_class):
    """Test MySQL AUTO_INCREMENT specific behavior"""
    # Create multiple users to test auto-increment sequence
    users = []
    for i in range(3):
        user = user_class(username=f'user_{i}', email=f'user_{i}@example.com')
        user.save()
        users.append(user)
    
    # Verify auto-increment IDs are sequential
    assert users[1].id == users[0].id + 1
    assert users[2].id == users[1].id + 1


def test_mysql_timestamp_default_behavior(user_class):
    """Test MySQL TIMESTAMP DEFAULT CURRENT_TIMESTAMP behavior"""
    user = user_class(username='timestamp_test', email='test@example.com')
    user.save()
    
    # Verify MySQL automatically set timestamps
    assert user.created_at is not None
    assert user.updated_at is not None
```

```python
# tests/rhosocial/activerecord_mysql_test/query/test_mysql_json_ops.py
"""MySQL-specific JSON operations tests"""
import pytest
from decimal import Decimal

from .fixtures.models import mysql_json_model_class


class TestMySQLJSONOperations:
    """Test MySQL-specific JSON column operations"""
    
    def test_json_extract_operator(self, mysql_json_model_class):
        """Test MySQL JSON_EXTRACT operator"""
        model = mysql_json_model_class(
            username='json_test',
            email='json@test.com',
            metadata={'profile': {'age': 25, 'city': 'New York'}}
        )
        model.save()
        
        # Query using JSON_EXTRACT
        result = mysql_json_model_class.where(
            "JSON_EXTRACT(metadata, '$.profile.age') = %s", [25]
        ).first()
        
        assert result is not None
        assert result.metadata['profile']['age'] == 25
    
    def test_json_array_operations(self, mysql_json_model_class):
        """Test MySQL JSON array operations"""
        model = mysql_json_model_class(
            username='json_array_test',
            email='array@test.com',
            metadata={'tags': ['python', 'mysql', 'json']}
        )
        model.save()
        
        # Query using JSON_CONTAINS
        result = mysql_json_model_class.where(
            "JSON_CONTAINS(metadata->'$.tags', %s)", ['"python"']
        ).first()
        
        assert result is not None
        assert 'python' in result.metadata['tags']
```

## 📦 Test Organization for Backend Packages

### Core Test Reuse Strategy

Backend-specific packages reuse core test functions while adding database-specific functionality:

```python
# tests/rhosocial/activerecord_mysql_test/basic/test_fields.py
"""Field type handling tests for MySQL backend"""

# Import and reuse core field tests
from rhosocial.activerecord_test.basic.test_fields import (
    test_string_field_handling as _test_string_field_handling,
    test_numeric_field_handling as _test_numeric_field_handling,
    test_datetime_field_handling as _test_datetime_field_handling,
)

# Import MySQL-specific fixtures
from .fixtures.models import type_case_class


# Reuse core field tests
def test_string_field_handling(type_case_class):
    """Test string field handling with MySQL backend"""
    return _test_string_field_handling(type_case_class)


def test_numeric_field_handling(type_case_class):
    """Test numeric field handling with MySQL backend"""
    return _test_numeric_field_handling(type_case_class)


# MySQL-specific field tests
def test_mysql_json_field_handling(type_case_class):
    """Test MySQL native JSON field type"""
    test_json = {"name": "John", "scores": [85, 92, 78]}
    
    model = type_case_class(
        username='json_test',
        email='json@test.com',
        json_val=test_json
    )
    model.save()
    
    retrieved = type_case_class.find_one(model.id)
    assert retrieved.json_val == test_json
    assert isinstance(retrieved.json_val, dict)


def test_mysql_decimal_precision_handling(type_case_class):
    """Test MySQL DECIMAL precision handling"""
    from decimal import Decimal
    
    model = type_case_class(
        username='decimal_test',
        email='decimal@test.com',
        decimal_val=Decimal('999999.9999')
    )
    model.save()
    
    retrieved = type_case_class.find_one(model.id)
    assert retrieved.decimal_val == Decimal('999999.9999')
```

### Backend-Specific Model Configuration

```python
# tests/rhosocial/activerecord_mysql_test/fixtures/models.py
"""MySQL-specific test model fixtures"""
import pytest
from rhosocial.activerecord_test.fixtures.models import (
    User as BaseUser,
    TypeCase as BaseTypeCase,
    ValidatedUser as BaseValidatedUser,
)
from rhosocial.activerecord_test.utils import create_active_record_fixture


class MySQLUser(BaseUser):
    """MySQL-specific user model"""
    __supported_backends__ = ["mysql"]  # Restrict to MySQL only
    __table_name__ = "mysql_users"


class MySQLTypeCase(BaseTypeCase):
    """MySQL-specific type case model with additional MySQL fields"""
    __supported_backends__ = ["mysql"]
    __table_name__ = "mysql_type_cases"
    
    # Additional MySQL-specific fields would be defined here
    # json_val: JSON field
    # enum_val: ENUM field  
    # set_val: SET field


class MySQLValidatedUser(BaseValidatedUser):
    """MySQL-specific validated user model"""
    __supported_backends__ = ["mysql"]
    __table_name__ = "mysql_validated_users"


# Create MySQL-specific fixtures
user_class = create_active_record_fixture(MySQLUser)
type_case_class = create_active_record_fixture(MySQLTypeCase)
validated_user_class = create_active_record_fixture(MySQLValidatedUser)
```

### Test Reuse Through Backend Configuration

The core mechanism for test reuse relies on:

1. **Model Restriction**: Set `__supported_backends__ = ["mysql"]` on model classes
2. **Fixture Creation**: Use `create_active_record_fixture(Model)` to create backend-specific fixtures
3. **Automatic Backend Selection**: Fixtures automatically use the correct backend
4. **Function Import**: Import and call core test functions directly in backend-specific test files

### Test Package Naming Convention

| Package Type | Test Package Name | Purpose |
|-------------|-------------------|---------|
| Main Package | `activerecord_test` | Core test suite and utilities |
| MySQL Package | `activerecord_mysql_test` | MySQL-specific tests and compatibility |
| PostgreSQL Package | `activerecord_pgsql_test` | PostgreSQL-specific tests and compatibility |
| MariaDB Package | `activerecord_mariadb_test` | MariaDB-specific tests and compatibility |

## 🔗 Test Reuse Mechanism

### Symlink Mechanism

When you install in editable mode:

```bash
pip install -e .
```

The installation process automatically creates a symlink:

```
src/rhosocial/activerecord_test -> tests/rhosocial/activerecord_test/
```

This allows:
- Test packages to import main package code
- Backend test packages to import and reuse core test functions
- IDE support for test development and debugging

### Backend Registration

Backend test packages register their database configurations:

```python
# tests/rhosocial/activerecord_mysql_test/utils.py
"""MySQL backend configuration for tests"""

from rhosocial.activerecord_test.utils import register_backend_config

# MySQL test database configuration
MYSQL_CONFIGS = {
    'mysql': {
        'engine': 'mysql',
        'host': 'localhost',
        'port': 3306,
        'database': 'test_activerecord',
        'username': 'test_user',
        'password': 'test_password',
        'options': {
            'charset': 'utf8mb4',
            'autocommit': True
        }
    }
}

# Register MySQL backend for test discovery
register_backend_config('mysql', MYSQL_CONFIGS['mysql'])
```

### Core Test Function Reuse

Backend packages reuse core test functions by importing them directly into functional test modules:

```python
# tests/rhosocial/activerecord_mysql_test/basic/test_crud.py
"""Basic CRUD operations for MySQL backend"""

# Import core test functions to reuse
from rhosocial.activerecord_test.basic.test_crud import (
    test_create_user as _test_create_user,
    test_find_user as _test_find_user,
    test_update_user as _test_update_user,
    test_delete_user as _test_delete_user,
)

# Import MySQL-specific fixtures
from .fixtures.models import user_class


# Wrapper functions that reuse core tests
def test_create_user(user_class):
    """Test creating a user record with MySQL backend"""
    return _test_create_user(user_class)


def test_find_user(user_class):
    """Test finding a user record with MySQL backend"""
    return _test_find_user(user_class)


def test_update_user(user_class):
    """Test updating a user record with MySQL backend"""
    return _test_update_user(user_class)


def test_delete_user(user_class):
    """Test deleting a user record with MySQL backend"""
    return _test_delete_user(user_class)


# MySQL-specific additional tests
def test_mysql_auto_increment_behavior(user_class):
    """Test MySQL AUTO_INCREMENT specific behavior"""
    # MySQL-specific test implementation
    pass


def test_mysql_timestamp_default_behavior(user_class):
    """Test MySQL TIMESTAMP DEFAULT CURRENT_TIMESTAMP behavior"""
    # MySQL-specific test implementation
    pass
```

```python
# tests/rhosocial/activerecord_mysql_test/query/test_conditions.py
"""Query conditions for MySQL backend"""

# Import and reuse core query condition tests
from rhosocial.activerecord_test.query.test_conditions import (
    test_where_conditions as _test_where_conditions,
    test_complex_conditions as _test_complex_conditions,
    test_null_conditions as _test_null_conditions,
)

# Import MySQL-specific fixtures
from .fixtures.models import query_test_class


# Reuse core query tests
def test_where_conditions(query_test_class):
    """Test WHERE conditions with MySQL backend"""
    return _test_where_conditions(query_test_class)


def test_complex_conditions(query_test_class):
    """Test complex conditions with MySQL backend"""
    return _test_complex_conditions(query_test_class)


# MySQL-specific query tests
def test_mysql_fulltext_search(query_test_class):
    """Test MySQL FULLTEXT search functionality"""
    # MySQL-specific FULLTEXT search tests
    pass


def test_mysql_json_path_queries(query_test_class):
    """Test MySQL JSON path query conditions"""
    # MySQL-specific JSON query tests
    pass
```

### Backend-Specific Model Configuration

Create MySQL-specific models that inherit from core models:

```python
# tests/rhosocial/activerecord_mysql_test/basic/fixtures/models.py
"""MySQL-specific test model fixtures for basic functionality"""

from rhosocial.activerecord_test.fixtures.models import (
    User as BaseUser,
    TypeCase as BaseTypeCase,
    ValidatedUser as BaseValidatedUser,
)
from rhosocial.activerecord_test.utils import create_active_record_fixture


class MySQLUser(BaseUser):
    """MySQL-specific user model"""
    __supported_backends__ = ["mysql"]
    __table_name__ = "mysql_users"
    
    class Meta:
        table_options = {
            'ENGINE': 'InnoDB',
            'DEFAULT CHARSET': 'utf8mb4',
            'COLLATE': 'utf8mb4_unicode_ci'
        }


class MySQLTypeCase(BaseTypeCase):
    """MySQL-specific type case model"""
    __supported_backends__ = ["mysql"]
    __table_name__ = "mysql_type_cases"
    
    # Additional MySQL-specific fields can be defined here
    class Meta:
        table_options = {
            'ENGINE': 'InnoDB',
            'DEFAULT CHARSET': 'utf8mb4',
            'COLLATE': 'utf8mb4_unicode_ci'
        }


class MySQLValidatedUser(BaseValidatedUser):
    """MySQL-specific validated user model"""
    __supported_backends__ = ["mysql"]
    __table_name__ = "mysql_validated_users"


# Create MySQL-specific fixtures
user_class = create_active_record_fixture(MySQLUser)
type_case_class = create_active_record_fixture(MySQLTypeCase)
validated_user_class = create_active_record_fixture(MySQLValidatedUser)
```

### Test Discovery and Execution

The test reuse mechanism works through:

1. **Backend Model Restriction**: Models specify `__supported_backends__ = ["mysql"]`
2. **Fixture Creation**: `create_active_record_fixture()` creates backend-specific test fixtures
3. **Automatic Backend Selection**: pytest fixtures automatically use the correct backend
4. **Function Import**: Core test functions are imported and called with backend-specific fixtures

### Running Backend-Specific Tests

```bash
# Run all MySQL basic tests (both reused and MySQL-specific)
PYTHONPATH=src:tests:$PYTHONPATH pytest tests/rhosocial/activerecord_mysql_test/basic/

# Run specific MySQL test module
PYTHONPATH=src:tests:$PYTHONPATH pytest tests/rhosocial/activerecord_mysql_test/basic/test_crud.py

# Run MySQL-specific query tests
PYTHONPATH=src:tests:$PYTHONPATH pytest tests/rhosocial/activerecord_mysql_test/query/

# Run only MySQL-specific functionality (not reused tests)
PYTHONPATH=src:tests:$PYTHONPATH pytest tests/rhosocial/activerecord_mysql_test/ -k "mysql_"
```

### Cross-Backend Test Validation

Verify compatibility across multiple backends:

```bash
# Run core tests with all available backends
PYTHONPATH=src:tests:$PYTHONPATH pytest tests/rhosocial/activerecord_test/basic/

# Run MySQL-specific tests to ensure backend compatibility
PYTHONPATH=src:tests:$PYTHONPATH pytest tests/rhosocial/activerecord_mysql_test/basic/

# Compare test results between core and backend implementations
PYTHONPATH=src:tests:$PYTHONPATH pytest \
    tests/rhosocial/activerecord_test/basic/test_crud.py \
    tests/rhosocial/activerecord_mysql_test/basic/test_crud.py \
    --junit-xml=reports/comparison.xml
```

## 🏗️ Environment Management

### Development Installation

The project uses **editable installation** to set up the development environment:

```bash
# Install main package in editable mode
pip install -e .

# Install with test dependencies
pip install -e ".[test]"

# Install with all optional dependencies
pip install -e ".[test,dev,docs]"
```

### What Happens During Editable Installation

1. **Package Registration**: The main package is registered with pip
2. **Symlink Creation**: A symlink is created: `src/rhosocial/activerecord_test -> tests/rhosocial/activerecord_test/`
3. **Path Setup**: The `src/` directory is added to Python's module search path
4. **Import Support**: Both main and test packages become importable

### Environment Verification

```bash
# Check if packages are importable
python -c "
import rhosocial.activerecord
import rhosocial.activerecord_test
print('✅ Environment setup successful')
"

# Check symlink status (Linux/macOS)
ls -la src/rhosocial/activerecord_test

# Expected output: src/rhosocial/activerecord_test -> tests/rhosocial/activerecord_test/
```

### Cleaning Development Environment

When uninstalling or switching environments:

```bash
# Uninstall package
pip uninstall rhosocial-activerecord

# Symlink still exists!
ls -la src/rhosocial/activerecord_test  # Still visible

# Manual cleanup required
rm src/rhosocial/activerecord_test
```

### Cleanup Script

```bash
#!/bin/bash
# clean_dev_environment.sh

echo "🧹 Cleaning development environment..."

# Uninstall package
pip uninstall rhosocial-activerecord -y

# Clean symlink
if [ -L "src/rhosocial/activerecord_test" ]; then
    rm "src/rhosocial/activerecord_test"
    echo "✅ Cleaned test package symlink"
fi

# Clean build files
rm -rf build/ dist/ *.egg-info/
echo "✅ Cleaned build files"

echo "🎉 Development environment cleanup complete"
```

## 🐛 Troubleshooting

### Common Issues

#### 1. Cannot Import Test Package

```python
ImportError: No module named 'rhosocial.activerecord_test'
```

**Solution:**
```bash
# Check if editable installation
pip list | grep rhosocial-activerecord

# If shows path, it's editable mode, check symlink
ls -la src/rhosocial/activerecord_test

# If symlink doesn't exist, reinstall
pip install -e .
```

#### 2. Invalid Symlink

```bash
ls: src/rhosocial/activerecord_test: No such file or directory
```

**Solution:**
```bash
# Create symlink manually
ln -sf tests/rhosocial/activerecord_test src/rhosocial/activerecord_test

# Or reinstall
pip uninstall rhosocial-activerecord -y
pip install -e .
```

#### 3. Test Dependencies Missing

```
ModuleNotFoundError: No module named 'pytest'
```

**Solution:**
```bash
# Install test dependencies
pip install -e ".[test]"

# Or install individually
pip install pytest pytest-asyncio pytest-cov coverage
```

#### 4. Command Line Import Errors

```
ModuleNotFoundError: No module named 'rhosocial'
```

**Solution:**
Ensure you're using the PYTHONPATH prefix:
```bash
PYTHONPATH=src:tests:$PYTHONPATH pytest
```

#### 5. PyCharm Test Runner Issues

**Symptoms**: Right-click test file shows no run options

**Solution:**
1. Ensure `src` and `tests` directories are properly marked
2. Check Python interpreter configuration  
3. Verify pytest is installed in current interpreter

#### 6. Backend Configuration Not Found

```
KeyError: 'mysql'
```

**Solution:**
Ensure your backend's `utils.py` is imported before running tests:
```python
# In test file or conftest.py
from rhosocial.activerecord_mysql_test.utils import MYSQL_CONFIGS  # This registers MySQL backend
```

#### 7. Backend-Specific Test Import Issues

```python
ImportError: cannot import name 'test_create_user' from 'rhosocial.activerecord_test.basic.test_crud'
```

**Solution:**
Verify the core test function exists and is properly named:
```bash
# Check what's available in the core test module
python -c "
from rhosocial.activerecord_test.basic import test_crud
print(dir(test_crud))
"

# Run a simple import test
python -c "
from rhosocial.activerecord_test.basic.test_crud import test_create_user
print('✅ Import successful')
"
```

#### 8. Backend Model Configuration Issues

```python
AttributeError: 'MySQLUser' object has no attribute '__supported_backends__'
```

**Solution:**
Ensure your backend models properly inherit and configure supported backends:
```python
# Correct backend model configuration
class MySQLUser(BaseUser):
    __supported_backends__ = ["mysql"]  # Required
    __table_name__ = "mysql_users"     # Recommended
    
    class Meta:
        table_options = {
            'ENGINE': 'InnoDB',
            'DEFAULT CHARSET': 'utf8mb4'
        }
```

#### 9. Test Fixture Configuration Problems

```python
fixture 'user_class' not found
```

**Solution:**
Verify your fixtures are properly configured in the test module:
```python
# tests/rhosocial/activerecord_mysql_test/basic/test_crud.py

# Ensure this import exists - it's needed as fixture, do not remove
from .fixtures.models import user_class, type_case_class, validated_user_class
```

#### 10. Database Connection Issues for Backend Tests

```python
DatabaseConnectionError: Can't connect to MySQL server on 'localhost'
```

**Solution:**
Verify your database configuration and connection:
```python
# Check MySQL connection configuration
from rhosocial.activerecord_mysql_test.utils import MYSQL_CONFIGS
print(MYSQL_CONFIGS)

# Test database connection manually
import mysql.connector
try:
    conn = mysql.connector.connect(
        host='localhost',
        port=3306,
        database='test_activerecord_mysql',
        user='test_user',
        password='test_password'
    )
    print("✅ Database connection successful")
    conn.close()
except Exception as e:
    print(f"❌ Database connection failed: {e}")
```

#### 11. Report Generation Failures

**Allure command not found:**
```bash
# Install Allure CLI
npm install -g allure-commandline
# or download from GitHub releases
```

**Missing report plugins:**
```bash
# Install required plugins
pip install pytest-html pytest-json-report allure-pytest
```

**Report directory permissions:**
```bash
# Ensure report directories are writable
mkdir -p reports allure-results
chmod 755 reports allure-results
```

#### 12. Core Test Function Reuse Issues

```python
TypeError: test_create_user() missing 1 required positional argument: 'user_class'
```

**Solution:**
Ensure you're calling the imported test function correctly:
```python
# Incorrect - calling function directly
from rhosocial.activerecord_test.basic.test_crud import test_create_user
test_create_user()  # ❌ Missing user_class argument

# Correct - wrapper function with fixture
from rhosocial.activerecord_test.basic.test_crud import test_create_user as _test_create_user
from .fixtures.models import user_class

def test_create_user(user_class):
    """Test creating a user record with MySQL backend"""
    return _test_create_user(user_class)  # ✅ Pass fixture to core function
```

#### 13. Conflicting Test Names

```python
FAILED tests/rhosocial/activerecord_mysql_test/basic/test_crud.py::test_create_user - Multiple tests with same name
```

**Solution:**
Use proper function aliasing when importing:
```python
# Import with alias to avoid conflicts
from rhosocial.activerecord_test.basic.test_crud import (
    test_create_user as _test_create_user,
    test_find_user as _test_find_user,
)

# Create wrapper functions with clear names
def test_create_user(user_class):
    """MySQL backend test for user creation"""
    return _test_create_user(user_class)

def test_mysql_specific_create_user(user_class):
    """MySQL-specific user creation features"""
    # MySQL-specific test implementation
    pass
```

### Debugging Tips

#### Basic Debugging Commands

```bash
# Verbose test execution with detailed output
PYTHONPATH=src:tests:$PYTHONPATH pytest -v -s \
    tests/rhosocial/activerecord_mysql_test/basic/test_crud.py

# Run single test with maximum verbosity
PYTHONPATH=src:tests:$PYTHONPATH pytest -vvv -s \
    tests/rhosocial/activerecord_mysql_test/basic/test_crud.py::test_create_user

# Debug test with pdb
PYTHONPATH=src:tests:$PYTHONPATH pytest --pdb \
    tests/rhosocial/activerecord_mysql_test/basic/test_crud.py::test_create_user

# Run with traceback on first failure
PYTHONPATH=src:tests:$PYTHONPATH pytest -x --tb=long \
    tests/rhosocial/activerecord_mysql_test/basic/
```

#### Backend-Specific Debugging

```bash
# Test only core function reuse (exclude MySQL-specific tests)
PYTHONPATH=src:tests:$PYTHONPATH pytest \
    tests/rhosocial/activerecord_mysql_test/basic/test_crud.py \
    -k "not mysql_" -v

# Test only MySQL-specific functionality
PYTHONPATH=src:tests:$PYTHONPATH pytest \
    tests/rhosocial/activerecord_mysql_test/ \
    -k "mysql_" -v

# Compare core vs backend test execution
PYTHONPATH=src:tests:$PYTHONPATH pytest \
    tests/rhosocial/activerecord_test/basic/test_crud.py \
    tests/rhosocial/activerecord_mysql_test/basic/test_crud.py \
    --tb=short -v
```

#### Test Environment Validation

```python
# validate_test_environment.py
"""Script to validate backend test environment setup"""

def validate_imports():
    """Validate all necessary imports work"""
    try:
        import rhosocial.activerecord
        print("✅ Core activerecord package: OK")
    except ImportError as e:
        print(f"❌ Core activerecord package: {e}")
        return False
    
    try:
        import rhosocial.activerecord_test
        print("✅ Core test package: OK")
    except ImportError as e:
        print(f"❌ Core test package: {e}")
        return False
    
    try:
        import rhosocial.activerecord_mysql_test
        print("✅ MySQL test package: OK")
    except ImportError as e:
        print(f"❌ MySQL test package: {e}")
        return False
    
    return True


def validate_core_test_imports():
    """Validate core test function imports"""
    try:
        from rhosocial.activerecord_test.basic.test_crud import (
            test_create_user,
            test_find_user,
            test_update_user,
            test_delete_user
        )
        print("✅ Core CRUD test functions: OK")
        return True
    except ImportError as e:
        print(f"❌ Core CRUD test functions: {e}")
        return False


def validate_backend_models():
    """Validate backend model configuration"""
    try:
        from rhosocial.activerecord_mysql_test.basic.fixtures.models import (
            user_class,
            type_case_class,
            validated_user_class
        )
        print("✅ MySQL model fixtures: OK")
        return True
    except ImportError as e:
        print(f"❌ MySQL model fixtures: {e}")
        return False


def validate_backend_registration():
    """Validate backend registration"""
    try:
        from rhosocial.activerecord_mysql_test.utils import MYSQL_CONFIGS
        print("✅ MySQL backend registration: OK")
        return True
    except ImportError as e:
        print(f"❌ MySQL backend registration: {e}")
        return False


def main():
    """Run all validation checks"""
    print("🔍 Validating test environment setup...\n")
    
    checks = [
        ("Import validation", validate_imports),
        ("Core test imports", validate_core_test_imports),
        ("Backend models", validate_backend_models),
        ("Backend registration", validate_backend_registration),
    ]
    
    passed = 0
    total = len(checks)
    
    for name, check_func in checks:
        print(f"\n📋 {name}:")
        if check_func():
            passed += 1
    
    print(f"\n📊 Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 Environment validation successful!")
        return 0
    else:
        print("❌ Environment validation failed!")
        return 1


if __name__ == "__main__":
    exit(main())
```

#### Comprehensive Test Reports with Debugging

```bash
# Generate comprehensive debugging reports
PYTHONPATH=src:tests:$PYTHONPATH pytest \
    tests/rhosocial/activerecord_mysql_test/ \
    --tb=long \
    --capture=no \
    --verbose \
    --junit-xml=reports/mysql-debug.xml \
    --html=reports/mysql-debug.html \
    --self-contained-html \
    --cov=rhosocial.activerecord_mysql \
    --cov-report=html:reports/mysql-debug-cov \
    --cov-report=term-missing

# Run environment validation before tests
python validate_test_environment.py && \
PYTHONPATH=src:tests:$PYTHONPATH pytest \
    tests/rhosocial/activerecord_mysql_test/basic/ \
    --tb=short -v
```

### Performance Debugging

```bash
# Profile test execution time
PYTHONPATH=src:tests:$PYTHONPATH pytest \
    tests/rhosocial/activerecord_mysql_test/basic/test_crud.py \
    --durations=10 \
    --tb=short

# Compare different test execution strategies
time PYTHONPATH=src:tests:$PYTHONPATH pytest tests/rhosocial/activerecord_test/basic/
time PYTHONPATH=src:tests:$PYTHONPATH pytest tests/rhosocial/activerecord_test/basic/ -v

# Memory usage debugging (requires pytest-memray)
pip install pytest-memray
PYTHONPATH=src:tests:$PYTHONPATH pytest \
    tests/rhosocial/activerecord_mysql_test/basic/test_crud.py \
    --memray \
    --tb=short
```

## 📞 Support

If you encounter issues or need help developing test support for new database backends, please:

1. **Check the troubleshooting section above** - Many common issues have solutions listed
2. **Run the environment validation script** - This can identify configuration problems
3. **Search existing issues on GitHub** - Your issue may already be documented
4. **Create a new issue** with detailed information including:
   - Your backend type and version
   - Complete error messages and stack traces
   - Test environment details (Python version, OS, etc.)
   - Minimal reproduction case
   - Output from the validation script

### Backend Development Support

For backend development support, please include:
- Target database type and version
- Test package structure showing your directory layout
- Specific test failures or compatibility issues with full error messages
- Database connection configuration (without sensitive credentials)
- Results from running the validation script
- Evidence of following the recommended directory structure

### Useful Debug Information to Include

```bash
# Collect comprehensive debug information
echo "=== System Information ===" > debug_info.txt
python --version >> debug_info.txt
pip list | grep rhosocial >> debug_info.txt

echo -e "\n=== Directory Structure ===" >> debug_info.txt
find tests/rhosocial/activerecord_mysql_test -name "*.py" | head -20 >> debug_info.txt

echo -e "\n=== Import Test ===" >> debug_info.txt
python -c "
try:
    from rhosocial.activerecord_test.basic.test_crud import test_create_user
    print('✅ Core import: Success')
except Exception as e:
    print(f'❌ Core import: {e}')
    
try:
    from rhosocial.activerecord_mysql_test.basic.fixtures.models import user_class
    print('✅ Backend import: Success')
except Exception as e:
    print(f'❌ Backend import: {e}')
" >> debug_info.txt 2>&1

echo -e "\n=== Environment Validation ===" >> debug_info.txt
python validate_test_environment.py >> debug_info.txt 2>&1

# Attach debug_info.txt to your issue
```

## 📞 Support

If you encounter issues or need help developing test support for new database backends, please:

1. Check the troubleshooting section above
2. Search existing issues on GitHub
3. Create a new issue with detailed information about your setup and the problem
4. Include relevant log outputs and your environment details

For backend development support, please include:
- Target database type and version
- Test package structure
- Specific test failures or compatibility issues
- Database connection configuration (without sensitive data)