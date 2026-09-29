# tests/rhosocial/activerecord_test/feature/query/joins/test_one_respects_join.py
"""
Bridge file for the joined ``one()`` regression tests from the testsuite.

``ActiveQuery.one()`` and ``AsyncActiveQuery.one()`` used to build their
internal query from a bare table reference, silently discarding the join
clause that ``all()`` / ``to_sql()`` / ``aggregate()`` all honour.
"""

from rhosocial.activerecord.testsuite.feature.query.joins.test_one_respects_join import *  # noqa: F403
