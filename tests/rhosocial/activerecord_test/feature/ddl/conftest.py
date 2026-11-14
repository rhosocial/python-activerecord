# tests/rhosocial/activerecord_test/feature/ddl/conftest.py
# Bridge fixtures: the shared suite owns the fixtures and the test cases; this
# file only makes them visible in this backend's tree.  The ddl tests render
# statements instead of creating tables, so no directory database is declared.

from rhosocial.activerecord.testsuite.feature.ddl.conftest import *  # noqa: F403
