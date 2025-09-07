# tests/rhosocial/activerecord_test/basic/__init__.py
"""Basic Functionality Test Module

Provides test cases for basic ActiveRecord functionality including
CRUD operations, field handling, and validation.
"""

# Import test modules
try:
    from . import test_crud
except ImportError:
    pass

try:
    from . import test_fields
except ImportError:
    pass

try:
    from . import test_validation
except ImportError:
    pass

# Import fixtures if available
try:
    from . import fixtures
except ImportError:
    pass

__all__ = [
    'test_crud',
    'test_fields',
    'test_validation',
    'fixtures',
]
