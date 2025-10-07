"""
Pytest configuration for feature/relation tests.

This file bridges the local backend-specific tests with the general testsuite.
"""
import pytest
import os


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


def pytest_configure(config):
    """
    Configure pytest with custom markers for feature/relation tests.
    """
    config.addinivalue_line(
        "markers", "feature_relation: Tests for relation functionality"
    )
    config.addinivalue_line(
        "markers", "relation: Tests specifically for relation module"
    )


def pytest_collection_modifyitems(config, items):
    """
    Modify test items during collection to add markers.
    """
    for item in items:
        if "relation" in item.nodeid:
            item.add_marker(pytest.mark.feature)
            item.add_marker(pytest.mark.feature_relation)