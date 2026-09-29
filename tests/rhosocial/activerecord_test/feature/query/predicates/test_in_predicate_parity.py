# tests/rhosocial/activerecord_test/feature/query/predicates/test_in_predicate_parity.py
"""
Bridge file for the IN / NOT IN input-shape parity tests from the testsuite.

``not_in()`` used to call ``tuple(values)`` unconditionally, so a subquery
passed to it was exploded into bind parameters instead of rendering
``NOT IN (SELECT ...)``. It now delegates to ``in_()`` and negates the result.
"""

from rhosocial.activerecord.testsuite.feature.query.predicates.test_in_predicate_parity import *  # noqa: F403
