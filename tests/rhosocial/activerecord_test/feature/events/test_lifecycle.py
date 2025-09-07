# tests/rhosocial/activerecord_test/feature/events/test_lifecycle.py
"""
Event Lifecycle Tests

Directly import and run the testsuite's event lifecycle tests.
"""

# IMPORTANT: These imports are essential for pytest to work correctly.
# Even though they may be flagged as "unused" by some IDEs or linters,
# they must not be removed. They are the mechanism by which pytest discovers
# the fixtures and the tests from the external testsuite package.

# Although the root conftest.py sets up the environment, explicitly importing
# the fixtures here makes the dependency clear and can help with test discovery
# in some IDEs. These fixtures are defined in the testsuite package and are
# parameterized to run against the scenarios defined in `providers/scenarios.py`.
from rhosocial.activerecord.testsuite.feature.events.conftest import (
    event_model,
    event_tracking_model,
)

# By importing *, we bring all the test functions (e.g., `test_save_lifecycle_events`)
# from the generic testsuite file into this module's scope. `pytest` then
# discovers and runs them as if they were defined directly in this file.
from rhosocial.activerecord.testsuite.feature.events.test_lifecycle import *