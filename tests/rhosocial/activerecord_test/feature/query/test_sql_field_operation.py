# tests/rhosocial/activerecord_test/feature/query/test_sql_field_operation.py
"""
This is a "bridge" file for the SQL Field Operation test group.

Its purpose is to import the generic tests from the `rhosocial-activerecord-testsuite`
package and make them discoverable by `pytest` within this project's test run.
"""

# Import fixtures that the tests will use.
from rhosocial.activerecord.testsuite.feature.query.conftest import (
    order_fixtures,
)

# Import all tests from the corresponding file in the testsuite.
from rhosocial.activerecord.testsuite.feature.query.test_sql_field_operation import *
