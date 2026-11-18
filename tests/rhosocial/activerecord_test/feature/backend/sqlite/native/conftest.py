# tests/rhosocial/activerecord_test/feature/backend/sqlite/native/conftest.py
"""L2 environment fixtures for the SQLite affinity tests.

- ``database``: one database per directory (session scope, emptied at start);
- ``schema``: the five affinity definition classes, dropped and recreated
  before every test (function scope), so each test starts from empty tables;
- ``affinity_models``: the five models configured against this directory's
  database.
"""

from pathlib import Path
from typing import Dict

import pytest

from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.testsuite.pytest_plugin import Declaration

from native_models import (
    AFFINITY_DEFINITIONS,
    NativeAffinityBlob,
    NativeAffinityInteger,
    NativeAffinityNumeric,
    NativeAffinityReal,
    NativeAffinityText,
)

# This directory owns one session-scoped database; parallel workers would
# recreate the same tables underneath each other.
DECLARATION = Declaration(
    # This scope opens a database; the plugin enforces this declaration.
    uses_database=True,
    parallel=True,
    purpose="SQLite storage classes and affinity over a directory-owned database",
    passes_means="every declared column stores and returns its SQLite affinity value",
    fails_means="a value is silently coerced into the wrong storage class",
)

DDL = ExecutionOptions(stmt_type=StatementType.DDL)

#: One model per affinity, in the order the tables are created.
MODELS = (
    ("text", NativeAffinityText),
    ("integer", NativeAffinityInteger),
    ("real", NativeAffinityReal),
    ("numeric", NativeAffinityNumeric),
    ("blob", NativeAffinityBlob),
)


def _database_name() -> str:
    """Database name from this directory's namespace (below ``feature``)."""
    parts = Path(__file__).parent.parts
    start = parts.index("feature") + 1
    return "test_" + "_".join(parts[start:])


@pytest.fixture(scope="session")
def database_config(backend_scenario):
    """The scenario, its connection configuration, and the directory database name."""
    name = _database_name()
    return backend_scenario, backend_scenario.make_config(name), name


@pytest.fixture(scope="session")
def database(database_config):
    """The directory's database, prepared once and left for later files."""
    scenario, config, name = database_config
    scenario.reset_database(name)
    backend = scenario.backend_class(connection_config=config)
    backend.connect()
    backend.introspect_and_adapt()
    yield backend
    backend.disconnect()


@pytest.fixture(scope="function", autouse=True)
def schema(database):
    """Drop and recreate the affinity tables this directory uses, before every test."""
    fixtures = [definition(database.dialect) for definition in AFFINITY_DEFINITIONS]
    for fixture in fixtures:
        database.execute(*fixture.create_table.to_sql(), options=DDL)
    yield
    for fixture in reversed(fixtures):
        database.execute(*fixture.drop_table.to_sql(), options=DDL)


@pytest.fixture(name="affinity_models")
def affinity_models(database_config) -> Dict[str, type]:
    """The five affinity models configured against this directory's database."""
    scenario, config, _name = database_config
    models = dict(MODELS)
    for model in models.values():
        model.configure(config, scenario.backend_class)
    yield models
    for model in models.values():
        model.backend().disconnect()
