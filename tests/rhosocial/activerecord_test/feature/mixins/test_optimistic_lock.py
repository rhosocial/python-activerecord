# tests/rhosocial/activerecord_test/feature/mixins/test_optimistic_lock.py
"""
Test optimistic locking functionality

Directly import and run the testsuite's optimistic locking tests.
"""

# Set the environment variable that the testsuite uses to locate the provider registry.
# The testsuite is a generic package and doesn't know the specific location of the
# provider implementations for this backend (SQLite). This environment variable
# acts as a bridge, pointing the testsuite to the correct import path.
import os
os.environ.setdefault(
    'TESTSUITE_PROVIDER_REGISTRY',
    'tests.providers.registry:provider_registry'
)

# Import the test functions from the testsuite
from rhosocial.activerecord.testsuite.feature.mixins.test_optimistic_lock import *