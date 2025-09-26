# tests/rhosocial/activerecord_test/feature/query/conftest.py
"""
Pytest configuration for query feature tests.

This file sets up the environment for running the testsuite's query tests
against this backend implementation.
"""
import os

# Set the environment variable that the testsuite uses to locate the provider registry.
# This must be done before any testsuite modules are imported.
os.environ.setdefault(
    'TESTSUITE_PROVIDER_REGISTRY',
    'tests.providers.registry:provider_registry'
)