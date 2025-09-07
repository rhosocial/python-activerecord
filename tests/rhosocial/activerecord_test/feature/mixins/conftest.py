# tests/rhosocial/activerecord_test/feature/mixins/conftest.py
"""
Pytest configuration for mixins feature tests.

This file sets up the environment for running the testsuite's mixins tests
against this backend implementation.
"""
import os

# Set the environment variable that the testsuite uses to locate the provider registry.
# This must be done before any testsuite modules are imported.
os.environ.setdefault(
    'TESTSUITE_PROVIDER_REGISTRY',
    'tests.providers.registry:provider_registry'
)

# Import the fixtures from the testsuite to make them available
from rhosocial.activerecord.testsuite.feature.mixins.conftest import *