# tests/rhosocial/activerecord_test/feature/mixins/test_combined_articles.py
"""
Combined Articles Mixin Tests

Directly import and run the testsuite's combined articles mixin tests.
"""

# IMPORTANT: The import of test functions with `*` is essential for pytest to work correctly.
# Even though they may be flagged as "unused" by some IDEs or linters,
# they must not be removed. They are the mechanism by which pytest discovers
# the tests from the external testsuite package by bringing them into this module's scope.

# Fixtures (e.g., article_model) are automatically discovered by pytest from `conftest.py` files
# in the test path and do not need to be explicitly imported here for pytest to find them.
# Explicit imports might be added for IDE-specific code completion or type checking,
# but are not required for test execution.

from rhosocial.activerecord.testsuite.feature.mixins.test_combined_articles import *