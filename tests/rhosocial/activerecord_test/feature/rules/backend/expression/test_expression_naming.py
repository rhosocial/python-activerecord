# tests/rhosocial/activerecord_test/feature/rules/backend/test_expression_naming.py
"""The generic layer's namespace rules, run against core's own subject.

The assertions are imported from the shared contracts unchanged. What differs
from a backend's run is the subject, supplied by this directory's conftest: core
owns the shared vocabulary, so it has no name to claim and the ownership claim is
reported as not applicable rather than passed.

Nothing here names an implementation. ``impl`` is excluded from the scanned
trees, and the package root this subject keeps open is that umbrella -- core's
own extension point -- not any backend's package.
"""

from rhosocial.activerecord.testsuite.feature.rules.contracts.naming import *  # noqa: F401,F403,E501
