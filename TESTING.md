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

When developing a new database backend package (e.g., `rhosocial-activerecord-mysql`), we recommend organizing your tests following the same pattern as the main package to enable test reuse:

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
│   │       │   ├── models.py           # Model definitions (reuse main package)
│   │       │   └── schema/
│   │       │       └── mysql/
│   │       │           ├── users.sql
│   │       │           ├── type_cases.sql
│   │       │           ├── type_tests.sql
│   │       │           └── validated_users.sql
│   │       ├── compatibility/          # Main package compatibility tests
│   │       │   ├── __init__.py
│   │       │   ├── test_basic_compat.py      # Reuse main package basic tests
│   │       │   ├── test_fields_compat.py     # Reuse main package field tests
│   │       │   └── test_validation_compat.py # Reuse main package validation tests
│   │       ├── mysql_backend/          # MySQL backend core tests
│   │       │   ├── __init__.py
│   │       │   ├── test_connection.py
│   │       │   ├── test_type_mapping.py
│   │       │   └── test_query_builder.py
│   │       ├── mysql_features/         # MySQL-specific feature tests
│   │       │   ├── __init__.py
│   │       │   ├── test_mysql_types.py
│   │       │   ├── test_json_columns.py
│   │       │   └── test_full_text_search.py
│   │       └── integration/            # MySQL integration tests
│   │           ├── __init__.py
│   │           ├── test_real_world.py
│   │           └── test_performance.py
│   └── conftest.py                     # Global test configuration
├── pyproject.toml
└── README.md
```

### Test Directory Categories

#### 1. Compatibility Tests (`compatibility/`)

These tests verify that your backend works correctly with the standard ActiveRecord interface by reusing the main package test suite:

```python
# tests/rhosocial/activerecord_mysql_test/compatibility/test_basic_compat.py
"""MySQL backend compatibility tests for basic functionality"""

# Import test functions from main package
from rhosocial.activerecord_test.basic.test_crud import (
    test_create_user,
    test_find_user,
    test_update_user,
    test_delete_user
)

# Import MySQL-specific fixtures
from ..fixtures.models import mysql_user_class


class TestMySQLBasicCompatibility:
    """Test MySQL backend compatibility with basic operations"""
    
    def test_mysql_create_user(self, mysql_user_class):
        """Test user creation with MySQL backend"""
        test_create_user(mysql_user_class)
    
    def test_mysql_find_user(self, mysql_user_class):
        """Test user finding with MySQL backend"""
        test_find_user(mysql_user_class)
    
    def test_mysql_update_user(self, mysql_user_class):
        """Test user updating with MySQL backend"""
        test_update_user(mysql_user_class)
    
    def test_mysql_delete_user(self, mysql_user_class):
        """Test user deletion with MySQL backend"""
        test_delete_user(mysql_user_class)
```

#### 2. Model Definition and Fixture Creation (`fixtures/models.py`)

The key to test reuse is defining models and fixtures correctly:

```python
# tests/rhosocial/activerecord_mysql_test/fixtures/models.py
"""MySQL backend test models - reusing main package model definitions"""

# Import model classes from main package
from rhosocial.activerecord_test.basic.fixtures.models import (
    User, TypeCase, ValidatedFieldUser, TypeTestModel
)

# Import fixture creation utility from main package
from rhosocial.activerecord_test.utils import create_active_record_fixture

# Import MySQL test utilities to register MySQL backend
from ..utils import logger

# Configure models to use only MySQL backend for this test package
User.__supported_backends__ = ["mysql"]
TypeCase.__supported_backends__ = ["mysql"]
ValidatedFieldUser.__supported_backends__ = ["mysql"]
TypeTestModel.__supported_backends__ = ["mysql"]

# Create MySQL-specific fixtures using the main package's fixture creation utility
# These will automatically use MySQL backend due to __supported_backends__ restriction
mysql_user_class = create_active_record_fixture(User)
mysql_type_case_class = create_active_record_fixture(TypeCase)
mysql_validated_user_class = create_active_record_fixture(ValidatedFieldUser)
mysql_type_test_model = create_active_record_fixture(TypeTestModel)

logger.info("MySQL-specific fixtures created successfully")
```

#### 3. Backend Registration (`utils.py`)

Register your backend in the global test configuration:

```python
# tests/rhosocial/activerecord_mysql_test/utils.py
"""MySQL backend test utilities"""
from rhosocial.activerecord.backend.impl.mysql.backend import MySQLBackend
from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig
from rhosocial.activerecord_test.utils import DB_HELPERS, DB_CONFIGS

# MySQL specific configurations
MYSQL_CONFIGS = {
    "local": {
        "host": "localhost",
        "port": 3306,
        "database": "activerecord_test",
        "username": "root",
        "password": "",
        "charset": "utf8mb4",
    },
    "docker": {
        "host": "mysql",
        "port": 3306,
        "database": "activerecord_test",
        "username": "test_user",
        "password": "test_password",
        "charset": "utf8mb4",
    }
}

# MySQL specific helper
MYSQL_HELPER = {
    "class": MySQLBackend,
    "config_class": MySQLConnectionConfig,
}

# Register MySQL configurations globally
DB_CONFIGS["mysql"] = MYSQL_CONFIGS
DB_HELPERS["mysql"] = MYSQL_HELPER
```

#### 4. Database Schema Files

Create corresponding schema files for your database:

```sql
-- tests/rhosocial/activerecord_mysql_test/fixtures/schema/mysql/users.sql
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    age INT UNSIGNED,
    balance DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_username (username),
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### 5. MySQL-Specific Features (`mysql_features/`)

Tests for database-specific functionality:

```python
# tests/rhosocial/activerecord_mysql_test/mysql_features/test_mysql_types.py
"""MySQL-specific data type functionality tests"""
import pytest
from decimal import Decimal

from ..fixtures.models import mysql_type_case_class


class TestMySQLDataTypes:
    """Test MySQL-specific data type handling"""
    
    def test_mysql_json_column(self, mysql_type_case_class):
        """Test MySQL native JSON column type"""
        test_json = {"name": "John", "scores": [85, 92, 78]}
        
        model = mysql_type_case_class(
            username='json_test',
            email='json@test.com',
            json_val=test_json
        )
        model.save()
        
        retrieved = mysql_type_case_class.find_one(model.id)
        assert retrieved.json_val == test_json
        assert isinstance(retrieved.json_val, dict)
    
    def test_mysql_decimal_precision(self, mysql_type_case_class):
        """Test MySQL DECIMAL precision handling"""
        model = mysql_type_case_class(
            username='decimal_test',
            email='decimal@test.com',
            decimal_val=Decimal('999999.9999')
        )
        model.save()
        
        retrieved = mysql_type_case_class.find_one(model.id)
        assert retrieved.decimal_val == Decimal('999999.9999')
```

### Test Reuse Through Backend Configuration

The core mechanism for test reuse is the `__supported_backends__` attribute and the `create_active_record_fixture` function:

1. **Model Restriction**: Set `__supported_backends__ = ["mysql"]` on imported model classes
2. **Fixture Creation**: Use `create_active_record_fixture(Model)` to create MySQL-specific fixtures
3. **Automatic Backend Selection**: The fixture will automatically use MySQL backend due to the restriction
4. **Test Function Reuse**: Import and call test functions from the main package directly

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

### Cross-Package Test Reuse

For example, `rhosocial-activerecord-aurora` (Amazon Aurora) package can reuse MySQL tests:

```python
# In Aurora package tests
from rhosocial.activerecord_test.basic.test_crud import test_create_user  # Main package test
from rhosocial.activerecord_mysql_test.mysql_features.test_mysql_types import (  # MySQL package test
    test_mysql_json_column
)

class TestAuroraMySQL:
    """Aurora MySQL compatibility tests"""
    
    def test_basic_crud_compatibility(self, aurora_model):
        # Reuse main package basic CRUD tests
        test_create_user(aurora_model)
    
    def test_mysql_json_compatibility(self, aurora_model):
        # Reuse MySQL package JSON functionality tests
        test_mysql_json_column(aurora_model)
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