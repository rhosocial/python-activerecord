# src/rhosocial/activerecord/testsuite/feature/events/conftest.py
"""
This file defines the pytest fixtures for the "events" feature test group.

Fixtures are a core concept in pytest. They are functions that provide a fixed
baseline state or data for tests. In this case, they provide fully configured
ActiveRecord model classes that are ready to be used in tests.

The key mechanism here is `pytest.fixture` parameterization. The fixtures are
parameterized by the list of "scenarios" provided by the backend's provider.
This causes pytest to run each test that uses one of these fixtures multiple times,
once for each database configuration (scenario) the backend supports.
"""
import pytest
from rhosocial.activerecord.testsuite.core.registry import get_provider_registry


def get_scenarios():
    """
    A helper function that runs during pytest's collection phase to discover
    all available test scenarios from the backend's registered provider.
    """
    # Dynamically get the registry and the provider for this test group.
    provider_registry = get_provider_registry()
    provider_class = provider_registry.get_provider("feature.events.IEventsProvider")
    if not provider_class:
        return []
    # Instantiate the provider and get the list of scenario names.
    return provider_class().get_test_scenarios()


# Discover the scenarios at module import time.
scenarios = get_scenarios()

# If no scenarios are found, create a single dummy parameter that will cause
# the tests to be skipped with a helpful message.
SCENARIO_PARAMS = scenarios if scenarios else [pytest.param("default", marks=pytest.mark.skip(reason="No testsuite scenarios found"))]


@pytest.fixture(scope="function", params=SCENARIO_PARAMS)
def event_model(request):
    """
    A pytest fixture that provides a configured `EventTestModel` model class for testing.
    It is parameterized to run for each available scenario.
    It also handles the setup and teardown for each test.
    """
    # `request.param` holds the current scenario name (e.g., "memory", "file").
    scenario = request.param
    provider_registry = get_provider_registry()
    provider_class = provider_registry.get_provider("feature.events.IEventsProvider")
    provider = provider_class()
    
    # Ask the provider to set up the database and configure the EventTestModel for this scenario.
    Model = provider.setup_event_model(scenario)
    
    # `yield` passes the configured model class to the test function.
    yield Model
    
    # After the test function finishes, the code below this line runs as a teardown.
    provider.cleanup_after_test(scenario)


@pytest.fixture(scope="function", params=SCENARIO_PARAMS)
def event_tracking_model(request):
    """
    A pytest fixture that provides a configured `EventTrackingModel` model class for testing.
    It is parameterized to run for each available scenario.
    It also handles the setup and teardown for each test.
    """
    # `request.param` holds the current scenario name (e.g., "memory", "file").
    scenario = request.param
    provider_registry = get_provider_registry()
    provider_class = provider_registry.get_provider("feature.events.IEventsProvider")
    provider = provider_class()
    
    # Ask the provider to set up the database and configure the EventTrackingModel for this scenario.
    # We'll need to add a specific method for this in the provider
    Model = provider.setup_event_tracking_model(scenario)
    
    # `yield` passes the configured model class to the test function.
    yield Model
    
    # After the test function finishes, the code below this line runs as a teardown.
    provider.cleanup_after_test(scenario)