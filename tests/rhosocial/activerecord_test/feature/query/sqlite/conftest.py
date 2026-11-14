# tests/rhosocial/activerecord_test/feature/query/sqlite/conftest.py
"""The SQLite-only query test set.

These tests are backend-specific, so the fixture group lives here rather than
in the shared suite; the tables still come from the topic's declarations.
"""
from rhosocial.activerecord.testsuite.feature.query.fixtures import tables

GROUP_TABLES = ("json_users", "users", "orders", "order_items")


def ensure_database(environment):
    """Create the directory's database, or clear it when it already exists."""
    environment.reset_database()


def prepare(environment):
    """Create the group's tables before every test."""
    for name in GROUP_TABLES:
        environment.execute(tables.QUERY_TABLES[name](environment.dialect))


def teardown(environment):
    """Drop the group's tables after every test."""
    for name in reversed(GROUP_TABLES):
        environment.execute(tables.drop_table(environment.dialect, name))
