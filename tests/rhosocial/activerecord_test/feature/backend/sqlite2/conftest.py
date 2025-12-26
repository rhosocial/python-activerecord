"""
Conftest for SQLite2 backend tests.

This test suite for the 'expression-dialect' system tests SQLite dialects with different versions
to verify version-specific feature support.
"""
import pytest
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


def _id_from_version(version):
    """Generate test ID from version tuple."""
    return f"sqlite_{'_'.join(map(str, version))}"


@pytest.fixture(params=[
    (3, 8, 0),    # Basic version without many features
    (3, 8, 3),    # First version with CTE support (https://sqlite.org/changes.html#version_3_8_3)
    (3, 24, 0),   # First version with UPSERT support (https://sqlite.org/changes.html#version_3_24_0)
    (3, 25, 0),   # First version with window functions (https://sqlite.org/changes.html#version_3_25_0)
    (3, 28, 0),   # Enhanced window functions with EXCLUDE clause and GROUPS frames (https://sqlite.org/changes.html#version_3_28_0)
    (3, 30, 0),   # FILTER clause for aggregate functions and NULLS FIRST/LAST syntax (https://sqlite.org/changes.html#version_3_30_0)
    (3, 34, 0),   # Enhanced recursive CTEs to support multiple recursive terms (https://sqlite.org/changes.html#version_3_34_0)
    (3, 35, 0),   # First version with RETURNING clause and generalized UPSERT (https://sqlite.org/changes.html#version_3_35_0)
    (3, 35, 4),   # Fixed RETURNING clause defects (https://sqlite.org/changes.html#version_3_35_4)
    (3, 38, 0),   # JSON functions become built-in and support -> operators (https://sqlite.org/changes.html#version_3_38_0)
    (3, 41, 0),   # JSON functions support JSON5 extensions (https://sqlite.org/changes.html#version_3_41_0)
    (3, 44, 0),   # Aggregate functions support ORDER BY clause, CONCAT and CONCAT_WS functions (https://sqlite.org/changes.html#version_3_44_0)
    (3, 45, 0),   # JSON functions rewritten with JSONB internal format (https://sqlite.org/changes.html#version_3_45_0)
    (3, 51, 0),   # Enhanced JSONB functions with jsonb_each() and jsonb_tree() (https://sqlite.org/changes.html#version_3_51_0)
], ids=_id_from_version)
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