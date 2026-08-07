# tests/rhosocial/activerecord_test/feature/basic/ddl/test_alter_table_if_exists.py
"""
ALTER TABLE IF [NOT] EXISTS tests (sync) for the SQLite backend.

Thin bridge that runs the shared testsuite contract against the plain
SQLite dialect, which renders ADD/DROP COLUMN and DROP CONSTRAINT without
any ``IF [NOT] EXISTS`` qualifier (the modifier tests are skipped via
``@requires_protocol``).
"""

from rhosocial.activerecord.testsuite.feature.basic.ddl.test_alter_table_if_exists import *  # noqa: F403