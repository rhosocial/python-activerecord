# tests/rhosocial/activerecord_test/feature/backend/sqlite/dialect/conftest.py
"""
Conftest for SQLite backend tests.

This test suite for the 'expression-dialect' system tests SQLite dialects with different versions
to verify version-specific feature support.
"""

import pytest
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend


def _id_from_version(version):
    """Generate test ID from version tuple."""
    return f"sqlite_{'_'.join(map(str, version))}"


@pytest.fixture
def sqlite_backend():
    """Provides a SQLiteBackend instance connected to an in-memory database."""
    backend = SQLiteBackend(database=":memory:")
    backend.connect()
    backend.introspect_and_adapt()
    yield backend
    backend.disconnect()


@pytest.fixture(
    params=[
        (3, 8, 0),  # no optional features
        (3, 8, 3),  # CTE
        (3, 24, 0),  # UPSERT
        (3, 25, 0),  # window functions
        (3, 28, 0),  # window EXCLUDE / GROUPS
        (3, 30, 0),  # FILTER, NULLS FIRST/LAST
        (3, 34, 0),  # multiple recursive terms
        (3, 35, 0),  # RETURNING, generalized UPSERT
        (3, 35, 4),  # RETURNING defect fixes
        (3, 38, 0),  # built-in JSON, -> operators
        (3, 41, 0),  # JSON5
        (3, 44, 0),  # ORDER BY in aggregates, CONCAT
        (3, 45, 0),  # JSONB
        (3, 51, 0),  # jsonb_each / jsonb_tree
        (3, 53, 0),  # ADD/DROP CONSTRAINT, REINDEX EXPRESSIONS, json_array_insert
    ],
    ids=_id_from_version,
)
def sqlite_dialect(request):
    """Provides a SQLiteDialect instance configured for a specific SQLite version."""
    version = request.param
    return SQLiteDialect(version=version)


@pytest.fixture
def sqlite_dialect_3_8_0():
    """Provides a SQLiteDialect instance for version 3.8.0 (basic features)."""
    return SQLiteDialect(version=(3, 8, 0))


@pytest.fixture
def sqlite_dialect_3_8_3():
    """Provides a SQLiteDialect instance for version 3.8.3 (with CTE support)."""
    return SQLiteDialect(version=(3, 8, 3))


@pytest.fixture
def sqlite_dialect_3_24_0():
    """Provides a SQLiteDialect instance for version 3.24.0 (with UPSERT support)."""
    return SQLiteDialect(version=(3, 24, 0))


@pytest.fixture
def sqlite_dialect_3_25_0():
    """Provides a SQLiteDialect instance for version 3.25.0 (with window functions)."""
    return SQLiteDialect(version=(3, 25, 0))


@pytest.fixture
def sqlite_dialect_3_28_0():
    """Provides a SQLiteDialect instance for version 3.28.0 (enhanced window functions)."""
    return SQLiteDialect(version=(3, 28, 0))


@pytest.fixture
def sqlite_dialect_3_30_0():
    """Provides a SQLiteDialect instance for version 3.30.0 (with FILTER clause and NULLS FIRST/LAST)."""
    return SQLiteDialect(version=(3, 30, 0))


@pytest.fixture
def sqlite_dialect_3_34_0():
    """Provides a SQLiteDialect instance for version 3.34.0 (enhanced recursive CTEs)."""
    return SQLiteDialect(version=(3, 34, 0))


@pytest.fixture
def sqlite_dialect_3_35_0():
    """Provides a SQLiteDialect instance for version 3.35.0 (with RETURNING clause and generalized UPSERT)."""
    return SQLiteDialect(version=(3, 35, 0))


@pytest.fixture
def sqlite_dialect_3_35_4():
    """Provides a SQLiteDialect instance for version 3.35.4 (with fixed RETURNING clause)."""
    return SQLiteDialect(version=(3, 35, 4))


@pytest.fixture
def sqlite_dialect_3_38_0():
    """Provides a SQLiteDialect instance for version 3.38.0 (with built-in JSON support and -> operators)."""
    return SQLiteDialect(version=(3, 38, 0))


@pytest.fixture
def sqlite_dialect_3_41_0():
    """Provides a SQLiteDialect instance for version 3.41.0 (with JSON5 extensions)."""
    return SQLiteDialect(version=(3, 41, 0))


@pytest.fixture
def sqlite_dialect_3_44_0():
    """Provides a SQLiteDialect instance for version 3.44.0 (with ORDER BY in aggregates and CONCAT functions)."""
    return SQLiteDialect(version=(3, 44, 0))


@pytest.fixture
def sqlite_dialect_3_45_0():
    """Provides a SQLiteDialect instance for version 3.45.0 (with JSONB format)."""
    return SQLiteDialect(version=(3, 45, 0))


@pytest.fixture
def sqlite_dialect_3_51_0():
    """Provides a SQLiteDialect instance for version 3.51.0 (with enhanced JSONB functions)."""
    return SQLiteDialect(version=(3, 51, 0))


@pytest.fixture
def sqlite_dialect_3_53_0():
    """Provides a SQLiteDialect for 3.53.0 (constraints, REINDEX EXPRESSIONS, JSON array insert)."""
    return SQLiteDialect(version=(3, 53, 0))
