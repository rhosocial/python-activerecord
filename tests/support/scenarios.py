# tests/support/scenarios.py
"""Scenario declarations for backend-owned benchmark suites."""

from support.sqlite import scenario

SCENARIOS = {"default": {}}


def get_enabled_scenarios():
    """Return the scenarios this backend enables."""
    return SCENARIOS


def get_scenario(name):
    """Return the backend class and connection config for a scenario."""
    current = scenario(name)
    return current.backend_class, current.make_config("benchmark")
