# Testing Guide

This document explains how to test the RhoSocial ActiveRecord package and how to develop tests for new database backends.

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Test Directory Structure](#test-directory-structure)
- [Running Tests](#running-tests)
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

# Parallel test execution (requires pytest-xdist)
pip install pytest-xdist
PYTHONPATH=src:tests:$PYTHONPATH pytest tests/ -n auto

# Run only failed tests
PYTHONPATH=src:tests:$PYTHONPATH pytest tests/ --lf

# Stop at first failure
PYTHONPATH=src:tests:$PYTHONPATH pytest tests/ -x
```

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

### Handling Partial Support

If your database backend has limitations, clearly document them:

```markdown
## MySQL Backend Limitations

### Unsupported Features
- ❌ Common Table Expressions (CTE) - MySQL versions below 8.0
- ❌ Certain advanced aggregate functions - depends on MySQL version

### Partial Support
- ⚠️ Optimistic locking mixin - requires manual version field
- ⚠️ Full-text search - only supports MyISAM and InnoDB engines

### Workarounds
- CTE functionality can be implemented using subqueries
- Version locking can be handled at application level
```

## 📂 Test Organization for Backend Packages

When developing a new database backend package (e.g., `rhosocial-activerecord-mysql`), we recommend organizing your tests following the same pattern as the main package to enable test reuse through symlinks:

### Recommended Directory Structure

```
rhosocial-activerecord-mysql/
├── src/
│   └── rhosocial/
│       └── activerecord/
│           └── backend/
│               └── impl/
│                   └── mysql/          # MySQL backend implementation
├── tests/
│   ├── rhosocial/
│   │   └── activerecord_mysql_test/    # MySQL test package (following main package pattern)
│   │       ├── __init__.py
│   │       ├── utils.py                # MySQL-specific test utilities
│   │       ├── fixtures/               # MySQL-specific test fixtures
│   │       │   ├── __init__.py
│   │       │   ├── storage.py
│   │       │   └── models.py
│   │       ├── compatibility/          # Main package compatibility tests
│   │       │   ├── __init__.py
│   │       │   ├── test_basic_compat.py      # Reuse main package basic tests
│   │       │   ├── test_query_compat.py      # Reuse main package query tests
│   │       │   ├── test_relation_compat.py   # Reuse main package relation tests
│   │       │   ├── test_events_compat.py     # Reuse main package events tests
│   │       │   └── test_mixins_compat.py     # Reuse main package mixins tests
│   │       ├── mysql_backend/          # MySQL backend core tests
│   │       │   ├── __init__.py
│   │       │   ├── test_connection.py
│   │       │   ├── test_type_mapping.py
│   │       │   ├── test_query_builder.py
│   │       │   └── test_executor.py
│   │       ├── mysql_features/         # MySQL-specific feature tests
│   │       │   ├── __init__.py
│   │       │   ├── test_mysql_types.py
│   │       │   ├── test_full_text_search.py
│   │       │   ├── test_json_columns.py
│   │       │   ├── test_spatial_data.py
│   │       │   └── test_generated_columns.py
│   │       ├── mysql_versions/         # MySQL version-specific tests
│   │       │   ├── __init__.py
│   │       │   ├── test_mysql57.py
│   │       │   ├── test_mysql80.py
│   │       │   └── test_version_detection.py
│   │       └── integration/            # MySQL integration tests
│   │           ├── __init__.py
│   │           ├── test_real_world.py
│   │           ├── test_performance.py
│   │           └── test_migration.py
│   └── conftest.py                     # Global test configuration
├── pyproject.toml
└── README.md
```

### Test Directory Categories

#### 1. Compatibility Tests (`compatibility/`)

These tests verify that your backend works correctly with the standard ActiveRecord interface by reusing the main package test suite:

```python
# tests/rhosocial/activerecord_mysql_test/compatibility/test_basic_compat.py
import pytest
from rhosocial.activerecord_test.utils import (
    generate_test_configs, 
    create_active_record_fixture,
    DBTestConfig
)
from rhosocial.activerecord_test.basic.test_crud import (
    test_create_user,
    test_find_user,
    test_update_user,
    test_delete_user
)

# Define your database configuration
MYSQL_CONFIGS = {
    "local": {
        "host": "localhost",
        "port": 3306,
        "database": "test_db",
        "username": "test_user", 
        "password": "test_pass"
    },
    "docker": {
        "host": "mysql",
        "port": 3306,
        "database": "test_db",
        "username": "test_user",
        "password": "test_password"
    }
}

def mysql_test_configs():
    for config_name, config in MYSQL_CONFIGS.items():
        yield DBTestConfig("mysql", config_name, config)

class TestMySQLBasicCompatibility:
    """Test MySQL backend compatibility with basic operations"""
    
    @pytest.fixture(params=list(mysql_test_configs()))
    def mysql_model(self, request):
        return create_mysql_model_with_config(request.param)
    
    def test_create_operation(self, mysql_model):
        test_create_user(mysql_model)
    
    def test_read_operation(self, mysql_model):
        test_find_user(mysql_model)
    
    def test_update_operation(self, mysql_model):
        test_update_user(mysql_model)
    
    def test_delete_operation(self, mysql_model):
        test_delete_user(mysql_model)
```

#### 2. Backend Core Tests (`mysql_backend/`)

These tests cover MySQL backend core implementation:

```python
# tests/rhosocial/activerecord_mysql_test/mysql_backend/test_connection.py
class TestMySQLConnection:
    """Test MySQL connection management"""
    
    def test_connection_pool(self, mysql_config):
        """Test connection pooling functionality"""
        pass
    
    def test_reconnection_logic(self, mysql_config):
        """Test automatic reconnection handling"""
        pass
```

#### 3. MySQL-Specific Features (`mysql_features/`)

These tests cover MySQL-specific functionality:

```python
# tests/rhosocial/activerecord_mysql_test/mysql_features/test_mysql_types.py
import pytest
from decimal import Decimal
from datetime import datetime

class TestMySQLDataTypes:
    """Test MySQL-specific data type handling"""
    
    def test_mysql_decimal_precision(self, mysql_model):
        """Test MySQL DECIMAL precision handling"""
        # MySQL DECIMAL(10,2) specific test
        model = mysql_model(price=Decimal('99999999.99'))
        model.save()
        
        retrieved = mysql_model.find_one(model.id)
        assert retrieved.price == Decimal('99999999.99')
    
    def test_mysql_json_column(self, mysql_model):
        """Test MySQL JSON column type (MySQL 5.7+)"""
        # Test JSON column functionality
        pass
```

#### 4. Version Compatibility (`mysql_versions/`)

Tests for different MySQL versions:

```python
# tests/rhosocial/activerecord_mysql_test/mysql_versions/test_mysql80.py
class TestMySQL80Features:
    """Test MySQL 8.0 specific features"""
    
    def test_cte_support(self, mysql_model):
        """Test Common Table Expressions support in MySQL 8.0+"""
        pass
    
    def test_window_functions(self, mysql_model):
        """Test window functions support"""
        pass
```

#### 5. Integration Tests (`integration/`)

These tests cover real-world scenarios and integration aspects:

```python
# tests/rhosocial/activerecord_mysql_test/integration/test_real_world.py
class TestRealWorldScenarios:
    """Test real-world usage patterns"""
    
    def test_high_concurrency_scenario(self, mysql_model):
        """Test behavior under high concurrency"""
        pass
    
    def test_large_dataset_operations(self, mysql_model):
        """Test operations on large datasets"""
        pass
```

### Test Reuse Through Symlinks

#### MySQL Package Symlink Setup

When you install the MySQL package in editable mode:

```bash
# In rhosocial-activerecord-mysql package
pip install -e .
```

It creates a symlink:
```
src/rhosocial/activerecord_mysql_test -> tests/rhosocial/activerecord_mysql_test/
```

#### Other Packages Reusing MySQL Tests

For example, `rhosocial-activerecord-aurora` (Amazon Aurora) package can reuse MySQL tests:

```python
# In Aurora package tests
from rhosocial.activerecord_test import (           # Reuse main package tests
    generate_test_configs, 
    create_active_record_fixture
)
from rhosocial.activerecord_mysql_test import (     # Reuse MySQL package tests
    mysql_test_configs,
    MYSQL_HELPERS
)
from rhosocial.activerecord_mysql_test.mysql_features.test_mysql_types import (
    test_mysql_decimal_precision,
    test_mysql_json_column
)

class TestAuroraMySQL:
    """Aurora MySQL compatibility tests"""
    
    def test_basic_crud_compatibility(self, aurora_model):
        # Reuse main package basic CRUD tests
        from rhosocial.activerecord_test.basic.test_crud import test_create_user
        test_create_user(aurora_model)
    
    def test_mysql_json_compatibility(self, aurora_model):
        # Reuse MySQL package JSON functionality tests
        test_mysql_json_column(aurora_model)
```

### Test Package Naming Convention

| Package Type | Test Package Name | Symlink Location |
|-------------|-------------------|------------------|
| Main Package | `activerecord_test` | `src/rhosocial/activerecord_test` |
| MySQL Package | `activerecord_mysql_test` | `src/rhosocial/activerecord_mysql_test` |
| PostgreSQL Package | `activerecord_pgsql_test` | `src/rhosocial/activerecord_pgsql_test` |
| MariaDB Package | `activerecord_mariadb_test` | `src/rhosocial/activerecord_mariadb_test` |

### Benefits of This Organization

1. **Consistent Structure**: Follows the same pattern as the main package
2. **Test Reusability**: Other packages can easily reuse MySQL package tests
3. **Clear Naming**: Each package has a distinct test namespace
4. **Easy Extension**: New database backends can reuse existing test patterns
5. **Symlink Support**: Enables test sharing through simple symlink mechanism

### Test Configuration Examples

```python
# tests/conftest.py (Global configuration)
import pytest
from rhosocial.activerecord_test.utils import DB_CONFIGS, DB_HELPERS

# Register your database configuration globally
DB_CONFIGS["mysql"] = {
    "local": {
        "host": "localhost",
        "port": 3306,
        "database": "activerecord_test",
        "username": "root",
        "password": "",
        "charset": "utf8mb4"
    }
}

# Register database helper
from your_backend.mysql_helper import MySQLTestHelper
DB_HELPERS["mysql"] = MySQLTestHelper

# tests/compatibility/conftest.py (Compatibility-specific configuration)
import pytest

@pytest.fixture(scope="session")
def compatibility_database():
    """Set up database for compatibility testing"""
    # Database setup specific to compatibility tests
    pass

# tests/mysql_specific/conftest.py (MySQL-specific configuration)
import pytest

@pytest.fixture(scope="session") 
def mysql_engine():
    """Set up MySQL engine for specific tests"""
    # MySQL-specific setup
    pass
```

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

This allows you to import test utilities in your code:

```python
from rhosocial.activerecord_test.utils import create_active_record_fixture
from rhosocial.activerecord_test.fixtures.storage import storage_fixture
from rhosocial.activerecord_test.utils import DBTestConfig
```

### Symlink Status Check

```bash
# Check if symlink exists
ls -la src/rhosocial/activerecord_test

# Verify symlink correctness
python -c "from rhosocial.activerecord_test import __version__; print(__version__)"
```

### Manual Symlink Creation

If automatic creation fails, you can create it manually:

```bash
# macOS/Linux
ln -sf tests/rhosocial/activerecord_test src/rhosocial/activerecord_test

# Verify
ls -la src/rhosocial/activerecord_test
```

## 🌍 Environment Management

### Development vs Production

| Installation Method | Test Package | Use Case |
|-------------------|-------------|----------|
| `pip install -e .` | ✅ Included | Development, testing, backend development |
| `pip install rhosocial-activerecord` | ❌ Not included | Production use |

### Production Installation

```bash
# Production installation (no test content)
pip install rhosocial-activerecord

# Verify (this will fail, which is expected)
python -c "from rhosocial.activerecord_test import __version__"
# ImportError: No module named 'rhosocial.activerecord_test'
```

## ⚠️ Important Notes

### Symlink Cleanup

**Important**: After editable installation, symlinks do **not** automatically disappear when uninstalling!

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

### Debugging Tips

```bash
# Verbose test execution
PYTHONPATH=src:tests:$PYTHONPATH pytest -v -s

# Run only failed tests
PYTHONPATH=src:tests:$PYTHONPATH pytest --lf --tb=short

# Enter debug mode
PYTHONPATH=src:tests:$PYTHONPATH pytest --pdb

# Generate HTML coverage report
PYTHONPATH=src:tests:$PYTHONPATH pytest --cov=rhosocial.activerecord --cov-report=html
open htmlcov/index.html
```

## 📞 Support

If you encounter issues or need help developing test support for new database backends, please:

1. Check the troubleshooting section above
2. Search existing issues on GitHub
3. Create a new issue with detailed information:
   - Operating system and Python version
   - Installation method and steps
   - Error messages and stack traces
   - Steps to reproduce

We welcome community contributions including test suite improvements, new test cases, and configuration optimizations.

### Getting Help

- **GitHub Issues**: [Submit bug reports or feature requests](https://github.com/rhosocial/python-activerecord/issues)
- **Discussions**: Feel free to open issues to discuss test setup improvements
- **Documentation**: Check online documentation for more information