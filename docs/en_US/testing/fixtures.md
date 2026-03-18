# Environment-Aware Fixture Selection System

The test suite provides an environment-aware fixture selection mechanism that automatically chooses the most appropriate model class based on the runtime Python version. This allows test code to leverage newer Python language features while maintaining backward compatibility.

## Overview

### Design Goals

1. **Version Awareness**: Select the optimal model implementation based on runtime Python version
2. **Progressive Enhancement**: Users on newer Python versions get better type hints and language features
3. **Backward Compatibility**: Users on older Python versions can still run tests normally
4. **Transparent Integration**: Backend developers don't need to worry about version details, automatically getting the best implementation

### Version-Specific Features

| Python Version | Feature | Example |
|----------------|---------|---------|
| 3.10+ | Union type syntax | `int \| None` instead of `Optional[int]` |
| 3.11+ | Self type | Precise return types for chainable methods |
| 3.12+ | @override decorator | Explicit method override marking |
| 3.12+ | Type parameter syntax | `class Model[T]:` instead of `Generic[T]` |

## Architecture

### Fixture File Structure

Each feature module's fixtures directory contains multiple version-specific model files:

```
testsuite/feature/query/fixtures/
├── models.py           # Base version (Python 3.8+)
├── models_py310.py     # Python 3.10+ features
├── models_py311.py     # Python 3.11+ features
└── models_py312.py     # Python 3.12+ features
```

### Version Declaration Mechanism

Each version-specific model class declares its minimum Python version requirement through the `__requires_python__` attribute:

```python
# models_py312.py
from typing import ClassVar, override
from rhosocial.activerecord.model import ActiveRecord

class User(ActiveRecord):
    __requires_python__ = (3, 12)  # Declare minimum version

    id: int | None = None
    username: str

    @override
    def get_display_name(self) -> str:
        return self.username
```

### Selector Function

The test suite provides the `select_fixture()` function for selecting the most appropriate model class:

```python
from rhosocial.activerecord.testsuite.utils import select_fixture

# Select highest compatible version
User = select_fixture([UserPy312, UserPy311, UserPy310, UserBase])
```

Selection logic:
1. Check each candidate class in list order
2. Verify the class's `__requires_python__` attribute
3. Return the first class satisfying the current Python version
4. If no match, return the last class in the list (usually the base version)

## Backend Integration

### Provider Implementation Pattern

Backend developers should use the fixture selection pattern at the module level:

```python
# tests/providers/query.py
import sys
from rhosocial.activerecord.testsuite.utils import select_fixture

# Import base version
from rhosocial.activerecord.testsuite.feature.query.fixtures.models import (
    User as UserBase,
    Order as OrderBase,
)

# Conditional import of higher versions
UserPy310 = UserPy311 = UserPy312 = None
if sys.version_info >= (3, 10):
    from rhosocial.activerecord.testsuite.feature.query.fixtures.models_py310 import (
        User as UserPy310,
    )
if sys.version_info >= (3, 11):
    from rhosocial.activerecord.testsuite.feature.query.fixtures.models_py311 import (
        User as UserPy311,
    )
if sys.version_info >= (3, 12):
    from rhosocial.activerecord.testsuite.feature.query.fixtures.models_py312 import (
        User as UserPy312,
    )

# Module-level selection of the most appropriate model class
User = select_fixture([UserPy312, UserPy311, UserPy310, UserBase])
Order = select_fixture([OrderPy312, OrderPy311, OrderPy310, OrderBase])
```

### Helper Function

To simplify repetitive code, you can define a module-level helper function:

```python
def _select_model_class(base_class, *versioned_classes, name: str):
    """Select the highest compatible version of a model class"""
    candidates = [c for c in versioned_classes if c is not None]
    if not candidates:
        return base_class
    return select_fixture([*candidates, base_class])
```

## Supported Feature Modules

The following feature modules support environment-aware fixture selection:

| Module | Base | py310 | py311 | py312 |
|--------|------|-------|-------|-------|
| basic | ✅ | ✅ | ✅ | ✅ |
| events | ✅ | ✅ | ✅ | ✅ |
| mixins | ✅ | ✅ | ✅ | ✅ |
| query | ✅ | ✅ | ✅ | ✅ |
| relation | ✅ | ✅ | ✅ | ✅ |

## Best Practices

### 1. Select Models at Module Level

Recommended to complete model selection at module level, not inside methods:

```python
# ✅ Recommended: Module-level selection
User = select_fixture([UserPy312, UserPy311, UserPy310, UserBase])

class QueryProvider:
    def setup_user_fixtures(self):
        user = User(username="test")
        # ...

# ❌ Not recommended: Import inside method
class QueryProvider:
    def setup_user_fixtures(self):
        from rhosocial.activerecord.testsuite.feature.query.fixtures.models import User
        user = User(username="test")
```

### 2. Maintain Consistent Import Order

Always arrange candidate classes from highest to lowest version:

```python
# ✅ Correct order: Higher versions first
Model = select_fixture([ModelPy312, ModelPy311, ModelPy310, ModelBase])

# ❌ Wrong order: Lower versions first prevents using new features
Model = select_fixture([ModelBase, ModelPy310, ModelPy311, ModelPy312])
```

### 3. Handle Optional Dependencies

Some version-specific features may depend on new standard library modules:

```python
from typing import ClassVar

# Python 3.11+ Self type
if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self
```
