"""
Pytest configuration for feature/relation tests.

This file imports the standardized fixtures from the testsuite.
"""
import pytest
import os

# Import all fixtures from the testsuite
from rhosocial.activerecord.testsuite.feature.relation.conftest import *  # noqa: F401,F403


# Set the PYTHONPATH to include the src directory when running tests
# This is required for the imports to work properly
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Set up the test environment before any tests run.
    """
    # Set the TESTSUITE_PROVIDER_REGISTRY environment variable
    # This is required for the testsuite to find the provider implementations
    if 'TESTSUITE_PROVIDER_REGISTRY' not in os.environ:
        os.environ['TESTSUITE_PROVIDER_REGISTRY'] = 'providers.registry:provider_registry'