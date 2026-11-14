# tests/rhosocial/activerecord_test/feature/backend/sqlite/dialect-ddl/conftest.py
"""Schedule this directory's IO tests on one xdist worker."""
import pytest

GROUP = "sqlite:dialect-ddl"


def pytest_collection_modifyitems(items):
    for item in items:
        item.add_marker(pytest.mark.xdist_group(GROUP))
