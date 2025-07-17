# tests/rhosocial/activerecord_test/interface/__init__.py
"""Interface Test Module

Provides test cases for interface implementations and
thread safety functionality.
"""

# Import test modules
try:
    from . import test_threadsafe_dict
except ImportError:
    pass

__all__ = [
    'test_threadsafe_dict',
]