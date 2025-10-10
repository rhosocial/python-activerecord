# Testing Architecture and Execution Guide

> **AI Assistant Note**: This document is optimized for AI code assistants (Claude Code, Gemini CLI, etc.). It uses imperative language and front-loads critical execution requirements.

## Architecture Overview

### Testsuite and Backend Relationship

```mermaid
graph TB
    subgraph "Backend Packages" 
        direction TB
        MYSQL[rhosocial-activerecord-mysql<br/>- Backend implementation<br/>- Schema definitions<br/>- Backend-specific tests]
        DEFAULT[rhosocial-activerecord<br/>- Default backend<br/>- Core functionality<br/>- Backend-specific tests]
    end

    subgraph "Testsuite Package" 
        direction TB
        TS[rhosocial-activerecord-testsuite<br/>- Standardized test contracts<br/>- Feature tests<br/>- Real-world scenarios<br/>- Performance benchmarks]
    end

    subgraph "Backend Developer Responsibilities" 
        direction TB
        PROVIDER[Implement test providers<br/>- Set up database schemas<br/>- Configure test models<br/>- Provide fixtures]
        SCHEMA[SQL Schema Creation<br/>- Create backend-specific<br/>  schema files<br/>- Match testsuite structure]
        REPORT[Generate compatibility reports<br/>- Run standardized tests<br/>- Track compatibility scores]
    end

    subgraph "Testsuite Author Responsibilities" 
        direction TB
        TESTDEF[Test Definition<br/>- Write backend-agnostic<br/>  test functions<br/>- Define test contracts<br/>- Provide test utilities]
        MARKER[Test Marking<br/>- Standard pytest markers<br/>- Categorization system<br/>- Feature identification]
        UTIL[Test Utilities<br/>- Schema generators<br/>- Helper functions<br/>- Provider interfaces]
    end

    %% Relationship arrows
    MYSQL -.->|uses| TS
    DEFAULT -.->|uses| TS
    PROVIDER -->|fulfills| TS
    SCHEMA -->|supports| TS
    REPORT -->|verifies| TS
    TESTDEF -->|provides| TS
    MARKER -->|organizes| TS
    UTIL -->|facilitates| TS

    style TS fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    style MYSQL fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    style DEFAULT fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    style PROVIDER fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    style SCHEMA fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    style REPORT fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    style TESTDEF fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style MARKER fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style UTIL fill:#fff3e0,stroke:#e65100,stroke-width:2px
```

### Testing Layer Architecture

```mermaid
graph LR
    subgraph "Testsuite Layer"
        TEST[Test Functions<br/>Backend-agnostic logic]
        IFACE[Provider Interfaces<br/>Contract definitions]
        CAPS[Capability Requirements<br/>Feature declarations]
    end
    
    subgraph "Backend Layer"
        PROV[Provider Implementation<br/>Model setup & fixtures]
        SCHEMA[SQL Schemas<br/>Database structure]
        CAPSDECL[Capability Declaration<br/>Supported features]
    end
    
    subgraph "Database Layer"
        DB[(Database<br/>SQLite/MySQL/PostgreSQL)]
    end
    
    TEST -->|uses| IFACE
    TEST -->|requires| CAPS
    IFACE -->|implemented by| PROV
    CAPS -->|checked against| CAPSDECL
    PROV -->|creates| SCHEMA
    PROV -->|configures models with| CAPSDECL
    SCHEMA -->|executed on| DB
    CAPSDECL -->|describes| DB
    
    style TEST fill:#e1f5fe
    style IFACE fill:#e1f5fe
    style CAPS fill:#fff3e0
    style PROV fill:#e8f5e8
    style SCHEMA fill:#e8f5e8
    style CAPSDECL fill:#fff3e0
    style DB fill:#f3e5f5
```

## CRITICAL: PYTHONPATH Configuration

**MUST configure PYTHONPATH before running tests.** The test directory (`tests/`) is **NOT** on the Python path by default.

### Why PYTHONPATH is Required

```
project-root/
├── src/rhosocial/activerecord/    # ← Python can import this
└── tests/                          # ← NOT importable by default
```

Tests import from `rhosocial.activerecord`, but the test files themselves are not in the package structure. Without PYTHONPATH, pytest cannot find the source code.

### Platform-Specific Commands

**Linux/macOS (bash/zsh):**
```bash
# Single command execution
PYTHONPATH=src pytest tests/

# Persistent for session
export PYTHONPATH=src
pytest tests/
```

**Windows (PowerShell):**
```powershell
# Single command execution
$env:PYTHONPATH="src"; pytest tests/

# Persistent for session
$env:PYTHONPATH="src"
pytest tests/
```

**Windows (CMD):**
```cmd
REM Single command execution
set PYTHONPATH=src && pytest tests/

REM Persistent for session
set PYTHONPATH=src
pytest tests/
```

### Common Errors Without PYTHONPATH

```python
# Error you'll see:
ModuleNotFoundError: No module named 'rhosocial.activerecord'

# Solution:
# Set PYTHONPATH=src before running pytest
```

### IDE Configuration

**PyCharm:**
- Mark `src/` as "Sources Root"
- Test runner automatically adds it to PYTHONPATH

**VS Code:**
```json
// .vscode/settings.json
{
    "python.testing.pytestArgs": [
        "tests"
    ],
    "python.testing.pytestEnabled": true,
    "python.envFile": "${workspaceFolder}/.env"
}
```

```bash
# .env file
PYTHONPATH=src
```

## Responsibilities Division

### Testsuite Authors MUST:
- Write backend-agnostic test logic
- Define provider interfaces
- Create test fixtures and utilities
- NEVER assume backend-specific features
- NEVER write SQL directly in tests
- Document required capabilities using correct category+capability format

### Backend Developers MUST:
- Implement provider interfaces
- Create backend-specific schema files
- Handle database connection/cleanup
- Write backend-specific tests separately
- Generate compatibility reports
- Declare backend capabilities using add_* methods

### Division of Labor

| Component | Testsuite | Backend |
|-----------|-----------|---------|
| Test logic | ✅ Defines | Uses |
| SQL schemas | Provides templates | ✅ Implements |
| Database setup | Defines interface | ✅ Implements |
| Model configuration | Defines fixtures | ✅ Provides models |
| Cleanup/teardown | Defines hooks | ✅ Implements |
| Capability declaration | Defines requirements | ✅ Declares support |

## Capability-Based Test Selection

### Overview

The capability negotiation mechanism uses a two-level hierarchy:

1. **Capability Categories** (CapabilityCategory): Top-level groupings like CTE, WINDOW_FUNCTIONS
2. **Specific Capabilities**: Individual features within each category

### Capability Architecture

```python
# Capability hierarchy structure
CapabilityCategory.CTE                    # Category
    ├── CTECapability.BASIC_CTE          # Specific capability
    ├── CTECapability.RECURSIVE_CTE      # Specific capability
    └── CTECapability.MATERIALIZED_CTE   # Specific capability

CapabilityCategory.WINDOW_FUNCTIONS       # Category
    ├── WindowFunctionCapability.ROW_NUMBER
    ├── WindowFunctionCapability.RANK
    └── WindowFunctionCapability.LAG

# Pre-defined combinations
ALL_CTE_FEATURES = (
    CTECapability.BASIC_CTE |
    CTECapability.RECURSIVE_CTE |
    CTECapability.COMPOUND_RECURSIVE_CTE |
    CTECapability.CTE_IN_DML |
    CTECapability.MATERIALIZED_CTE
)
```

### Backend Capability Declaration

```python
# Backend declares its capabilities
# src/rhosocial/activerecord/backend/impl/sqlite/backend.py
from rhosocial.activerecord.backend.capabilities import (
    DatabaseCapabilities,
    CapabilityCategory,
    CTECapability,
    WindowFunctionCapability,
    ALL_CTE_FEATURES,
    ALL_WINDOW_FUNCTIONS
)

class SQLiteBackend(StorageBackend):
    def _initialize_capabilities(self):
        """Initialize and return the backend's capability descriptor."""
        capabilities = DatabaseCapabilities()
        version = self.get_server_version()

        # CTEs supported from 3.8.3+
        if version >= (3, 8, 3):
            # Add specific capabilities
            capabilities.add_cte([
                CTECapability.BASIC_CTE,
                CTECapability.RECURSIVE_CTE
            ])
            # This automatically adds CapabilityCategory.CTE

        # Window functions from 3.25.0+
        if version >= (3, 25, 0):
            # Use pre-defined combination
            capabilities.add_window_function(ALL_WINDOW_FUNCTIONS)

        return capabilities
```

### Declaring Test Requirements

Tests must specify BOTH category AND specific capability:

```python
# Correct format: (category, specific_capability)
from rhosocial.activerecord.backend.capabilities import (
    CapabilityCategory,
    CTECapability
)
from rhosocial.activerecord.testsuite.utils import requires_capabilities

# Single capability requirement
@requires_capabilities((CapabilityCategory.CTE, CTECapability.BASIC_CTE))
def test_basic_cte(order_fixtures):
    """Test requires basic CTE support."""
    pass

# Multiple capabilities from same category
@requires_capabilities((CapabilityCategory.CTE, [CTECapability.BASIC_CTE, CTECapability.RECURSIVE_CTE]))
def test_recursive_cte(tree_fixtures):
    """Test requires both basic and recursive CTE."""
    pass

# Multiple capabilities from different categories
@requires_capabilities(
    (CapabilityCategory.CTE, CTECapability.RECURSIVE_CTE),
    (CapabilityCategory.WINDOW_FUNCTIONS, WindowFunctionCapability.ROW_NUMBER)
)
def test_complex_query(order_fixtures):
    """Test requires recursive CTE and window functions."""
    pass

# Category-only check (any capability in category)
@requires_capabilities((CapabilityCategory.JSON_OPERATIONS, None))
def test_json_support(json_user_fixtures):
    """Test requires any JSON operation support."""
    pass
```

### Capability Checking Process

```mermaid
sequenceDiagram
    participant Test as Test Function
    participant Decorator as @requires_capabilities
    participant Fixture as order_fixtures
    participant Backend as Database Backend
    participant Caps as DatabaseCapabilities
    
    Test->>Decorator: Execute test
    Decorator->>Fixture: Extract model class
    Fixture->>Decorator: Return (User, Order, OrderItem)
    Decorator->>Backend: Get backend from User
    Backend->>Caps: Query capabilities
    
    alt Category Check
        Decorator->>Caps: supports_category(category)
        Caps-->>Decorator: True/False
    else Specific Capability Check
        Decorator->>Caps: supports_cte(CTECapability.RECURSIVE_CTE)
        Caps-->>Decorator: True/False
    end
    
    alt Capability Supported
        Decorator->>Test: Proceed with test
    else Capability Not Supported
        Decorator->>Test: pytest.skip(reason)
    end
```

### Runtime vs Collection-Time Checking

**Collection-time checking** (in conftest.py):
- Faster - checks capabilities before test execution
- Requires access to backend during collection phase
- May need workaround if backend initialization is expensive
- Can cause issues if trying to access fixtures during setup

**Runtime checking** (in test or decorator):
- Slower - capabilities checked during test execution
- Always accurate - uses actual configured backend
- Recommended for dynamic capability scenarios
- Use `pytest_runtest_call` hook to access `item.funcargs` which contains already resolved fixtures

**Common Issue & Solution:**
If capability checks are performed in `pytest_runtest_setup` and attempt to access fixtures, it can cause issues like:
`AssertionError: (<Function test_func[memory]>, {})` - This happens when trying to access fixtures during test setup.
Move capability checks to `pytest_runtest_call` and access fixtures via `item.funcargs` instead of `request.getfixturevalue()`.

### Fixtures vs Raw Objects Access Patterns

**Composite Fixtures Return Pattern:**
When fixtures return tuples of models (like `order_fixtures` returns `(User, Order, OrderItem)`) but test expects a tuple:
- Test code may use: `Node = tree_fixtures[0]`
- But fixture returns raw object: `yield Node` instead of `yield (Node,)`
- This causes error: `TypeError: cannot be parametrized because it does not inherit from typing.Generic`
- Solution: Ensure fixture returns tuple if test code expects tuple indexing

**Correct Fixture Implementation:**
```python
# If test uses tree_fixtures[0], return a tuple
@pytest.fixture
def tree_fixtures(request):
    # Get Node model for the test via fixture group
    result = provider.setup_tree_fixtures(scenario)
    
    # Ensure we return a tuple for consistency with test expectation
    if isinstance(result, tuple):
        yield result
    else:
        # If only a single model is returned, wrap it in a tuple
        yield (result,)
```

## Provider Pattern Implementation

### Core Concept

The provider pattern enables test reuse across backends:

1. **Testsuite defines** test logic and provider interface
2. **Backend implements** provider to configure models/schemas
3. **Test execution** uses provider to run same tests on different backends
4. **Capability checking** determines which tests can run

### Provider Interface Example

```python
# Testsuite defines this
# src/rhosocial/activerecord/testsuite/feature/query/interfaces.py
from abc import ABC, abstractmethod
from typing import Type, List, Tuple
from rhosocial.activerecord import ActiveRecord


class IQueryProvider(ABC):
    """Provider interface for query feature tests."""
    
    @abstractmethod
    def get_test_scenarios(self) -> List[str]:
        """Return available test scenarios (e.g., 'local', 'docker')."""
        pass
    
    @abstractmethod
    def setup_order_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord]]:
        """
        Setup order-related models (User, Order, OrderItem).
        
        Returns:
            Tuple of (User, Order, OrderItem) model classes
        """
        pass
    
    @abstractmethod
    def setup_tree_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord]]:
        """
        Setup tree structure model (Node).
        
        Returns:
            Single-element tuple containing (Node,)
        """
        pass
    
    @abstractmethod
    def cleanup_after_test(self, scenario_name: str):
        """Cleanup after test execution."""
        pass
```

### Backend Provider Implementation

```python
# Backend implements this
# rhosocial-activerecord-mysql/tests/providers/mysql_query_provider.py
from rhosocial.activerecord.testsuite.feature.query.interfaces import IQueryProvider
from rhosocial.activerecord.backend.mysql import MySQLBackend

class MySQLQueryProvider(IQueryProvider):
    def get_test_scenarios(self):
        return ["local_mysql", "docker_mysql"]
    
    def setup_order_fixtures(self, scenario):
        """Setup and return User, Order, OrderItem models."""
        config = self._get_config(scenario)
        backend = MySQLBackend(config)
        
        # Configure models with backend
        User.configure(backend)
        Order.configure(backend)
        OrderItem.configure(backend)
        
        # Execute schema
        self._execute_schema_file("schemas/feature/query/order_models.sql", scenario)
        
        # MUST return tuple (even for single model)
        return (User, Order, OrderItem)
    
    def setup_tree_fixtures(self, scenario):
        """Setup and return Node model."""
        config = self._get_config(scenario)
        backend = MySQLBackend(config)
        
        Node.configure(backend)
        self._execute_schema_file("schemas/feature/query/tree_model.sql", scenario)
        
        # MUST return single-element tuple
        return (Node,)
    
    def cleanup(self, scenario):
        self._drop_all_tables(scenario)
```

### Composite Fixtures Usage Pattern

Tests receive fixtures as tuples and can unpack or index them:

```python
# Pattern 1: Unpacking multiple models
def test_basic_cte(order_fixtures):
    """Test with multiple models."""
    # Unpack the tuple returned by provider
    User, Order, OrderItem = order_fixtures
    
    user = User(username='test', email='test@example.com')
    order = Order(user_id=user.id, order_number='ORD-1')


# Pattern 2: Indexing single model from tuple
def test_recursive_cte_basics(tree_fixtures):
    """Test with single model in tuple."""
    # Extract the model from single-element tuple
    Node = tree_fixtures[0]
    
    root = Node(id=1, name="Root", parent_id=None)


# Pattern 3: Multiple models with indexing
def test_complex_scenario(order_fixtures):
    """Alternative access pattern."""
    User = order_fixtures[0]
    Order = order_fixtures[1]
    OrderItem = order_fixtures[2]
```

**Key Points:**
- Providers ALWAYS return tuples (even for single model: `(Model,)`)
- Tests can unpack: `Model1, Model2 = fixture`
- Tests can index: `Model = fixture[0]`
- Tuple unpacking is preferred for multiple models
- Indexing is acceptable for single-model tuples
- Tuples prevent accidental modification in tests

### Pytest Fixture Integration

```python
# Backend's conftest.py
import pytest
from .providers.mysql_query_provider import MySQLQueryProvider

# Register provider
_provider = MySQLQueryProvider()

@pytest.fixture
def order_fixtures(request):
    """Provide order-related models for tests."""
    scenario = request.config.getoption("--scenario", default="local_mysql")
    
    # Provider returns tuple
    fixtures = _provider.setup_order_fixtures(scenario)
    
    yield fixtures
    
    # Cleanup
    _provider.cleanup_after_test(scenario)


@pytest.fixture
def tree_fixtures(request):
    """Provide tree model for tests."""
    scenario = request.config.getoption("--scenario", default="local_mysql")
    
    # Provider returns single-element tuple
    fixtures = _provider.setup_tree_fixtures(scenario)
    
    yield fixtures
    
    _provider.cleanup_after_test(scenario)
```

## Directory Structure and Naming

### Testsuite Package Structure

```
python-activerecord-testsuite/
└── src/rhosocial/activerecord/testsuite/
    ├── feature/           # Core functionality tests
    │   ├── basic/         # CRUD operations
    │   ├── query/         # Query building
    │   │   ├── interfaces.py          # Provider interface
    │   │   ├── test_cte_basic.py      # Basic CTE tests
    │   │   └── test_cte_recursive.py  # Recursive CTE tests
    │   ├── relation/      # Relationships
    │   ├── events/        # Event hooks
    │   └── mixins/        # Mixin functionality
    ├── realworld/         # Business scenarios
    │   ├── ecommerce/
    │   ├── finance/
    │   └── social/
    ├── benchmark/         # Performance tests
    ├── core/              # Core testing infrastructure
    │   ├── registry.py    # Provider registry
    │   └── provider.py    # Base provider interface
    └── utils.py           # Testing utilities
```

### Backend Package Structure

```
rhosocial-activerecord-{backend}/
└── tests/
    ├── rhosocial/
    │   └── activerecord_test/
    │       ├── feature/
    │       │   ├── basic/             # Basic CRUD tests
    │       │   ├── query:             # Query functionality tests
    │       │   ├── relation/          # Relationship tests
    │       │   ├── events/            # Event hook tests
    │       │   ├── mixins/            # Mixin functionality tests
    │       │   └── backend/           # Backend-specific tests (Note: The structure below is an example from the current repository. Other backend implementations may use different directory names based on their specific needs and conventions)
    │       │       ├── common/        # Common backend interface tests
    │       │       ├── sqlite/       # SQLite backend tests (example from current repository)
    │       │       └── sqlite2/       # SQLite2 backend tests (example from current repository)
    │       └── realworld/             # Real-world scenario tests
    ├── providers/                     # Provider implementations
    │   └── {backend}_query_provider.py
    ├── schemas/                       # SQL schema files
    │   └── feature/
    │       └── query/
    │           ├── order_models.sql
    │           └── tree_model.sql
    ├── conftest.py                   # pytest configuration
    └── test_{backend}_*.py           # Backend-specific tests
```

### Naming Conventions

**Testsuite tests (backend-agnostic):**
- `feature/basic` → `python-activerecord-testsuite/.../feature/basic/`
- `feature/query` → `python-activerecord-testsuite/.../feature/query/`
- NO backend-specific naming

**Backend-specific tests:**
- `test_sqlite_*.py` → SQLite-specific tests
- `test_mysql_*.py` → MySQL-specific tests
- `test_pgsql_*.py` → PostgreSQL-specific tests
- MUST use prefix or subdirectory to distinguish from testsuite

## Test Execution Commands

### Quick Reference

```bash
# ALWAYS set PYTHONPATH first
export PYTHONPATH=src  # or equivalent for your platform

# Run local backend tests only (default)
pytest tests/

# Run testsuite validation tests
pytest tests/ --run-testsuite

# Run specific feature tests by directory
pytest tests/rhosocial/activerecord_test/feature/basic/  # Run basic CRUD tests
pytest tests/rhosocial/activerecord_test/feature/query/  # Run query tests
pytest tests/rhosocial/activerecord_test/feature/backend/sqlite/  # Run SQLite backend tests

# Run with capability report
pytest tests/ --run-testsuite --show-skipped-capabilities
```

### Test Organization and Execution

Tests are now primarily organized by directory structure rather than pytest markers. The following directory-based execution patterns are recommended:

```bash
# Feature tests by category
pytest tests/rhosocial/activerecord_test/feature/basic/     # Basic CRUD tests
pytest tests/rhosocial/activerecord_test/feature/query/     # Query functionality tests
pytest tests/rhosocial/activerecord_test/feature/relation/  # Relationship tests
pytest tests/rhosocial/activerecord_test/feature/events/    # Event hook tests
pytest tests/rhosocial/activerecord_test/feature/mixins/    # Mixin functionality tests

# Backend-specific tests
pytest tests/rhosocial/activerecord_test/feature/backend/common/   # Common backend interface tests
pytest tests/rhosocial/activerecord_test/feature/backend/sqlite/  # SQLite backend tests
pytest tests/rhosocial/activerecord_test/feature/backend/sqlite2/  # SQLite2 backend tests

# Real-world scenarios
pytest tests/rhosocial/activerecord_test/realworld/ecommerce/  # E-commerce scenarios
pytest tests/rhosocial/activerecord_test/realworld/finance/   # Financial scenarios

# Benchmarks
pytest tests/benchmark/                                     # Benchmark tests
```

While pytest markers still exist for backward compatibility and certain global classifications, the preferred method for test selection is through the directory structure, which provides clearer organization and eliminates the need for extensive marker definitions in conftest.py files.

Some commonly used markers for global classification:

## Writing Tests

### For Testsuite Authors

**Rules:**
- NEVER import backend-specific modules
- NEVER write SQL directly (use provider interface)
- NEVER assume database features without declaring capability requirements
- ALWAYS use fixtures provided by provider
- ALWAYS use pytest markers
- ALWAYS specify BOTH category AND specific capability in requirements

**Example:**

```python
# Good - backend-agnostic with capability declaration
from rhosocial.activerecord.backend.capabilities import (
    CapabilityCategory,
    CTECapability
)
from rhosocial.activerecord.testsuite.utils import requires_capabilities

@pytest.mark.feature
@pytest.mark.feature_query
@requires_capabilities((CapabilityCategory.CTE, CTECapability.BASIC_CTE))
def test_basic_cte(order_fixtures):
    """Test basic CTE functionality."""
    User, Order, OrderItem = order_fixtures
    
    user = User(username='test', email='test@example.com')
    assert user.save()

# Bad - missing category in capability requirement
@requires_capabilities(CTECapability.BASIC_CTE)  # WRONG - no category
def test_basic_cte(order_fixtures):
    pass

# Bad - backend-specific
def test_basic_cte():
    from rhosocial.activerecord.backend.mysql import MySQLBackend
    # DON'T DO THIS
```

### For Backend Developers

**Rules:**
- MUST implement all provider interface methods
- MUST create schema files matching testsuite structure
- MUST prefix backend-specific tests with `test_{backend}_`
- MUST handle database connection pooling
- MUST clean up test data
- MUST declare backend capabilities accurately using add_* methods
- MUST return tuples from provider methods (even for single model)

## Debugging Test Failures

### Common Issues

**Issue: ModuleNotFoundError**
```bash
# Cause: PYTHONPATH not set
# Fix: Set PYTHONPATH before running tests
export PYTHONPATH=src
pytest tests/
```

**Issue: Test skipped due to capabilities**
```bash
# Cause: Backend doesn't support required feature
# Fix: Check backend capability declaration
pytest tests/ --run-testsuite --show-skipped-capabilities
```

**Issue: Fixture returns wrong type**
```bash
# Cause: Provider not returning tuple
# Fix: Ensure provider returns tuple
return (Model,)  # Correct
return Model     # Wrong
```

**Issue: Cannot determine capability category**
```bash
# Cause: Only specific capability provided, no category
# Fix: Always provide (category, capability) tuple
@requires_capabilities((CapabilityCategory.CTE, CTECapability.BASIC_CTE))  # Correct
@requires_capabilities(CTECapability.BASIC_CTE)  # Wrong - no category
```

**Issue: Plugin registration conflicts**
```bash
# Error: RuntimeError: Plugin already registered under a different name
# Cause: Same plugin registered in multiple places (e.g., pytest_plugins and entry points)
# Fix: Remove duplicate registrations - choose one method (preferably entry points in pyproject.toml)
```

**Issue: Backend access method confusion**
```bash
# Old approach: model.get_backend() - does not exist
# Correct approach: model.backend() or model.__backend__
# In capability checking plugins, ensure using the IActiveRecord interface methods
```

**Issue: Fixtures accessed incorrectly in pytest hooks**
```bash
# Problem: Accessing fixtures in pytest_runtest_setup can cause:
# AssertionError: (<Function test_func[memory]>, {})
# Solution: Access fixtures in pytest_runtest_call via item.funcargs
# Or access them in auto-use fixtures using request.getfixturevalue()
```

**Issue: Tuple vs Object fixture mismatches**
```python
# Problem: Tests expect tuple indexing (fixture[0]) but fixture yields raw object
# Error: TypeError: cannot be parametrized because it does not inherit from typing.Generic
# Solution: Ensure fixture returns tuple if test code uses indexing
@pytest.fixture
def tree_fixtures(request):
    result = provider.setup_tree_fixtures(scenario)
    # Ensure we return a tuple for consistency 
    if isinstance(result, tuple):
        yield result
    else:
        yield (result,)  # Wrap single object in tuple
```

**Issue: Environment variable not set**
```bash
# Error: RuntimeError: The TESTSUITE_PROVIDER_REGISTRY environment variable is not set
# Cause: Missing environment variable that points to provider registry
# Fix: Set the environment variable, typically in testsuite conftest.py:
import os
os.environ.setdefault(
    'TESTSUITE_PROVIDER_REGISTRY',
    'providers.registry:provider_registry'
)
```

**Issue: Understanding skip messages**
```bash
# In the test output, you'll see skip messages like this:
# SKIPPED [1] ..\python-activerecord-testsuite\src\rhosocial\activerecord\testsuite\plugin\pytest_activerecord_capabilities.py:196: 
# Unsupported capabilities: AdvancedGroupingCapability.CUBE (tests/rhosocial/activerecord_test/feature/query/test_advanced_grouping.py::test_cube_basic[memory])

# The format is now: "Unsupported capabilities: [list of capabilities] (test_file_path::test_function_name[scenario])"
# This tells you exactly which test was skipped and why, making it easier to debug capability issues.
# Previously, it showed generic plugin information that was less helpful for identifying specific tests.
```

## Best Practices

### For AI Code Assistants

When executing tests:
1. **ALWAYS** set PYTHONPATH first
2. **ALWAYS** check platform (Linux/macOS/Windows)
3. **NEVER** assume tests will work without PYTHONPATH
4. **VERIFY** command syntax for user's shell environment
5. **PROVIDE** platform-specific commands
6. **CHECK** capability requirements use (category, capability) format

### For Developers

When writing tests:
1. **Backend-agnostic first**: Default to testsuite structure
2. **Provider pattern**: Use fixtures, not direct DB access
3. **Clear markers**: Tag all tests appropriately
4. **Declare capabilities correctly**: Always use (category, capability) format
5. **Return tuples**: Providers must return tuples for consistency
6. **Document requirements**: Comment on capability needs
7. **Minimize redundant markers**: If tests can be distinguished by directory structure, avoid adding equivalent markers in conftest.py files

### For Backend Implementers

When implementing backends:
1. **Accurate capability declaration**: Use add_* methods correctly
2. **Complete provider implementation**: Implement all interface methods
3. **Return tuples consistently**: Even single models should be in tuples
4. **Schema versioning**: Match schema structure to testsuite organization
5. **Cleanup thoroughly**: Don't leave test data between runs

### For Plugin Developers

When developing pytest plugins for capability checking:
1. **Use appropriate pytest hooks**: Use `pytest_runtest_call` to access resolved fixtures via `item.funcargs`, not `pytest_runtest_setup`
2. **Avoid multiple plugin registration**: Register plugins either via `pytest_plugins` or entry points, never both
3. **Proper backend access**: Access backend via `model.backend()` or `model.__backend__` following the IActiveRecord interface
4. **Error handling**: Add detailed logging to help debug capability check failures
5. **Environment setup**: Ensure necessary environment variables (like `TESTSUITE_PROVIDER_REGISTRY`) are set in conftest.py

### For Plugin Developers

When creating pytest plugins for capability checking:
1. **Use `pytest_runtest_call` hook** to access `item.funcargs` which contains resolved fixtures
2. **Avoid `pytest_runtest_setup`** when accessing fixtures that might cause initialization issues
3. **Handle exceptions gracefully** in plugin code to prevent test failures
4. **Use entry points registration** instead of pytest_plugins to avoid conflicts
5. **Access backend correctly** using IActiveRecord interface: `model.backend()` or `model.__backend__`
6. **Set required environment variables** in the testsuite conftest.py to ensure provider registry access
7. **Test plugin behavior** with different fixture types (single objects, tuples, etc.)

## Backend Test Organization

### Current Implementation Structure

The backend tests are organized in a hierarchical structure that reflects both feature-based organization and backend-specific implementations:

```
tests/rhosocial/activerecord_test/
├── feature/                    # Feature-based test organization
│   ├── basic/                 # Basic CRUD operations
│   │   ├── test_crud.py      # Basic CRUD tests
│   │   ├── test_fields.py    # Field operations tests
│   │   └── test_validation.py # Validation tests
│   ├── query/                 # Query functionality
│   │   ├── test_basic.py             # Basic query tests
│   │   ├── test_cte_basic.py         # Basic CTE tests
│   │   ├── test_cte_recursive.py     # Recursive CTE tests
│   │   ├── test_joins.py            # Join operation tests
│   │   ├── sqlite/                  # SQLite-specific query tests
│   │   │   ├── test_explain_basic.py      # SQLite EXPLAIN tests
│   │   │   └── test_explain_cte_basic.py  # SQLite CTE EXPLAIN tests
│   │   └── schema/                  # SQL schema files
│   │       ├── users.sql
│   │       ├── orders.sql
│   │       └── order_items.sql
│   ├── relation/              # Relationship operations
│   ├── events/               # Event hooks
│   ├── mixins/               # Mixin functionality
│   └── backend/              # Backend-specific functionality
│       ├── common/           # Common backend interface tests
│       ├── sqlite/          # SQLite backend tests
│       └── sqlite2/         # SQLite2 backend tests
└── realworld/                # Real-world scenario tests
```

### Test Categories

**1. Feature Tests**
- Located in `tests/rhosocial/activerecord_test/feature/*/`
- Contain actual test implementations for specific ActiveRecord features
- May include backend-specific subdirectories (e.g., `query/sqlite/`) for backend-specific test cases
- Use standard pytest test discovery with descriptive test function names

**2. Backend Common Tests**
- Located in `tests/rhosocial/activerecord_test/feature/backend/common/`
- Tests that validate common backend interface behaviors
- Ensure all backends follow the same interface contract
- Use provider pattern for backend adaptation

**3. Backend-Specific Tests**
- Located in `tests/rhosocial/activerecord_test/feature/backend/{backend_name}/`
- Tests for backend-specific functionality and optimizations
- Validate dialect-specific features and behaviors
- Include performance and capability-specific tests
- May include SQLite-specific tests like EXPLAIN functionality tests

### Implementation Strategy

The current implementation follows these principles:

1. **Feature-first organization**: Tests are grouped by ActiveRecord features rather than by backend types
2. **Direct test implementation**: Tests are implemented directly rather than separated into interface/scenario patterns
3. **Backend-specific subdirectories**: When backend-specific test cases are needed, they are placed in subdirectories (e.g., `query/sqlite/`)
4. **Provider pattern**: Backend-specific adaptations for feature tests are handled through the provider mechanism
5. **Capability declaration**: Backends declare their supported capabilities to enable selective test execution
6. **Schema organization**: SQL schema files are organized by feature to support different test scenarios

This structure ensures clear test organization while allowing for both generic feature testing and backend-specific validation.

## Quick Command Reference

```bash
# Setup (REQUIRED)
export PYTHONPATH=src  # Linux/macOS
$env:PYTHONPATH="src"  # Windows PowerShell

# Basic execution
pytest tests/                              # Local tests only
pytest tests/ --run-testsuite              # Include testsuite

# Directory-based execution (preferred method)
pytest tests/rhosocial/activerecord_test/feature/basic/     # Basic CRUD tests
pytest tests/rhosocial/activerecord_test/feature/query/     # Query tests
pytest tests/rhosocial/activerecord_test/feature/backend/sqlite/  # SQLite backend tests

# With capability reporting
pytest tests/ --run-testsuite --show-skipped-capabilities

# Debug mode
pytest -v tests/                           # Verbose
pytest --lf tests/                         # Last failed
pytest -k "test_create" tests/             # Name filter
pytest --collect-only tests/               # Show what would be collected
```

## Summary

**Critical constraints for AI assistants:**
- ✅ MUST set PYTHONPATH=src before pytest
- ✅ MUST provide platform-specific commands
- ✅ MUST understand testsuite vs backend division
- ✅ MUST understand provider pattern and composite fixtures
- ✅ MUST use (category, capability) format for requirements
- ✅ NEVER run pytest without PYTHONPATH
- ✅ NEVER assume test discovery will work
- ✅ Ensure plugin registration is not duplicated across multiple mechanisms
- ✅ Access fixtures in the right pytest hook (use `pytest_runtest_call` for `item.funcargs`)
- ✅ Use correct backend access methods (`model.backend()` or `model.__backend__`)

**Key concepts:**
- Two-layer architecture (testsuite + backend)
- Provider pattern for test reuse
- Composite fixtures (always return tuples)
- Two-level capability hierarchy (category + specific)
- Backend capability declaration using add_* methods
- Backend-agnostic test logic
- Backend-specific implementation details
- PYTHONPATH requirement for execution

**Key lessons learned during this session:**
1. Pytest plugins accessing fixtures during `pytest_runtest_setup` can cause assertion errors; use `pytest_runtest_call` and access fixtures via `item.funcargs`
2. Plugin registration conflicts occur when registering the same plugin via multiple methods (pytest_plugins and entry points)
3. Backend access methods must follow the IActiveRecord interface (`model.backend()` not `model.get_backend()`)
4. Fixture return values need to match test expectations (tuples vs raw objects)
5. Environment variables like `TESTSUITE_PROVIDER_REGISTRY` must be set for provider registry access
6. Detailed error logging in plugin code helps identify and resolve fixture access issues quickly
7. When tests are unexpectedly interrupted, check for leftover temporary database files in system temp directory with names like `test_activerecord_*_*.sqlite` that need manual cleanup

## Temporary Database Files and Cleanup

### Temporary File Naming Convention

The testing framework generates temporary SQLite database files with the following naming convention when using file-based scenarios (e.g., "tempfile") to ensure test isolation:

```
test_activerecord_{scenario_name}_{uuid_hex}.sqlite
```

**Example:**
- `test_activerecord_tempfile_a1b2c3d4e5f678901234567890123456.sqlite`

### Handling Unexpected Test Interruption

If tests are unexpectedly interrupted (crashes, manual termination, etc.), temporary database files may be left in the system temporary directory. These files need to be manually cleaned up to free disk space and avoid confusion with future test runs.

**Manual Cleanup Command:**
```bash
# Linux/macOS (bash/zsh)
find $(mktemp -d) -name "test_activerecord_*.sqlite" -delete

# Alternative for Linux/macOS to find in standard temp directory
find /tmp -name "test_activerecord_*.sqlite" -delete

# Windows (PowerShell)
Get-ChildItem -Path $env:TEMP -Name "test_activerecord_*.sqlite" | Remove-Item

# Windows (CMD)
del /q %TEMP%\test_activerecord_*.sqlite
```