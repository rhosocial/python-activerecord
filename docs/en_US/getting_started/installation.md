# Installation

Getting started with `rhosocial-activerecord` is straightforward. This guide provides detailed instructions for various installation methods and environment configurations.

## Requirements

### Python Version
*   **Python 3.8+** — Supports latest Python 3.14 and free-threaded builds (3.13t, 3.14t)
*   **Recommended Version**: Python 3.11+ for optimal performance and feature support

### Core Dependencies
*   **Pydantic V2** — Data validation and serialization framework
    *   Python 3.8: pydantic 2.10.6 (due to compatibility constraints)
    *   Python 3.9+: pydantic 2.12+ (full feature support)

### Database Requirements
*   **SQLite**: 3.25+ (built-in support)
*   **Other Databases**: Require corresponding backend packages
    *   MySQL/MariaDB: `rhosocial-activerecord-mysql`
    *   PostgreSQL: `rhosocial-activerecord-postgres`
    *   Oracle: `rhosocial-activerecord-oracle` (planned)
    *   SQL Server: `rhosocial-activerecord-mssql` (planned)

## Install via pip

### Basic Installation
```bash
pip install rhosocial-activerecord
```

### Install Specific Database Backend Support
```bash
# Install MySQL/MariaDB support
pip install rhosocial-activerecord[mysql]

# Install PostgreSQL support
pip install rhosocial-activerecord[postgres]

# Install all database support
pip install rhosocial-activerecord[databases]

# Install complete package (including all optional dependencies)
pip install rhosocial-activerecord[all]
```

### Development Environment Installation
If you plan to contribute to the project or run tests:
```bash
# Install development dependencies (formatting, type checking, testing, etc.)
pip install rhosocial-activerecord[dev,test]

# Install documentation build dependencies
pip install rhosocial-activerecord[docs]
```

## Install from Source

If you want to use the latest development version or contribute to the project:

### Clone the Repository
```bash
git clone https://github.com/rhosocial/python-activerecord.git
cd python-activerecord
```

### Development Mode Installation
```bash
# Development mode installation (recommended for development)
pip install -e .

# Install all development dependencies
pip install -e .[dev,test,docs]
```

### Production Mode Installation
```bash
# Production mode installation
pip install .
```

## Virtual Environment Recommendation

It's highly recommended to install and use `rhosocial-activerecord` in a virtual environment:

### Using venv
```bash
# Create virtual environment
python -m venv activerecord-env

# Activate virtual environment
# Windows:
activerecord-env\Scripts\activate
# macOS/Linux:
source activerecord-env/bin/activate

# Install rhosocial-activerecord
pip install rhosocial-activerecord

# Deactivate virtual environment when done
deactivate
```

### Using conda
```bash
# Create virtual environment
conda create -n activerecord-env python=3.11

# Activate virtual environment
conda activate activerecord-env

# Install rhosocial-activerecord
pip install rhosocial-activerecord

# Deactivate virtual environment when done
conda deactivate
```

## Verify Installation

You can verify the installation through multiple methods:

### Check Version Number
```python
from importlib.metadata import version
print(version("rhosocial_activerecord"))
```

### Basic Functionality Test
```python
# Test basic imports
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from typing import ClassVar

# Define simple model for testing
class TestModel(ActiveRecord):
    __table_name__ = "test_table"
    name: str
    c: ClassVar[FieldProxy] = FieldProxy()

# Check if model definition succeeded
print("ActiveRecord model definition successful")
print(f"Model class: {TestModel}")
```

### Check Dependency Integrity
```bash
# Check installed packages
pip list | grep -E "(rhosocial|pydantic)"

# Check Python version compatibility
python --version
```

## Common Installation Issues and Solutions

### 1. Dependency Conflicts
If you encounter dependency version conflicts:
```bash
# Upgrade pip to the latest version
pip install --upgrade pip

# Clear cache and retry
pip cache purge
pip install rhosocial-activerecord
```

### 2. Python 3.8 Compatibility Issues
For Python 3.8 users, ensure correct dependency versions are installed:
```bash
# Python 3.8 users will automatically install compatible versions
pip install rhosocial-activerecord
```

### 3. Permission Issues
If you encounter permission issues:
```bash
# Use --user flag to install to user directory
pip install --user rhosocial-activerecord

# Or use virtual environment (recommended)
python -m venv myenv
source myenv/bin/activate  # Windows: myenv\Scripts\activate
pip install rhosocial-activerecord
```

### 4. Network Issues
If download is slow or times out:
```bash
# Use alternative PyPI mirrors
pip install --index-url https://pypi.org/simple/ rhosocial-activerecord

# Configure pip to use a specific mirror permanently
# pip config set global.index-url https://pypi.org/simple/

# Clear pip cache and retry
pip cache purge
pip install rhosocial-activerecord
```

## Next Steps

After installation, it's recommended to:

1. **Read the Quick Start Guide**: Check the [Quick Start](quick_start.md) documentation for basic usage
2. **Configure Database**: Learn how to [configure database connections](configuration.md)
3. **Build Your First App**: Follow the [First CRUD App](first_crud.md) tutorial

## Getting Help

If you encounter issues during installation:

1. **Check System Requirements**: Ensure minimum Python and dependency version requirements are met
2. **Review Error Logs**: Carefully read error messages during installation
3. **Consult Documentation**: Refer to the [Troubleshooting](troubleshooting.md) documentation
4. **Submit Issues**: Submit issues on [GitHub Issues](https://github.com/rhosocial/python-activerecord/issues)

---

> 💡 **Tip**: It's recommended to regularly update to the latest version to get new features and security fixes:
> ```bash
> pip install --upgrade rhosocial-activerecord
> ```
