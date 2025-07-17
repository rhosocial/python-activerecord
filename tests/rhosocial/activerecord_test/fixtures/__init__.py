# tests/rhosocial/activerecord_test/fixtures/__init__.py
"""Test Fixtures Module

Provides reusable test fixtures and model definitions for testing.
"""

# Import fixture modules
try:
    from . import events
except ImportError:
    pass

try:
    from . import storage
except ImportError:
    pass

# Community fixtures
try:
    from . import community
except ImportError:
    pass

# Mixin fixtures
try:
    from . import mixins
except ImportError:
    pass

__all__ = [
    'events',
    'storage',
    'community',
    'mixins',
]