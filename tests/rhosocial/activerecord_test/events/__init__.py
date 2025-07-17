# tests/rhosocial/activerecord_test/events/__init__.py
"""Event System Test Module

Provides test cases for the event system including
lifecycle events and event handlers.
"""

# Import test modules
try:
    from . import test_lifecycle
except ImportError:
    pass

try:
    from . import test_handlers
except ImportError:
    pass

# Import fixtures if available
try:
    from . import fixtures
except ImportError:
    pass

__all__ = [
    'test_lifecycle',
    'test_handlers',
    'fixtures',
]